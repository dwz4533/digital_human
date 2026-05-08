import socket
import json
import queue
import time
import threading

import numpy as np
import sounddevice as sd
import torch
from faster_whisper import WhisperModel


class WhisperASR:
    def __init__(self):
        
        self.audio_q = queue.Queue()  # 用于接收音频数据的队列

        self.UNITY_HOST = "127.0.0.1"
        self.UNITY_PORT = 5005

        self.MODEL_SIZE = "small"       # 3050 4GB + CPU：建议 tiny / base / small
        self.DEVICE = "cpu"             # 你已跑通 CPU；后面要 GPU 再改为 "cuda"
        self.COMPUTE_TYPE = "int8"      # CPU 推荐 int8；GPU 可用 float16

        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1

        self.FRAME_MS = 40                      # 改为 40 ms，确保帧长 ≥ 512
        self.FRAME_SAMPLES = int(self.SAMPLE_RATE * self.FRAME_MS / 1000)  # 640
        
        self.START_SPEECH_FRAMES = 5  # 150ms
        self.MAX_TAIL_SILENCE_FRAMES = 6

        self.VAD_THRESHOLD = 0.5        # Silero VAD 阈值（原 VAD_MODE 3 等效）
        self.MAX_SILENCE_MS = 800       # 静音超过多少 ms 认为一句话结束
        self.MAX_UTTERANCE_SEC = 10     # 单段最长秒数，防止一直不结束

        self.LANGUAGE = "zh"            # 中文；也可 None 自动识别
    
        # 1) 初始化 Whisper 模型
        self.model = WhisperModel(self.MODEL_SIZE, device=self.DEVICE, compute_type=self.COMPUTE_TYPE)
        print("✅ Whisper model loaded:", self.MODEL_SIZE, self.DEVICE, self.COMPUTE_TYPE)

        # 2) 初始化 Silero VAD 模型（替换 webrtcvad）
        self.vad_model = self._load_vad_model()
        print("✅ Silero VAD model loaded")

    def _load_vad_model(self):
        """使用 torch.hub 加载 Silero VAD 模型"""
        model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False,
            verbose=False
        )
        model.eval()
        return model

    def _is_speech_frame(self, audio_frame: np.ndarray) -> bool:
        """判断当前帧是否为语音（替代 webrtcvad.is_speech）"""
        audio_tensor = torch.from_numpy(audio_frame).float()
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        with torch.no_grad():
            speech_prob = self.vad_model(audio_tensor, self.SAMPLE_RATE)[0].item()
        return speech_prob > self.VAD_THRESHOLD

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print("Audio status:", status)
        # indata: float32 [-1,1], shape (frames, channels)
        mono = indata[:, 0].copy()
        self.audio_q.put(mono)

    # VAD分段（原 webrtcvad 的 PCM16 转换已不再需要，保留以防其他地方调用）
    def float_to_pcm16(self, x: np.ndarray) -> bytes:
        x = np.clip(x, -1.0, 1.0)
        pcm16 = (x * 32767).astype(np.int16)
        return pcm16.tobytes()

    def run_realtime_asr(self):
        speech_count = 0
        tail_silence_frames = 0

        # 分段缓冲
        voiced_frames = []
        in_speech = False       # 当前是否在说话
        silence_ms = 0          # 当前静默的毫秒数
        utter_start_time = None

        # 3) 打开麦克风
        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=self.FRAME_SAMPLES,
            callback=self.audio_callback
        ):
            print("🎙️ Listening... Speak now")

            while True:
                frame = self.audio_q.get()  # float32 mono, len=FRAME_SAMPLES

                # 使用 Silero VAD 判断当前帧是否为语音
                is_speech = self._is_speech_frame(frame)

                now = time.time()

                if is_speech:
                    speech_count += 1
                    if not in_speech:
                        if speech_count < self.START_SPEECH_FRAMES:
                            continue
                        in_speech = True
                        utter_start_time = now
                        voiced_frames = []
                        silence_ms = 0

                    voiced_frames.append(frame)
                else:
                    speech_count = 0
                    if in_speech:
                        silence_ms += self.FRAME_MS
                        if tail_silence_frames < self.MAX_TAIL_SILENCE_FRAMES:
                            tail_silence_frames += 1
                            voiced_frames.append(frame)  # 也把结尾一点静音带上更自然

                        # 结束条件：静音足够长 or 单段太长
                        dur = now - (utter_start_time or now)
                        if silence_ms >= self.MAX_SILENCE_MS or dur >= self.MAX_UTTERANCE_SEC:
                            # 拼接成一段
                            audio = np.concatenate(voiced_frames, axis=0)

                            # 进行识别
                            try:
                                # 防止误触的情况的发生
                                dur_sec = audio.shape[0] / self.SAMPLE_RATE
                                rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

                                if dur_sec < 0.5 or rms < 0.01:
                                    in_speech = False
                                    silence_ms = 0
                                    utter_start_time = None
                                    voiced_frames = []
                                    continue

                                # 模型进行处理
                                segments, info = self.model.transcribe(
                                    audio,
                                    language=self.LANGUAGE,
                                    vad_filter=True,
                                    vad_parameters=dict(min_silence_duration_ms=800, speech_pad_ms=200),
                                    beam_size=5,
                                    initial_prompt=None,
                                )
                                text = "".join([seg.text for seg in segments]).strip()
                            except Exception as e:
                                text = ""
                                print("❌ transcribe error:", e)

                            if text:
                                print("📝", text)
                                try:
                                    # 返回用户的话
                                    return text
                                except Exception as e:
                                    print("❌ send failed:", e)

                            # 重置
                            in_speech = False
                            silence_ms = 0
                            utter_start_time = None
                            voiced_frames = []
                            tail_silence_frames = 0
                    else:
                        # 非说话状态：啥也不做
                        pass

if __name__ == "__main__":
    asr = WhisperASR()
    asr.run_realtime_asr()
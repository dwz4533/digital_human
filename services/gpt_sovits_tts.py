# import requests
# import numpy as np
# import sounddevice as sd
# import queue
# import threading
# import soundfile as sf
# import time


# class GPTSovitsTTS:
#     def __init__(self, api_url="http://127.0.0.1:9880", ref_audio_path="reference.wav", prompt_text=""):
#         self.api_url = api_url
#         self.ref_audio_path = ref_audio_path
#         self.prompt_text = prompt_text
#         self.sample_rate = 32000  # GPT-SoVITS 默认输出

#     def synthesize_stream(self, text_generator):
#         for idx, text in enumerate(text_generator):
#             if not text.strip():
#                 continue
#             print(f"📝 发送第 {idx+1} 句: {text}")
#             resp = requests.post(
#                 f"{self.api_url}/tts",
#                 json={
#                     "text": text,
#                     "text_lang": "zh",
#                     "ref_audio_path": self.ref_audio_path,
#                     "prompt_text": self.prompt_text,
#                     "prompt_lang": "zh",
#                     "streaming_mode": True,
#                     "media_type": "wav",
#                     "text_split_method": "cut5",
#                     "stream_chunk_size": 20,
#                     "fragment_interval": 0.3,
#                     "top_k": 12,
#                     "top_p": 0.8,
#                     "temperature": 0.8,
#                     "speed_factor": 1.0,
#                     "batch_size": 1,
#                     "seed": 42,
#                 },
#                 stream=True,
#                 timeout=30
#             )
#             if resp.status_code != 200:
#                 print(f"❌ API 错误 {resp.status_code}: {resp.text}")
#                 continue

#             print(f"🎤 开始接收音频流...")
#             chunk_count = 0
#             for chunk in resp.iter_content(chunk_size=1024):
#                 if chunk:
#                     chunk_count += 1
#                     yield chunk
#             print(f"✅ 第 {idx+1} 句完成，共 {chunk_count} 个音频块")

#     def play_stream_realtime(self, audio_bytes_iter):
#         """使用 sounddevice 实时播放，支持原始 PCM 和 WAV"""
#         audio_queue = queue.Queue(maxsize=50)
#         stop_event = threading.Event()

#         def _player():
#             # 播放线程：持续从队列取 PCM int16 数据并播放
#             sd.default.samplerate = self.sample_rate
#             sd.default.channels = 1
#             sd.default.dtype = 'int16'

#             with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
#                 while not stop_event.is_set():
#                     try:
#                         pcm_chunk = audio_queue.get(timeout=0.1)
#                         if pcm_chunk is None:
#                             break
#                         # 确保数据是 int16 类型
#                         if pcm_chunk.dtype != np.int16:
#                             pcm_chunk = pcm_chunk.astype(np.int16)
#                         stream.write(pcm_chunk)
#                     except queue.Empty:
#                         continue
#             print("🎧 播放线程退出")

#         player_thread = threading.Thread(target=_player, daemon=True)
#         player_thread.start()

#         # 主线程：解析接收到的数据，提取 PCM
#         buffer = b''
#         wav_header_parsed = False
#         data_offset = 0
#         sample_rate_from_header = None

#         for chunk in audio_bytes_iter:
#             buffer += chunk
#             # 解析 WAV 头（只需一次）
#             if not wav_header_parsed and len(buffer) >= 44:
#                 if buffer[:4] == b'RIFF' and buffer[8:12] == b'WAVE':
#                     import struct
#                     # 采样率在字节 24-27
#                     sr = struct.unpack('<I', buffer[24:28])[0]
#                     if sr != self.sample_rate:
#                         print(f"⚠️ 警告：WAV头采样率为 {sr} Hz，与预期不符，已自动调整")
#                         self.sample_rate = sr
#                     # 查找 data chunk 位置
#                     pos = 12
#                     while pos < len(buffer) - 8:
#                         ck_id = buffer[pos:pos+4]
#                         ck_size = struct.unpack('<I', buffer[pos+4:pos+8])[0]
#                         if ck_id == b'data':
#                             data_offset = pos + 8
#                             break
#                         pos += 8 + ck_size
#                     wav_header_parsed = True
#                     # 切出头后的 PCM 数据
#                     pcm_data = buffer[data_offset:]
#                     buffer = b''
#                     if pcm_data:
#                         audio_np = np.frombuffer(pcm_data, dtype=np.int16)
#                         audio_queue.put(audio_np)
#                     continue

#             if wav_header_parsed and buffer:
#                 # 后续数据都是纯 PCM
#                 audio_np = np.frombuffer(buffer, dtype=np.int16)
#                 audio_queue.put(audio_np)
#                 buffer = b''

#         # 处理剩余 buffer
#         if buffer:
#             audio_np = np.frombuffer(buffer, dtype=np.int16)
#             audio_queue.put(audio_np)

#         # 等待播放完毕
#         time.sleep(1)  # 确保最后一块播完
#         stop_event.set()
#         audio_queue.put(None)
#         player_thread.join(timeout=2)
#         print("✅ 实时播放结束")

#     def save_stream_to_file(self, audio_bytes_iter, output_path="output.wav"):
#         all_audio = bytearray()
#         for audio_bytes in audio_bytes_iter:
#             all_audio.extend(audio_bytes)
#         audio_np = np.frombuffer(all_audio, dtype=np.int16).astype(np.float32) / 32767.0
#         sf.write(output_path, audio_np, self.sample_rate)
#         print(f"💾 音频已保存至: {output_path}")


# if __name__ == "__main__":
#     REF_AUDIO_PATH = r"D:/Desktop/GPT-SoVITS-v3lora-20250228/reference.wav"
#     PROMPT_TEXT = "高管也通过电话、短信、微信等方式对报道给予好评"

#     tts = GPTSovitsTTS(ref_audio_path=REF_AUDIO_PATH, prompt_text=PROMPT_TEXT)

#     def text_generator():
#         yield "你好，我是黄河非遗小助手三三。"
#         yield "请问你有什么问题呢？"
#         yield "我可以给你介绍很多的非遗项目"

#     print("=" * 50)
#     print("开始实时流式合成测试...")

#     stream = tts.synthesize_stream(text_generator())
#     tts.play_stream_realtime(stream)

#     print("=" * 50)
#     print("测试完成！")

import requests
import numpy as np
import sounddevice as sd
import queue
import threading
import soundfile as sf
import time


class GPTSovitsTTS:
    def __init__(self, api_url="http://127.0.0.1:9880", ref_audio_path="reference.wav", prompt_text=""):
        self.api_url = api_url
        self.ref_audio_path = ref_audio_path
        self.prompt_text = prompt_text
        self.sample_rate = 32000  # GPT-SoVITS 默认输出采样率

    def synthesize_stream(self, text_generator):
        """
        逐句请求 API，每次返回完整句子的音频（原始 PCM int16）。
        """
        for idx, text in enumerate(text_generator):
            if not text.strip():
                continue
            print(f"📝 发送第 {idx+1} 句: {text}")
            resp = requests.post(
                f"{self.api_url}/tts",
                json={
                    "text": text,
                    "text_lang": "zh",
                    "ref_audio_path": self.ref_audio_path,
                    "prompt_text": self.prompt_text,
                    "prompt_lang": "zh",
                    "streaming_mode": True,
                    "media_type": "raw",            # 关键改动：请求原始 PCM，避免 WAV 头问题
                    "text_split_method": "cut5",
                    "stream_chunk_size": 0,         # 0 表示返回完整音频流
                    "fragment_interval": 0.3,
                    "top_k": 12,
                    "top_p": 0.8,
                    "temperature": 0.8,
                    "speed_factor": 1.0,
                    "batch_size": 1,
                    "seed": 42,
                },
                stream=True,
                timeout=30
            )
            if resp.status_code != 200:
                print(f"❌ API 错误 {resp.status_code}: {resp.text}")
                continue

            # 收集该句子的全部 PCM 数据
            pcm_data = bytearray()
            for chunk in resp.iter_content(chunk_size=1024):
                if chunk:
                    pcm_data.extend(chunk)
            if pcm_data:
                print(f"✅ 第 {idx+1} 句完成，PCM 数据 {len(pcm_data)} 字节 ({len(pcm_data)//2} 采样点)")
                yield pcm_data
            else:
                print(f"⚠️ 第 {idx+1} 句未返回音频数据")
                
    def _synthesize_one(self, text, max_retries=2):
        """合成单个短句，支持重试，返回 int16 numpy 数组"""
        for attempt in range(max_retries):
            try:
                pcm_bytes = next(self.synthesize_stream(iter([text])))
                return np.frombuffer(pcm_bytes, dtype=np.int16)
            except StopIteration:
                if attempt < max_retries - 1:
                    time.sleep(0.3)
                    continue
                raise RuntimeError(f"TTS 合成无返回数据，文本: {text}")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                raise e
        # 最终失败返回一小段静音（避免播放中断）
        print(f"⚠️ 合成彻底失败，插入静音占位: {text}")
        return np.zeros(int(0.2 * self.sample_rate), dtype=np.int16)

    def synthesize_and_enqueue(self, sentences, pcm_queue, session_manager, sid):
        """固定双缓冲：始终保证队列中有 1 句待播，同时后台合成下一句"""
        import threading

        if not sentences:
            return

        n = len(sentences)
        lock = threading.Lock()
        next_idx = 0  # 下一个要入队的索引
        pending = {}
        session_invalid = False

        def try_enqueue():
            nonlocal next_idx
            while next_idx in pending:
                pcm = pending.pop(next_idx)
                if pcm is not None:
                    pcm_queue.put(pcm)
                    print(f"   -> 第 {next_idx+1} 句已入队 ({len(pcm)/self.sample_rate:.2f}s)")
                next_idx += 1

        # 合成第一句，立即入队
        try:
            pcm = self._synthesize_one(sentences[0])
        except Exception as e:
            print(f"❌ 第一句合成失败: {e}")
            return
        with lock:
            pending[0] = pcm
            try_enqueue()

        if n == 1:
            return

        # 后台线程：顺序合成剩余句子，但受队列状态控制
        def producer():
            nonlocal session_invalid
            idx = 1
            while idx < n and not session_invalid:
                # 等待队列有空位（即播放线程已取走前一句）
                while pcm_queue.qsize() >= 2:  # 最多积压2句
                    time.sleep(0.05)
                    if session_manager.get_session_id() != sid:
                        session_invalid = True
                        return
                if session_manager.get_session_id() != sid:
                    session_invalid = True
                    return

                sent = sentences[idx]
                print(f"🔊 后台合成第 {idx+1}/{n} 句: {sent}")
                try:
                    pcm = self._synthesize_one(sent)
                except Exception as e:
                    print(f"❌ 第 {idx+1} 句合成失败: {sent} - {e}")
                    pcm = np.zeros(int(0.3 * self.sample_rate), dtype=np.int16)

                with lock:
                    pending[idx] = pcm
                    try_enqueue()
                idx += 1

        threading.Thread(target=producer, daemon=True).start()
            
    
    def start_playback_loop(self, pcm_queue, session_manager, stop_event, on_play_start=None, on_play_end=None):
        def _player():
            with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
                current_sid = None
                idle_counter = 0
                idle_threshold = 5

                while not stop_event.is_set():
                    sid = session_manager.get_session_id()
                    if sid != current_sid:
                        # 清空队列仅当会话真正改变时
                        if current_sid is not None:
                            while not pcm_queue.empty():
                                try:
                                    pcm_queue.get_nowait()
                                except queue.Empty:
                                    break
                        current_sid = sid
                        idle_counter = 0
                        # 注意：不要 continue，立即尝试获取数据

                    try:
                        pcm_chunk = pcm_queue.get(timeout=0.1)
                        if pcm_chunk is None:
                            continue
                        if session_manager.get_session_id() != current_sid:
                            continue
                        if on_play_start and idle_counter > idle_threshold:
                            on_play_start()
                        stream.write(pcm_chunk)
                        idle_counter = 0
                    except queue.Empty:
                        idle_counter += 1
                        if idle_counter == idle_threshold and on_play_end:
                            on_play_end()
                        continue
        threading.Thread(target=_player, daemon=False).start()  # 改为非守护线程

#     def play_sentences_pipeline(self, sentences):
#         """
#         真正的流水线：第一句合成后立即播放，后台预合成后续句子。
#         解决队列空时播放线程提前退出的问题。
#         """
#         if not sentences:
#             return

#         pcm_queue = queue.Queue(maxsize=2)  # 缓冲句数
#         stop_event = threading.Event()
#         playback_finished = threading.Event()
#         synthesis_done = threading.Event()  # 标记所有句子已提交合成

#         def _player():
#             """播放线程：只要合成未完成或队列非空，就持续尝试获取数据"""
#             with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='int16') as stream:
#                 while not stop_event.is_set():
#                     try:
#                         pcm_chunk = pcm_queue.get(timeout=0.1)
#                         if pcm_chunk is None:   # 收到结束信号
#                             break
#                         stream.write(pcm_chunk)
#                     except queue.Empty:
#                         # 如果队列暂时为空，但合成尚未结束，继续等待
#                         if synthesis_done.is_set() and pcm_queue.empty():
#                             break
#                         continue
#             playback_finished.set()
#             print("🎧 播放线程退出")

#         player_thread = threading.Thread(target=_player, daemon=False)
#         player_thread.start()

#         # ---------- 合成第一句 ----------
#         first_sent = sentences[0]
#         print(f"🔊 合成第 1/{len(sentences)} 句: {first_sent}")
#         try:
#             first_pcm_bytes = next(self.synthesize_stream(iter([first_sent])))
#             first_pcm = np.frombuffer(first_pcm_bytes, dtype=np.int16)
#             pcm_queue.put(first_pcm)
#             print(f"   -> 第 1 句 PCM 长度 {len(first_pcm)} 采样点 ({len(first_pcm)/self.sample_rate:.2f} 秒)")
#         except Exception as e:
#             print(f"   ❌ 第 1 句合成失败: {e}")
#             # 通知播放线程结束
#             synthesis_done.set()
#             pcm_queue.put(None)
#             player_thread.join()
#             return

#         # 如果只有一句，直接结束
#         if len(sentences) == 1:
#             synthesis_done.set()
#             pcm_queue.put(None)
#             playback_finished.wait(timeout=10)
#             player_thread.join(timeout=2)
#             print("✅ 流水线播放结束")
#             return

#         # ---------- 后台合成剩余句子 ----------
#         def synthesize_remaining():
#             for idx, sent in enumerate(sentences[1:], start=2):
#                 print(f"🔊 合成第 {idx}/{len(sentences)} 句: {sent}")
#                 try:
#                     pcm_bytes = next(self.synthesize_stream(iter([sent])))
#                     pcm = np.frombuffer(pcm_bytes, dtype=np.int16)
#                     pcm_queue.put(pcm)
#                     print(f"   -> 第 {idx} 句 PCM 长度 {len(pcm)} 采样点 ({len(pcm)/self.sample_rate:.2f} 秒)")
#                 except Exception as e:
#                     print(f"   ❌ 第 {idx} 句合成失败: {e}")
#             synthesis_done.set()
#             pcm_queue.put(None)

#         synth_thread = threading.Thread(target=synthesize_remaining, daemon=False)
#         synth_thread.start()

#         # 等待合成线程完成，同时播放线程在后台工作
#         synth_thread.join()
#         # 等待播放线程清空队列
#         playback_finished.wait(timeout=len(sentences) * 10)
#         player_thread.join(timeout=2)
#         print("✅ 流水线播放结束")

#     def save_stream_to_file(self, pcm_bytes_iter, output_path="output.wav"):
#         """
#         将 PCM 字节流保存为 WAV 文件。
#         """
#         all_pcm = bytearray()
#         for pcm_bytes in pcm_bytes_iter:
#             all_pcm.extend(pcm_bytes)
#         if not all_pcm:
#             print("❌ 没有 PCM 数据，无法保存")
#             return
#         pcm = np.frombuffer(all_pcm, dtype=np.int16)
#         audio_float = pcm.astype(np.float32) / 32767.0
#         sf.write(output_path, audio_float, self.sample_rate)
#         print(f"💾 音频已保存至: {output_path}")

# # # 测试代码

# if __name__ == "__main__":
#     REF_AUDIO_PATH = r"./audio/my_audio.wav"
#     PROMPT_TEXT = "大家好，我是三三，很高兴认识你。今天天气不错，要一起出去走走吗？"

#     tts = GPTSovitsTTS(ref_audio_path=REF_AUDIO_PATH, prompt_text=PROMPT_TEXT)

#     def text_generator():
#         yield "你好，我是黄河非遗小助手三三。"
#         yield "请问你有什么问题呢？"
#         yield "我可以给你介绍很多的非遗项目"
        
#     texts = ["你好，我是黄河非遗小助手三三。", "请问你有什么问题呢？", "我可以给你介绍很多的非遗项目"]

#     print("=" * 50)
#     print("开始实时流式合成测试...")

#     stream = tts.synthesize_stream(text_generator())
#     # tts.save_stream_to_file(stream, '11.wav')
#     tts.play_sentences_pipeline(texts)

#     print("=" * 50)
#     print("测试完成！")


if __name__ == "__main__":
    import queue
    import threading
    import time

    REF_AUDIO_PATH = r"./audio/my_audio.wav"
    PROMPT_TEXT = "大家好，我是三三，很高兴认识你。今天天气不错，要一起出去走走吗？"

    tts = GPTSovitsTTS(ref_audio_path=REF_AUDIO_PATH, prompt_text=PROMPT_TEXT)

    class DummySessionManager:
        def get_session_id(self):
            return "test_sid"

    session_mgr = DummySessionManager()
    stop_evt = threading.Event()
    pcm_q = queue.Queue(maxsize=5)

    # 启动播放线程
    tts.start_playback_loop(pcm_q, session_mgr, stop_evt)

    # 测试句子（8句）
    test_sentences = [
        "你好，我是黄河非遗小助手三三。",
        "请问你有什么问题呢？",
        "我可以给你介绍很多的非遗项目",
        "黄河流域的皮影戏是国家级非物质文化遗产。",
        "它通过光影艺术讲述英雄史诗与民间故事。",
        "在桐柏县，这项技艺依然被老艺人们传承着。",
        "皮影戏起源于汉代，以竹制或皮制影人投射在幕布上，配合唱腔与器乐，演绎历史传说与人间百态，被誉为东方光影艺术瑰宝。",
        "如今，非遗传承人们将传统技艺与现代数字特效相结合，让古老的皮影戏在节庆活动和公益巡演中焕发新的生命力。"
    ]

    print("=" * 50)
    print("开始并发流水线测试...")

    # 在独立线程中运行合成入队
    def produce():
        tts.synthesize_and_enqueue(test_sentences, pcm_q, session_mgr, "test_sid")

    prod_thread = threading.Thread(target=produce)
    prod_thread.start()

    # 等待合成线程完成（所有句子已提交入队）
    prod_thread.join()
    print("所有句子合成并已入队，等待播放完成...")

    # 等待队列清空（即播放完毕）
    # 简单方法：估算总时长并等待，或监控队列
    total_duration = sum(len(pcm)/tts.sample_rate for pcm in list(pcm_q.queue)) if not pcm_q.empty() else 30
    time.sleep(total_duration + 2)  # 额外加2秒缓冲

    stop_evt.set()
    print("=" * 50)
    print("测试完成！")
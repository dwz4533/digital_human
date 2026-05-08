import time
import json
import ssl
import base64
import queue
import threading
import pyaudio
import websocket
import audioop  # RMS

from config import logger
from voice import ApiManager


class WakeASR:
    BYTES_PER_SAMPLE = 2  # paInt16 => 2 bytes

    def __init__(
        self,
        wake_word: str = "金鳞",
        api_manager: ApiManager = None,
        rate: int = 16000,
        chunk_ms: int = 40,
        max_record_seconds: float = 10.0,
        silence_seconds: float = 1.2,
        rms_threshold: int = 500,
        ws_open_timeout: float = 3.0,
    ):
        self.wake_word = wake_word
        self.rate = rate
        self.chunk_ms = chunk_ms
        self.max_record_seconds = max_record_seconds
        self.silence_seconds = silence_seconds
        self.rms_threshold = rms_threshold
        self.ws_open_timeout = ws_open_timeout

        if api_manager is None:
            import config
            self.api_manager = ApiManager(config.XF_API_CONFIGS)
        else:
            self.api_manager = api_manager

    # ===================== 对外方法 =====================

    def wait_and_recognize(self) -> str:
        logger.info(f"[WakeASR] Waiting wake word: {self.wake_word}")

        while True:
            text = self._recognize_one_sentence()
            if not text:
                continue

            logger.info(f"[WakeASR] Heard: {text}")

            if self.wake_word in text:
                after = text.split(self.wake_word, 1)[1].strip(" ，,。.!！?？")
                if after:
                    return after

                logger.info("[WakeASR] Woken. Listening for question...")
                question = self._recognize_one_sentence()
                if question:
                    return question

                logger.warning("[WakeASR] No question captured, back to wake waiting...")
                continue

            # 你如果只想“必须唤醒词”才返回，把这一行改成 continue
            return text

    # ===================== 核心：识别一句 =====================

    def _recognize_one_sentence(self) -> str:
        ws_param = self.api_manager.get_current_api()
        if not ws_param:
            logger.error("[WakeASR] No available API config.")
            return ""

        # frames / bytes
        chunk_frames = int(self.rate * (self.chunk_ms / 1000.0))  # 40ms => 640 frames
        if chunk_frames <= 0:
            chunk_frames = 640

        chunk_bytes = chunk_frames * self.BYTES_PER_SAMPLE
        send_interval = chunk_frames / self.rate

        done_event = threading.Event()
        stop_send_event = threading.Event()
        opened_event = threading.Event()

        # ⭐ 用 ws-seq 做动态修正，避免重复
        wsseq_lock = threading.Lock()
        wsseq_words = []  # list[str]，每个元素对应一次 ws_item 的合并文本

        def _ws_to_text(ws_list) -> str:
            """把 result.ws 转成纯文本"""
            out = []
            for ws_item in ws_list or []:
                for cw in ws_item.get("cw", []):
                    w = cw.get("w", "")
                    if w:
                        out.append(w)
            return "".join(out)

        def _apply_wpgs(result_obj: dict):
            """
            讯飞 wpgs：
            - pgs == 'apd' 或缺省：追加
            - pgs == 'rpl'：按 rg=[start,end] 替换
            """
            nonlocal wsseq_words
            pgs = result_obj.get("pgs")  # "apd" / "rpl" / None
            rg = result_obj.get("rg")    # [start,end] (按 ws 序号，不是字符下标)
            ws_list = result_obj.get("ws", [])

            text = _ws_to_text(ws_list)
            if not text:
                return

            with wsseq_lock:
                if pgs == "rpl" and isinstance(rg, list) and len(rg) == 2:
                    start, end = rg[0], rg[1]
                    # 防御：范围不合法就当追加
                    if isinstance(start, int) and isinstance(end, int) and start <= end and start >= 0:
                        # 讯飞 rg 是 “第 start~end 个 ws 序号”，一般是闭区间
                        # 我们这里做 slice 替换：start..end 替换为当前这段 text
                        # 注意：如果 end 超过当前长度，先扩展
                        if end >= len(wsseq_words):
                            # 用空串补齐
                            wsseq_words.extend([""] * (end - len(wsseq_words) + 1))
                        # 替换
                        wsseq_words[start:end + 1] = [text]
                    else:
                        wsseq_words.append(text)
                else:
                    # apd / None => 追加
                    wsseq_words.append(text)

        def _get_final_text() -> str:
            with wsseq_lock:
                return "".join(wsseq_words).strip()

        # --- WebSocket 回调 ---
        def on_open(ws):
            opened_event.set()
            logger.info("[WakeASR] WS opened")

        def on_message(ws, message: str):
            try:
                data = json.loads(message)
                code = data.get("code", 0)
                status = data.get("data", {}).get("status", 0)

                if code != 0:
                    logger.error(f"[WakeASR] WS error code={code}, msg={data.get('message')}")
                    stop_send_event.set()
                    done_event.set()
                    try:
                        ws.close()
                    except:
                        pass
                    return

                result = data.get("data", {}).get("result", {})
                if result:
                    _apply_wpgs(result)

                if status == 2:
                    stop_send_event.set()
                    done_event.set()
                    try:
                        ws.close()
                    except:
                        pass

            except Exception as e:
                logger.exception(f"[WakeASR] on_message exception: {e}")
                stop_send_event.set()
                done_event.set()
                try:
                    ws.close()
                except:
                    pass

        def on_error(ws, error):
            logger.error(f"[WakeASR] WS on_error: {error}")
            stop_send_event.set()
            done_event.set()

        def on_close(ws, code, msg):
            logger.info(f"[WakeASR] WS closed code={code}, msg={msg}")
            stop_send_event.set()
            done_event.set()

        # --- 建立 WS ---
        websocket.enableTrace(False)
        ws_url = ws_param.create_url()
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.ws_param = ws_param

        ws_thread = threading.Thread(
            target=ws.run_forever,
            kwargs={
                "sslopt": {"cert_reqs": ssl.CERT_NONE},
                "ping_interval": 20,
                "ping_timeout": 10,
            },
            daemon=True,
        )
        ws_thread.start()

        if not opened_event.wait(timeout=self.ws_open_timeout):
            logger.error("[WakeASR] WS open timeout")
            try:
                ws.close()
            except:
                pass
            return ""

        # --- 打开麦克风 ---
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.rate,
            input=True,
            frames_per_buffer=chunk_frames,
        )
        stream.start_stream()

        # --- start 帧 ---
        start_frame = {
            "common": {"app_id": ws_param.APPID},
            "business": {
                "domain": "iat",
                "language": "zh_cn",
                "accent": "mandarin",
                "dwa": "wpgs",
            },
            "data": {
                "status": 0,
                "format": f"audio/L16;rate={self.rate}",
                "encoding": "raw",
                "audio": "",
            },
        }

        try:
            if ws.sock and ws.sock.connected:
                ws.send(json.dumps(start_frame, ensure_ascii=False))
            else:
                logger.warning("[WakeASR] WS not connected right after open.")
                stop_send_event.set()
                done_event.set()
        except Exception as e:
            logger.error(f"[WakeASR] send start_frame failed: {e}")
            stop_send_event.set()
            done_event.set()

        # --- 音频发送线程 ---
        def send_audio_loop():
            start_time = time.time()
            speech_started = False
            silence_start = None

            try:
                while not stop_send_event.is_set():
                    if time.time() - start_time > self.max_record_seconds:
                        break

                    if not (ws.sock and ws.sock.connected):
                        break

                    try:
                        audio = stream.read(chunk_frames, exception_on_overflow=False)
                    except Exception as e:
                        logger.error(f"[WakeASR] stream.read error: {e}")
                        break

                    if not audio or len(audio) != chunk_bytes:
                        continue

                    rms = audioop.rms(audio, 2)
                    if rms >= self.rms_threshold:
                        speech_started = True
                        silence_start = None
                    else:
                        if speech_started:
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start >= self.silence_seconds:
                                break

                    frame = {
                        "common": {"app_id": ws_param.APPID},
                        "business": {
                            "domain": "iat",
                            "language": "zh_cn",
                            "accent": "mandarin",
                            "dwa": "wpgs",
                        },
                        "data": {
                            "status": 1,
                            "format": f"audio/L16;rate={self.rate}",
                            "encoding": "raw",
                            "audio": base64.b64encode(audio).decode("utf-8"),
                        },
                    }

                    try:
                        ws.send(json.dumps(frame, ensure_ascii=False))
                    except Exception as e:
                        logger.error(f"[WakeASR] send audio frame failed: {e}")
                        break

                    time.sleep(send_interval)

            finally:
                end_frame = {
                    "common": {"app_id": ws_param.APPID},
                    "business": {"domain": "iat", "language": "zh_cn", "accent": "mandarin"},
                    "data": {
                        "status": 2,
                        "format": f"audio/L16;rate={self.rate}",
                        "encoding": "raw",
                        "audio": "",
                    },
                }
                try:
                    if ws.sock and ws.sock.connected:
                        ws.send(json.dumps(end_frame, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"[WakeASR] send end_frame failed: {e}")

                stop_send_event.set()
                done_event.set()

        threading.Thread(target=send_audio_loop, daemon=True).start()

        # --- 等待结束 ---
        last_change = time.time()
        last_text = ""

        try:
            while not done_event.is_set():
                time.sleep(0.1)
                now_text = _get_final_text()
                if now_text != last_text:
                    last_text = now_text
                    last_change = time.time()

                # 发送停了 & 文本长时间不变 => 退出
                if stop_send_event.is_set() and (time.time() - last_change > 0.8):
                    break

        finally:
            stop_send_event.set()
            done_event.set()
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
            try:
                p.terminate()
            except:
                pass
            try:
                ws.close()
            except:
                pass

        return _get_final_text()

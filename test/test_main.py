import queue
import threading
import time
import logging
import asyncio
import re

from services import speak, speaking   # speak: async, speaking: sync fallback
from services.llm_service import LLMClient
from test_voice import WakeASR
from services import UnitySender
from test_whisper import WhisperASR
from SummerizeHistory import HistoryAndTimeManager

logging.basicConfig(level=logging.INFO)


question_q = queue.Queue()  # (sid, sentence), 用于保存用户的问题
sentence_q = queue.Queue()  # (sid, sentence), 用于保存LLM的回复
tts_q = queue.Queue()   # (sid, sentence), 用于tts播放
histories = dict()      #用于保存历史对话


sender = UnitySender()
asr = WhisperASR()  # 使用 WhisperASR 类实例化
llm = LLMClient()

conn = sender.connect_to_unity()


# ===== 会话ID：用于打断 =====
session_lock = threading.Lock()
current_session_id = 0


def next_session_id():
    global current_session_id
    with session_lock:
        current_session_id += 1
        return current_session_id


def get_session_id():
    with session_lock:
        return current_session_id


def _drain_queue(q: queue.Queue):
    try:
        while True:
            q.get_nowait()
    except queue.Empty:
        return

# ASR线程
def asr_worker():
    while True:
        text = asr.run_realtime_asr()
        if not text:
            continue

        sid = next_session_id()
        logging.info("[ASR] 用户问题：%s (sid=%s)", text, sid)

        _drain_queue(sentence_q)
        _drain_queue(tts_q)

        sender.send_line(conn, {"type": "user", "text": text})

        question_q.put((sid, text))


# LLM线程
def llm_worker():
    while True:
        sid, text = question_q.get()
        if not text:
            continue

        if sid != get_session_id():
            continue

        logging.info("[LLM] 开始生成 sid=%s", sid)

        try:
            llm.ask_LLM(
                problem=text,
                response_queue=sentence_q,
                sid=sid
            )
        except Exception as e:
            logging.exception("[LLM] 生成异常 sid=%s: %s", sid, e)
            sentence_q.put((sid, "我这边生成回答时出了点问题，你再试一次好吗？"))
        finally:
            sentence_q.put((sid, "__END__"))



# TTS与UI分别处理线程
_END_PUNCT = set("。！？!?")
_punct_re = re.compile(r"[。！？!?]")


def ui_and_tts_consumer():
    min_chars = 20               # 凑够多少字就先说（12~20都行）
    flush_interval = 1.0         # 最久等多久就必须开口（秒）
    max_chars = 120               # 太长了就强制切一段，避免一句过长合成慢

    tts_buf = ""
    last_flush = time.time()
    last_sid = None
    
    def flush(sid, force=False):
        nonlocal tts_buf, last_flush
        chunk = tts_buf.strip()
        if not chunk:
            tts_buf = ""
            last_flush = time.time()
            return

        # 避免句子太长导致合成时间大大加长
        if len(chunk) > max_chars:
            chunk = chunk[:max_chars]

        tts_q.put((sid, chunk))     # 用于TTS播报
        tts_buf = tts_buf[len(chunk):]  # 剩余留在 buffer
        last_flush = time.time()
    
    opened = False

    while True:
        sid, item = sentence_q.get()    #获得LLM的回复

        if sid != get_session_id():
            continue

        # 新会话：清空上一轮 TTS buffer
        if last_sid is None or sid != last_sid:
            tts_buf = ""
            last_flush = time.time()
            last_sid = sid
            opened = False
            
        if item == "__END__":
            # 把残留的也播掉
            flush(sid, force=True)
            sender.send_line(conn, {"type": "bot_end", "text": ""})
            opened = False
            continue

        sentence = (item or "").strip()
        if not sentence:
            continue
        
        if not opened:
            sender.send_line(conn, {"type": "bot_begin", "text": ""})
            opened = True

        # 将所有的LLM的回复都发送给UI界面
        sender.send_line(conn, {"type": "bot", "text": sentence})
        logging.info("[UI] -> Unity: %s (sid=%s)", sentence, sid)


        tts_buf += sentence

        now = time.time()
        has_punct = _punct_re.search(tts_buf) is not None   # 是否包含标点
        long_enough = len(tts_buf) >= min_chars             # 句子是否足够长
        timeout = (now - last_flush) >= flush_interval      # 是否超过最长等待时限
        too_long = len(tts_buf) >= max_chars                # 句子是否超过最长长度

        # 满足任一条件就立刻开口
        if has_punct or long_enough or timeout or too_long:
            if has_punct:
                m = _punct_re.search(tts_buf)
                cut = m.end()
                tts_q.put((sid, tts_buf[:cut].strip()))
                tts_buf = tts_buf[cut:]
                last_flush = time.time()
            else:
                flush(sid)


# TTS 线程
def tts_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def tts_loop():
        while True:
            sid, sentence = await asyncio.to_thread(tts_q.get)

            if sid != get_session_id():     # 若当前的sid不是最新会话则跳过
                continue

            sentence = (sentence or "").strip()
            if not sentence:
                continue

            try:
                sender.send_line(conn, {"type": "is_talking", "text": ""})
                # ok = await speak(sentence, sid=sid, get_session_id=get_session_id)
                ok = False
                if not ok:
                    speaking(sentence)          # 同步播放的后备方案(声音难听版，机器音)
                sender.send_line(conn, {"type": "is_talking_not", "text": ""})
            except Exception as e:
                if sid == get_session_id():
                    speaking(sentence)
                logging.exception(f"[TTS] 播放异常 sid={sid}: {e}")

    loop.run_until_complete(tts_loop())


if __name__ == "__main__":
    history_manager = HistoryAndTimeManager()
    
    threading.Thread(target=asr_worker, daemon=True).start()
    threading.Thread(target=llm_worker, daemon=True).start()
    threading.Thread(target=ui_and_tts_consumer, daemon=True).start()
    threading.Thread(target=tts_worker, daemon=True).start()

    # 确保信号能触发保存
    import sys
    def save_and_exit(sig, frame):
        print(f"\n程序终止，保存时间戳...")
        history_manager.ensure_timestamp_save()
        sys.exit(0)
    
    import signal
    signal.signal(signal.SIGINT, save_and_exit)
    signal.signal(signal.SIGTERM, save_and_exit)

    try:
        while True:
            time.sleep(1)
    finally:
        # 一定进行时间戳的保存
        print("执行 finally 块...")
        history_manager.ensure_timestamp_save()
    

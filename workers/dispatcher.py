import time
import re
from config import logger


_END_RE = re.compile(r"[。！？!?]")


def dispatcher_worker(app):
    """
    持续消费 sentence_q：
    1. 把 LLM 输出实时发给 Unity
    2. 把文本缓存起来
    3. 按标点/长度/超时切块送入 tts_q
    """
    min_chars = 20
    flush_interval = 1.0
    max_chars = 120

    tts_buf = ""
    last_flush = time.time()
    last_sid = None
    opened = False

    def flush(sid):
        nonlocal tts_buf, last_flush
        chunk = tts_buf.strip()
        if not chunk:
            tts_buf = ""
            last_flush = time.time()
            return

        if len(chunk) > max_chars:
            chunk = chunk[:max_chars]

        app.queue_manager.tts_q.put((sid, chunk))
        tts_buf = tts_buf[len(chunk):]
        last_flush = time.time()

    while not app.stop_event.is_set():
        sid, item = app.queue_manager.sentence_q.get()

        if sid != app.session_manager.get_session_id():
            continue

        if last_sid is None or sid != last_sid:
            tts_buf = ""
            last_flush = time.time()
            last_sid = sid
            opened = False

        if item == "__END__":
            flush(sid)
            app.unity_service.send_line(app.conn, {"type": "bot_end", "text": ""})
            opened = False
            continue

        sentence = (item or "").strip()
        if not sentence:
            continue

        if not opened:
            app.unity_service.send_line(app.conn, {"type": "bot_begin", "text": ""})
            opened = True

        app.unity_service.send_line(app.conn, {"type": "bot", "text": sentence})
        logger.info("[UI] -> Unity: %s (sid=%s)", sentence, sid)

        tts_buf += sentence

        now = time.time()
        has_punct = _END_RE.search(tts_buf) is not None
        long_enough = len(tts_buf) >= min_chars
        timeout = (now - last_flush) >= flush_interval
        too_long = len(tts_buf) >= max_chars

        if has_punct or long_enough or timeout or too_long:
            if has_punct:
                m = _END_RE.search(tts_buf)
                cut = m.end()
                chunk = tts_buf[:cut].strip()
                if chunk:
                    app.queue_manager.tts_q.put((sid, chunk))
                tts_buf = tts_buf[cut:]
                last_flush = time.time()
            else:
                flush(sid)
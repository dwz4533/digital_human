import time
import asyncio
from config import logger


def tts_worker(app):
    """
    持续消费 tts_q：
    1. 判断 sid 是否过期
    2. 通知 Unity 当前在说话
    3. 优先走异步 TTS
    4. 失败则走离线 fallback
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def tts_loop():
        while not app.stop_event.is_set():
            sid, sentence = await asyncio.to_thread(app.queue_manager.tts_q.get)

            if sid != app.session_manager.get_session_id():
                continue

            sentence = (sentence or "").strip()
            if not sentence:
                continue

            try:
                app.unity_service.send_line(app.conn, {"type": "is_talking", "text": ""})

                result = await app.tts_service.speak(
                    text=sentence,
                    sid=sid,
                    get_session_id=app.session_manager.get_session_id
                )

                if result == 'error':
                    app.tts_service.speaking(
                        text=sentence,
                        sid=sid,
                        get_session_id=app.session_manager.get_session_id
                    )
                

                app.unity_service.send_line(app.conn, {"type": "is_talking_not", "text": ""})

            except Exception as e:
                logger.exception("[TTS] 播放异常 sid=%s: %s", sid, e)

                try:
                    if sid == app.session_manager.get_session_id():
                        app.tts_service.speaking(sentence)
                except Exception:
                    pass

    loop.run_until_complete(tts_loop())

# import re
# import time
# import asyncio
# import threading
# import queue
# from config import logger


# def tts_worker(app):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)

#     # 启动播放线程，传入 stop_event
#     app.tts_service.start_playback_loop(
#         pcm_queue=app.queue_manager.pcm_q,
#         session_manager=app.session_manager,
#         stop_event=app.stop_event
#     )

#     async def tts_loop():
#         last_sid = None
#         while not app.stop_event.is_set():
#             sid, sentence = await asyncio.to_thread(app.queue_manager.tts_q.get)

#             if sid != last_sid:
#                 app.queue_manager.clear_pcm_queue()
#                 last_sid = sid

#             if sid != app.session_manager.get_session_id():
#                 continue

#             sentence = (sentence or "").strip()
#             if not sentence:
#                 continue

#             sub_sentences = split_sentence(sentence, max_chars=25, max_comma_chars=35)
#             sub_sentences = [s for s in sub_sentences if s.strip() and len(s.strip()) > 1]
#             if not sub_sentences:
#                 continue

#             try:
#                 app.unity_service.send_line(app.conn, {"type": "is_talking", "text": ""})
#                 await asyncio.to_thread(
#                     app.tts_service.synthesize_and_enqueue,
#                     sub_sentences,
#                     app.queue_manager.pcm_q,
#                     app.session_manager,
#                     sid
#                 )
#             except Exception:
#                 logger.exception("[TTS] 合成入队异常")
#             # 此处不发送 is_talking_not，交由播放线程在空闲时发送

#     loop.run_until_complete(tts_loop())
    
    

# def split_sentence(text, max_chars=30, max_comma_chars=50):
#     """
#     智能切分长文本，尽量避免在词语中间截断。
#     """
#     if not text:
#         return []
    
#     # 移除不可见控制字符
#     text = re.sub(r'[\x00-\x1f\x7f]', '', text.strip())
    
#     # 第一步：按句末标点切分（。！？!?）
#     sent_end_pat = r'([^。！？!?]+[。！？!?]+)'
#     parts = re.findall(sent_end_pat, text)
#     remainder = re.sub(sent_end_pat, '', text).strip()
    
#     segments = [p.strip() for p in parts if p.strip()]
#     if remainder:
#         segments.append(remainder)
    
#     result = []
#     for seg in segments:
#         if len(seg) <= max_comma_chars:
#             result.append(seg)
#         else:
#             # 第二步：按逗号、分号切分
#             comma_parts = re.split(r'([,，;；])', seg)
#             merged = []
#             i = 0
#             while i < len(comma_parts):
#                 if i + 1 < len(comma_parts) and comma_parts[i+1] in (',', '，', ';', '；'):
#                     merged.append(comma_parts[i] + comma_parts[i+1])
#                     i += 2
#                 else:
#                     merged.append(comma_parts[i])
#                     i += 1
            
#             # 合并过短片段，但不超过 max_comma_chars
#             temp = []
#             buf = ""
#             for part in merged:
#                 if len(buf + part) <= max_comma_chars:
#                     buf += part
#                 else:
#                     if buf:
#                         temp.append(buf)
#                     buf = part
#             if buf:
#                 temp.append(buf)
            
#             for sub in temp:
#                 if len(sub) <= max_chars:
#                     result.append(sub)
#                 else:
#                     # 第三步：强制按字数切分，但尽量在标点/空格处断句
#                     for i in range(0, len(sub), max_chars):
#                         chunk = sub[i:i+max_chars]
#                         # 如果是最后一块，直接保留
#                         if i + max_chars >= len(sub):
#                             result.append(chunk)
#                         else:
#                             # 从后往前找最近的标点或空格作为切分点
#                             cut_pos = max_chars
#                             for j in range(max_chars-1, max_chars//2, -1):
#                                 if chunk[j] in '，,。！？;；、 ':
#                                     cut_pos = j + 1
#                                     break
#                             result.append(chunk[:cut_pos])
#                             # 将剩余部分放回 sub 前面，下一轮处理
#                             sub = sub[cut_pos:] + sub[i+max_chars:]
#                             # 重置循环变量，相当于重新处理剩余部分
#                             i = -max_chars  # 技巧：使得下一轮 i=0，重新开始
#     return result
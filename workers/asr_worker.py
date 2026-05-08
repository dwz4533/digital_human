import time
from config import logger


def asr_worker(app):
    """
    持续监听语音输入：
    1. 调用 ASR 识别
    2. 生成新的 session id
    3. 清空旧会话残留队列
    4. 发给 Unity
    5. 推入 question_q
    """
    while not app.stop_event.is_set():
        try:
            start_time = time.time()
            text = app.asr_service.run_realtime_asr()
            logger.info("[ASR] 获取问题所需时间：%d", time.time() - start_time)
            if not text:
                continue

            sid = app.session_manager.next_session_id()
            logger.info("[ASR] 用户问题：%s (sid=%s)", text, sid)

            '''
            清除上一轮的llm回答和tts语音播放文本
            '''
            # 清空sentence_q队列，注：sentence_q是用来存储llm的回答的语句
            app.queue_manager.drain_queue(app.queue_manager.sentence_q)
            # 清空tts_q队列，等待llm模块进行输入
            app.queue_manager.drain_queue(app.queue_manager.tts_q)


            # 向unity发送用户的问题
            app.unity_service.send_line(app.conn, {"type": "user", "text": text})
            # 发送新的用户问题
            app.queue_manager.question_q.put((sid, text))

        except Exception as e:
            logger.exception("[ASR] 识别异常: %s", e)
            time.sleep(0.2)
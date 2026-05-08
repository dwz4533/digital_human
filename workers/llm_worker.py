import time
from config import logger, KEY_PATH


def llm_worker(app):

    while not app.stop_event.is_set():
        sid, user_question = app.queue_manager.question_q.get()

        if not user_question:
            continue

        if sid != app.session_manager.get_session_id():
            continue

        logger.info("[LLM] 开始生成 sid=%s", sid)

        try:
            memory = app.history_manager.long_term_memory.recall_memories(user_question)
            
            # 当前系统维护的历史记录
            current_QA = ''.join([dic['user'] + dic['bot'] for dic in app.history_manager.temp_history])
            print(current_QA)
            
            hybrid_results = app.rag_service.hybrid_retrieve(user_question, KEY_PATH, top_k=10, vec_weight=0.7)
            prompt = app.rag_service.build_prompt(hybrid_results, memory=memory)
            
            # 开始生成LLM回答
            start_time = time.time()
            bot_answer = app.llm_service.ask_LLM(
                problem='【前几轮的参考部分，不可重复使用】：'+ current_QA + '【本次问题】：' + user_question,
                response_queue=app.queue_manager.sentence_q,
                sid=sid,
                system_prompt=prompt
            )
            
            QAGroup = {
                'user': user_question,
                'bot': bot_answer
            }
            app.history_manager.short_memory(QAGroup)
            
            logger.info("[LLM] 生成时间为：%lf", time.time() - start_time)
                        
        except Exception as e:
            logger.exception("[LLM] 生成异常 sid=%s: %s", sid, e)
            app.queue_manager.sentence_q.put(
                (sid, "我这边生成回答时出了点问题，你再试一次好吗？")
            )
        finally:            
            app.queue_manager.sentence_q.put((sid, "__END__"))
import os
import threading
import time
import json
import signal

from config import logger
from core.queue_manager import QueueManager
from core.session_manager import SessionManager
from core.history_manager import HistoryAndTimeManager

from services.llm_service import LLMService
from services.asr_service import WhisperASRService
from services.tts_service import TTSService
from services.rag_service import RAGService
from services.unity_service import UnitySender
from services.gpt_sovits_tts import GPTSovitsTTS

from workers.asr_worker import asr_worker
from workers.llm_worker import llm_worker
from workers.dispatcher import dispatcher_worker
from workers.tts_worker import tts_worker

from config import MODEL, JSONL_PATH, INDEX_PATH, DB_PATH, TABLE_NAME, AUDIO_PATH

class AppController:
    def __init__(self):      
        self.unity_service = UnitySender()
        self.asr_service = WhisperASRService()
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        # self.tts_service = GPTSovitsTTS(
        #     ref_audio_path=AUDIO_PATH,
        #     prompt_text="大家好，我是三三，很高兴认识你。今天天气不错，要一起出去走走吗？"  # 与音频严格一致
        # )
        self.rag_service = RAGService(MODEL, JSONL_PATH, INDEX_PATH, DB_PATH, TABLE_NAME)

        self.queue_manager = QueueManager()
        self.session_manager = SessionManager()
        self.history_manager = HistoryAndTimeManager(LLM=self.llm_service)
        
        short_path = './history/short_history.json'
        self.history_manager.delete_long_memory()
        if os.path.isfile(short_path):
            print('正在更新记忆...')
            with open(short_path, 'r', encoding='utf-8') as f:
                short_memory = json.load(f)['temp_history']
                self.history_manager.long_memory(short_memory)
            print('记忆更新成功！！！')

        # 连接到unity
        self.conn = self.unity_service.connect_to_unity()
        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(target=asr_worker, args=(self,), daemon=True).start()
        threading.Thread(target=llm_worker, args=(self,), daemon=True).start()
        threading.Thread(target=dispatcher_worker, args=(self,), daemon=True).start()
        threading.Thread(target=tts_worker, args=(self,), daemon=True).start()

        self._register_signal_handlers()

        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        finally:
            logger.info("执行 finally 块，保存时间戳...")
            self.history_manager.ensure_timestamp_save()

    def stop(self):
        self.stop_event.set()
        logger.info("程序终止，保存时间戳...")
        self.history_manager.ensure_timestamp_save()

    def _register_signal_handlers(self):
        def save_and_exit(sig, frame):
            logger.info("收到退出信号：%s", sig)
            self.stop()
            raise SystemExit(0)

        signal.signal(signal.SIGINT, save_and_exit)
        signal.signal(signal.SIGTERM, save_and_exit)
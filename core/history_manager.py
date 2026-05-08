import os
import sys
import json
import time
import threading
from datetime import datetime
from services.longm_service import LongTermMemoryManager

class HistoryAndTimeManager:
    def __init__(self, LLM,  timestamp_file: str = "./history/short_history.json"):
        self.timestamp_file = timestamp_file
        self.llm = LLM
        self.long_term_memory = LongTermMemoryManager()
        self.last_update_unix, self.next_update_expected = self._load_timestamp(timestamp_file)
        self.temp_history = []
        self._lock = threading.Lock()

    # 只加载时间戳信息
    def _load_timestamp(self, timestamp_file: str):
        try:
            with open(timestamp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("last_update_unix", 0.0), data.get("next_update_expected", 0.0)
        except (FileNotFoundError, json.JSONDecodeError):
            now = time.time()
            return now, now

    def delete_long_memory(self):
        self.long_term_memory.delete_memory()

    def long_memory(self, query):
        session_summary = self.llm.ask_LLM(
            problem=str(query),
            response_queue=None,
            sid=0,
            system_prompt='帮我总结一下这些上下文，形成一段长期记忆，要求简洁、有重点'
        )
        self.long_term_memory.add_memory(session_summary)
        print(f"将会话总结存入长期记忆。")
        

    def short_memory(self, QAGroup: dict):
        """
        存储一组问答对到临时历史中。
        QAGroup 格式示例: 
        {
            'user': '用户问题文本',
            'bot': '机器人回答文本'
        }
        """
        with self._lock:
            self.temp_history.append(QAGroup.copy())
            MAX_HISTORY = 200
            if len(self.temp_history) > MAX_HISTORY:
                self.temp_history.pop(0)
        
        
    # 保存当前会话的时间戳和问答组
    def ensure_timestamp_save(self):
        timestamp_iso = datetime.now().isoformat()
        timestamp_unix = time.time()

        saved = False

        def save_now(reason="final"):
            nonlocal saved
            if saved:
                return

            try:
                with self._lock:
                    history_snapshot = self.temp_history.copy()

                history_snapshot = {
                    "last_update_iso": timestamp_iso,
                    "last_update_unix": timestamp_unix,
                    "next_update_expected": timestamp_unix + (10 * 24 * 60 * 60),
                    "temp_history": self.temp_history
                }

                # 确保目录存在
                os.makedirs(os.path.dirname(self.timestamp_file), exist_ok=True)

                with open(self.timestamp_file, 'w', encoding='utf-8') as f:
                    json.dump(history_snapshot, f, indent=2, ensure_ascii=False)

            except Exception as e:
                try:
                    # 第二层：简化保存（同样保存问答组）
                    simple_data = {
                        "last_update_unix": timestamp_unix,
                        "next_update_expected": timestamp_unix + (10 * 24 * 60 * 60),
                        "temp_history": self.temp_history
                    }
                    with open(f"{self.timestamp_file}.simple", 'w') as f:
                        json.dump(simple_data, f)
                except:
                    try:
                        # 第三层：最低限度保存（只保存时间戳，丢失问答组）
                        if not os.path.exists("./tmp"):
                            os.mkdir("./tmp")
                        os.system(f"echo '{time.time()}' > ./tmp/guaranteed_timestamp.txt")
                    except:
                        # 第四层：写入stderr
                        sys.stderr.write(f"GUARANTEED_TIMESTAMP:{time.time()}\n")
                        sys.stderr.flush()

            saved = True
            print(f"时间戳已确保保存 ({reason})")

        # 注册 atexit 和信号处理（省略，与原代码相同）
        import atexit
        atexit.register(lambda: save_now("atexit"))

        import signal
        def handle_signal(signum, frame):
            save_now(f"signal_{signum}")
            sys.exit(1)

        available_signals = []
        for sig_name in ('SIGINT', 'SIGTERM', 'SIGQUIT', 'SIGHUP', 'SIGBREAK'):
            if hasattr(signal, sig_name):
                available_signals.append(getattr(signal, sig_name))

        for sig in available_signals:
            signal.signal(sig, handle_signal)

        return save_now
import queue

class QueueManager:
    def __init__(self):
        self.question_q = queue.Queue()
        self.sentence_q = queue.Queue()
        self.tts_q = queue.Queue()
        self.pcm_q = queue.Queue(maxsize=8)  # 缓冲句数

    # 负责清空队列
    @staticmethod
    def drain_queue(q):
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass
    
    def clear_pcm_queue(self):
        while not self.pcm_q.empty():
            try:
                self.pcm_q.get_nowait()
            except queue.Empty:
                break
        # 放入 None 打断正在等待的播放线程
        self.pcm_q.put(None)
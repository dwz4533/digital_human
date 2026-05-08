import sqlite3
import json
import config
from datetime import datetime
from sentence_transformers import SentenceTransformer

class LongTermMemoryManager:
    def __init__(self, db_path=config.L_DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.embedder = SentenceTransformer(config.MODEL)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        # 创建存储对话摘要及其向量的表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                summary TEXT,
                embedding_json TEXT
            )
        ''')
        self.conn.commit()

    def _get_embedding(self, text):
        """将文本转换为向量"""
        embedding = self.embedder.encode(text).tolist()
        return json.dumps(embedding)  # 转为JSON字符串存储
    
    def delete_memory(self):
        cursor = self.conn.cursor()
        # 创建存储对话摘要及其向量的表
        cursor.execute('''
            SELECT id, timestamp FROM memory_store
        ''')
        rows = cursor.fetchall()  # 先取出所有，避免迭代时修改
        deleted_count = 0
        for idx, ts_str in rows:
            past_time = datetime.fromisoformat(ts_str)
            if (datetime.now() - past_time).days > 3:
                cursor.execute("DELETE FROM memory_store WHERE id = ?", (idx,))
                deleted_count += 1
        self.conn.commit()
        print(f"已删除 {deleted_count} 条过期记忆")


    def add_memory(self, qa_group):
        """
        存储一个问答组到长期记忆
        :param qa_group: 字典，例如 {'user': (sid, '用户问题'), 'bot': (sid, '机器人回答')}
        """
        summary = qa_group

        embedding_json = self._get_embedding(summary)
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO memory_store (timestamp, summary, embedding_json)
            VALUES (?, ?, ?)
        ''', (datetime.now().isoformat(), summary, embedding_json))
        self.conn.commit()
        print(f"长期记忆已存储: {summary}")


    def recall_memories(self, query_text, top_k=3):
        """
        根据查询文本，回忆最相关的 top_k 条历史记忆
        """
        query_embedding = self._get_embedding(query_text)
        cursor = self.conn.cursor()
        # 获取所有记忆（实际应用中需要向量索引优化）
        cursor.execute("SELECT id, summary, embedding_json FROM memory_store")
        all_memories = cursor.fetchall()

        # 计算相似度并排序
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        similarities = []
        for mem_id, summary, embedding_json in all_memories:
            mem_embedding = np.array(json.loads(embedding_json)).reshape(1, -1)
            query_emb = np.array(json.loads(query_embedding)).reshape(1, -1)
            sim = cosine_similarity(query_emb, mem_embedding)[0][0]
            similarities.append((sim, summary))

        similarities.sort(key=lambda x: x[0], reverse=True)
        # 返回最相关的 top_k 条摘要
        return [summary for _, summary in similarities[:top_k]]
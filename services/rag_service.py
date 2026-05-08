import os
import json
import time
import jieba
import faiss
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer

class Config:
    FAISS_BATCH_SIZE = 32
    STOP_NEW_WORDS_PATH = "stop_words.txt"

config = Config()

class RAGService:
    def __init__(self, model_path, jsonl_path, index_path, db_path, table_name="heritage", stop_words_path=None):
        start_time = time.time()
        print('正在加载模型...')
        self.embedding_model = SentenceTransformer(model_path,
                                                   tokenizer_kwargs={"use_fast": True},
                                                   model_kwargs={"torch_dtype": "float16"})
        print('模型加载成功！！！')
        print(f"模型加载时间为: {time.time() - start_time}")
        self.index_path = index_path
        self.db_path = db_path
        self.table_name = table_name
        self.jsonl_path = jsonl_path

        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
            self._load_metadata()
        else:
            self._create_index()
            self._save_metadata()

        self.stop_words = set()
        stop_path = stop_words_path or config.STOP_NEW_WORDS_PATH
        if os.path.exists(stop_path):
            with open(stop_path, 'r', encoding='utf-8') as f:
                self.stop_words = set(line.strip() for line in f if line.strip())

    # -------------------- 索引构建和元数据加载 --------------------
    def _load_intro_map(self):
        intro_map = {}
        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                name = data.get('名称', '').strip()
                intro = data.get('简介', '').strip()
                if name:
                    intro_map[name] = intro
        return intro_map

    def _create_index(self):
        documents = []
        self.metadatas = []
        intro_map = self._load_intro_map()
        print(f"从 JSONL 加载了 {len(intro_map)} 条简介")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, name, category, level, sn, batch, region FROM {self.table_name}")
        rows = cursor.fetchall()
        conn.close()

        matched = 0
        unmatched_names = []
        for row in rows:
            doc_id, name, category, level, sn, batch, region = row
            name = name.strip()
            intro = intro_map.get(name, "")
            if not intro:
                unmatched_names.append(name)
            else:
                matched += 1
            text = f"名称：{name}\n简介：{intro}"
            documents.append(text)
            self.metadatas.append({
                'id': doc_id,
                'name': name,
                'intro': intro,
                'full_text': text
            })

        print(f"匹配成功: {matched} 条，未匹配: {len(unmatched_names)} 条")
        if unmatched_names:
            print("未匹配到的名称示例:", unmatched_names[:10])

        embeddings = []
        for i in range(0, len(documents), config.FAISS_BATCH_SIZE):
            batch = documents[i:i + config.FAISS_BATCH_SIZE]
            batch_emb = self.embedding_model.encode(batch, show_progress_bar=True)
            embeddings.append(batch_emb)

        embeddings = np.vstack(embeddings).astype('float32')
        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

        faiss.write_index(self.index, self.index_path)

    def _save_metadata(self):
        meta_path = self.index_path + ".meta.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadatas, f, ensure_ascii=False, indent=2)

    def _load_metadata(self):
        meta_path = self.index_path + ".meta.json"
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                self.metadatas = json.load(f)
        else:
            self._load_metadata_from_db()

    def _load_metadata_from_db(self):
        self.metadatas = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, province, name, category, level, sn, batch, region FROM {self.table_name}")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            doc_id, province, name, category, level, sn, batch, region = row
            text = f"名称：{name}\n省份：{province}\n类别：{category}\n级别：{level}\n编号：{sn}\n批次：{batch}\n区域：{region}"
            self.metadatas.append({
                'id': doc_id,
                'name': name,
                'intro': text,
                'full_text': text
            })

    # -------------------- 检索方法 --------------------
    def retrieve(self, query, top_k=5):
        """纯向量检索，返回 (score, meta) 列表"""
        query_emb = self.embedding_model.encode([query])[0].astype('float32')
        query_emb = query_emb.reshape(1, -1)
        faiss.normalize_L2(query_emb)
        scores, indices = self.index.search(query_emb, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.metadatas):
                results.append((float(score), self.metadatas[idx]))
        return results

    def keyword_search(self, query, key_path, top_k=10):
        """关键词检索，返回按词频排序的前 top_k 个 (doc_id, freq)"""
        keys = jieba.cut(query, cut_all=False, HMM=True)
        with open(key_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        id_freq = {}
        for key in keys:
            ids_list = data.get(key)
            if ids_list:
                for doc_id in ids_list:
                    id_freq[doc_id] = id_freq.get(doc_id, 0) + 1

        # 按词频降序排序，取前 top_k
        sorted_items = sorted(id_freq.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_k]   # [(doc_id, freq), ...]

    def hybrid_retrieve(self, query, key_path, top_k=5, vec_weight=0.6):
        """
        混合检索：加权融合向量检索和关键词检索
        :param vec_weight: 向量检索权重 (关键词权重为 1-vec_weight)
        """
        # 1. 向量检索（多取一些候选）
        vec_results = self.retrieve(query, top_k=top_k * 2)
        # 2. 关键词检索
        kw_items = self.keyword_search(query, key_path, top_k=top_k * 2)

        id_to_meta = {meta['id']: meta for meta in self.metadatas}
        candidate_scores = {}

        # 向量得分归一化
        max_vec_score = vec_results[0][0] if vec_results else 1.0
        for score, meta in vec_results:
            norm_score = score / max_vec_score if max_vec_score > 0 else 0
            candidate_scores[meta['id']] = norm_score * vec_weight

        # 关键词得分：每个词贡献 (1-vec_weight)，词频累加
        for doc_id, freq in kw_items:
            kw_score = freq * (1 - vec_weight)
            if doc_id in candidate_scores:
                candidate_scores[doc_id] += kw_score
            else:
                candidate_scores[doc_id] = kw_score

        # 排序取 top_k
        sorted_ids = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        final_ids = [doc_id for doc_id, _ in sorted_ids[:top_k]]

        final_results = []
        for doc_id in final_ids:
            if doc_id in id_to_meta:
                final_results.append((0.0, id_to_meta[doc_id]))  # 分数占位
        return final_results

    # -------------------- Prompt 构建 --------------------
    def build_prompt(self, retrieved_docs, memory, kw_ids=None):
        """
        构建 prompt
        :param retrieved_docs: 混合检索结果，格式 [(score, meta), ...]
        :param kw_ids: 可选，关键词命中的ID列表（用于额外融合，已废弃，保留兼容）
        """
        context_parts = []
        indecies = []
        for i, (score, meta) in enumerate(retrieved_docs):
            context_parts.append(f"【参考文档 {i+1}】\n名称：{meta['name']}\n简介：{meta['intro']}\n")
            indecies.append(meta['id'])
        context = "\n".join(context_parts)

        struct_parts = []
        if indecies:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join('?' for _ in indecies)
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id IN ({placeholders})", indecies)
            for row in cursor.fetchall():
                struct_parts.append(str(row[1:]))
            conn.close()
        base_context = '\n'.join(struct_parts)

        prompt = f"""【问答信息】
                    [长期记忆库]：{memory}\n
                    请根据以下参考信息回答用户的问题。
                    参考信息：
                    {context}
                    
                    基本信息：(省份, 名称, 类别, 级别, 编号, 批次, 所在区域)
                    {base_context}

                    请基于以上参考信息给出准确、简洁的回答，回答中不要出现“根据记忆”和“根据上下文”这样的字眼。
                    如果参考信息不足以回答问题，请如实告知。
                    """
        return prompt


if __name__ == "__main__":
    MODEL = "C:/Users/dwz/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/snapshots/e8f8c211226b894fcb81acc59f3b34ba3efd5f42/"
    INDEX_PATH = "./data/non_heritage.faiss"
    DB_PATH = "./data/heritage.db"
    TABLE_NAME = "heritage"
    KEY_PATH = "./data/KeyWord.json"
    JSONL_PATH = "./data/heritage_source.jsonl"

    rag = RAGService(MODEL, JSONL_PATH, INDEX_PATH, DB_PATH, TABLE_NAME)

    queries = [
        "二十四节气是什么时候入选非遗的？",
        '编号为“Ⅷ-469”的非遗项目名称是什么？它属于陕西省哪个市、县？',
        '“咸阳鲁氏鎏金鎏银技艺”属于哪个类别？它的公布批次是第几批？',
        '请至少列出三个属于“传统技艺”类别且批次为“第七批”的陕西省级非遗项目名称。',
        '“安塞剪纸”被列入哪一批次？其保护单位（区域）是哪里？',
        '“黄帝陵祭典”属于哪一类民俗活动？它的省级编号是多少？',
        '传统戏剧“华阴老腔”的省级项目编号是什么？其保护区域是哪个市、县？',
        '在陕西非遗项目中，与“社火”相关的项目有哪些？请写出至少两个完整项目名称。',
        '“红拳”属于哪个类别？它是第几批列入省级非物质文化遗产的？',
        '请找出一个编号以“Ⅸ”开头的传统医药类项目，并说明它的完整名称和所在区域。',
        '“凤翔泥塑”属于传统美术类别，它是哪一批次公布的？其保护单位位于哪个县？'
    ]

    # 演示混合检索
    for query in queries:
        print(f"\n{'='*60}\n用户问题: {query}\n{'='*60}")
        # 使用混合检索
        hybrid_results = rag.hybrid_retrieve(query, KEY_PATH, top_k=5, vec_weight=0.7)
        print("混合检索结果（前5）：")
        for _, meta in hybrid_results:
            print(f"  名称: {meta['name']}")
        prompt = rag.build_prompt(query, hybrid_results)
        print("\n生成的 Prompt 预览（前500字符）：\n", prompt)
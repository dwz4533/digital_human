import os
import json
import time
import jieba
import faiss
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Dict, Any

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

    def retrieve(self, query, top_k=5):
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
        """返回按词频排序的前 top_k 个文档ID，以及对应的词频"""
        keys = jieba.cut(query, cut_all=False, HMM=True)
        with open(key_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        id_freq = {}
        for key in keys:
            ids_list = data.get(key)
            if ids_list:
                for doc_id in ids_list:
                    id_freq[doc_id] = id_freq.get(doc_id, 0) + 1

        # 按词频降序排序，返回前 top_k 个 ID 和对应的频次
        sorted_items = sorted(id_freq.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_items[:top_k]
        return top_items   # 返回 [(doc_id, freq), ...]

    def hybrid_retrieve(self, query, key_path, top_k=5, vec_weight=0.5):
        """
        混合检索：合并向量检索和关键词检索结果，按权重排序后取 top_k
        :param vec_weight: 向量检索的权重（关键词权重 = 1 - vec_weight）
        """
        # 1. 向量检索
        vec_results = self.retrieve(query, top_k=top_k * 2)  # 多取一些候选
        # 2. 关键词检索，获取 (doc_id, freq)
        kw_items = self.keyword_search(query, key_path, top_k=top_k * 2)

        # 构建 id -> 文档元数据的映射
        id_to_meta = {meta['id']: meta for meta in self.metadatas}

        # 收集所有候选文档的 id，并计算混合分数
        candidate_scores = {}
        # 向量检索分数（归一化到 0-1）
        max_vec_score = vec_results[0][0] if vec_results else 1.0
        for score, meta in vec_results:
            norm_score = score / max_vec_score if max_vec_score > 0 else 0
            candidate_scores[meta['id']] = norm_score * vec_weight

        # 关键词检索分数：根据命中词频加权，每个词贡献 (1 - vec_weight) / 总词数？简化：每个词固定分数
        # 为了让多词命中优势明显，直接将词频乘以 (1 - vec_weight)
        for doc_id, freq in kw_items:
            kw_score = freq * (1 - vec_weight)
            if doc_id in candidate_scores:
                candidate_scores[doc_id] += kw_score
            else:
                candidate_scores[doc_id] = kw_score

        # 按分数降序排序
        sorted_ids = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        final_ids = [doc_id for doc_id, _ in sorted_ids[:top_k]]

        # 返回最终结果（元数据）
        final_results = []
        for doc_id in final_ids:
            if doc_id in id_to_meta:
                # 此处分数可保留或设为0
                final_results.append((0.0, id_to_meta[doc_id]))
        return final_results

    def build_prompt(self, query, retrieved_docs, ids):
        context_parts = []
        indecies = []
        # 注意：此处使用混合检索的结果 retrieved_docs，不再做额外筛选
        for i, (score, meta) in enumerate(retrieved_docs):
            context_parts.append(f"【参考文档 {i+1}】\n名称：{meta['name']}\n简介：{meta['intro']}\n")
            indecies.append(meta['id'])
        context = "\n".join(context_parts)

        struct_parts = []
        if indecies:
            indecies = [int(i) for i in indecies if str(i).isdigit()]
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join('?' for _ in indecies)
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id IN ({placeholders})", indecies)
            for row in cursor.fetchall():
                struct_parts.append(str(row[1:]))
            conn.close()
        base_context = '\n'.join(struct_parts)

        prompt = f"""你是一个非物质文化遗产知识助手。请根据以下参考信息回答用户的问题。
                参考信息：
                {context}
                
                基本信息：(省份, 名称, 类别, 级别, 编号, 批次, 所在区域)
                {base_context}

                用户问题：{query}

                请基于以上参考信息给出准确、简洁的回答。如果参考信息不足以回答问题，请如实告知。
                """
        return prompt


def evaluate_recall_at_k(rag_service: RAGService, test_set_path: str, max_k: int = 20, step: int = 5, vec_weight: float = 0.5) -> Dict[int, Dict[str, float]]:
    """评估不同 k 下的 recall@k，返回每个 k 的向量召回率和混合召回率"""
    with open(test_set_path, 'r', encoding='utf-8') as f:
        test_queries = json.load(f)

    k_values = list(range(step, max_k + 1, step))
    results = {k: {"vector": [], "hybrid": []} for k in k_values}

    for item in test_queries:
        query = item["query"]
        relevant_ids = set(item["relevant_ids"])
        if not relevant_ids:
            continue

        # 获取所有可能的检索结果（取最大 k 值，避免重复检索）
        max_k_val = max(k_values)
        vec_all = rag_service.retrieve(query, top_k=max_k_val)
        hybrid_all = rag_service.hybrid_retrieve(query, rag_service.key_path, top_k=max_k_val, vec_weight=vec_weight)

        # 将结果按 k 截取，计算每个 k 的召回率
        for k in k_values:
            vec_ids = {meta["id"] for _, meta in vec_all[:k]}
            hybrid_ids = {meta["id"] for _, meta in hybrid_all[:k]}
            recall_vec = len(vec_ids & relevant_ids) / len(relevant_ids)
            recall_hybrid = len(hybrid_ids & relevant_ids) / len(relevant_ids)
            results[k]["vector"].append(recall_vec)
            results[k]["hybrid"].append(recall_hybrid)

    # 计算平均值
    final = {}
    for k in k_values:
        final[k] = {
            "vector_only": sum(results[k]["vector"]) / len(results[k]["vector"]) if results[k]["vector"] else 0,
            "hybrid": sum(results[k]["hybrid"]) / len(results[k]["hybrid"]) if results[k]["hybrid"] else 0
        }
    return final


if __name__ == "__main__":
    MODEL = "C:/Users/dwz/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2/snapshots/e8f8c211226b894fcb81acc59f3b34ba3efd5f42/"
    INDEX_PATH = "./data/non_heritage.faiss"
    DB_PATH = "./data/heritage.db"
    TABLE_NAME = "heritage"
    KEY_PATH = "./data/KeyWord.json"
    JSONL_PATH = "./data/heritage_source.jsonl"

    rag = RAGService(MODEL, JSONL_PATH, INDEX_PATH, DB_PATH, TABLE_NAME)
    rag.key_path = KEY_PATH

    results = evaluate_recall_at_k(rag, "./data/test_queries.json", max_k=20, step=5, vec_weight=0.8)
    for k, rec in results.items():
        print(f"recall@{k}: vector={rec['vector_only']:.4f}, hybrid={rec['hybrid']:.4f}")

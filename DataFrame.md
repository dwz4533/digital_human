question_q：问题队列。ASR->LLM
tts_q：语音播放队列。LLM->tts
sentence_q：LLM回答队列。LLM->unity

# 数据流程框架
```
多轮对话
   ↓
抽取长期有价值记忆
   ↓
写 SQLite user_memory
   ↓
写 FAISS memory_collection
   ↓
后续按语义召回
```

**json负责：**
配置文件
Prompt 模板
角色设定
动作映射
敏感词表
原始知识数据的小规模文件

**SQLite负责：**
知识主表
文本 chunk 主数据
会话记录
用户长期记忆
日志
索引和元数据映射

**Faiss负责：**
文本 chunk 的向量索引
用户长期记忆向量索引
查询时的 top-k 语义召回

SQLite和Faiss通过chunk_id和memory_id对齐


## 整体流程：
### 知识入库：
```
原始知识(JSON/文本)
    ↓
   清洗
    ↓
   切块
    ↓
写入 SQLite 的 knowledge_chunks 表
    ↓
计算 embedding
    ↓
写入 FAISS 索引
    ↓
保存 faiss_idx 与 chunk_id 的映射
```

### 问答检索：
```
用户问题
   ↓
embedding
   ↓
FAISS 检索 top-k
   ↓
根据 faiss_idx 查映射表
   ↓
根据 chunk_id 去 SQLite 查文本和 metadata
   ↓
做过滤、重排、拼接 prompt
   ↓
送给 LLM
```

### 记忆检索：
```
历史对话
   ↓
抽取长期记忆
   ↓
写 SQLite:user_memory
   ↓
embedding
   ↓
写 memory.index
   ↓
保存 memory_map.json
```


import json
import re
import config
import requests
from config import logger


class LLMService:
    def __init__(self, host: str = "127.0.0.1", port: str = "11434", model: str = "qwen3:1.7b"):
        self.url = f"http://{host}:{port}/api/chat"
        self.model = model
        self.headers = {"Content-Type": "application/json"}

    def ask_LLM(self, problem: str, response_queue, sid: int, system_prompt:str =None) -> str:

        data = {
            "model": self.model,
            "options": {"temperature": 0.2, "num_ctx": 8192},
            "stream": True,
            "messages": [
                {"role": "system", "content": config.LLM_SYSTEM_PROMPT + '\n' + system_prompt},
                {"role": "user", "content": problem},
            ],
        }

        full_text = []
        buffer = ""

        try:
            with requests.post(self.url, json=data, headers=self.headers, stream=True, timeout=None) as resp:
                resp.raise_for_status()

                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    content = (chunk.get("message", {}) or {}).get("content", "")
                    if not content:
                        continue

                    visible = self._strip_tagged_blocks(content)
                    if not visible:
                        continue

                    buffer += visible

                    # 断句：遇到标点不断输出
                    while True:
                        idx = self._first_sentence_end(buffer)
                        if idx < 0:
                            break
                        sentence = buffer[: idx + 1].strip()
                        buffer = buffer[idx + 1 :]

                        if sentence:
                            if response_queue:
                                response_queue.put((sid, sentence))
                                logger.info(f"sentence: {sentence}")
                            full_text.append(sentence)

                # 最后残留
                tail = buffer.strip()
                if tail:
                    if response_queue:
                        response_queue.put((sid, tail))
                    full_text.append(tail)
                    logger.info(f"tail: {tail}")

            return "".join(full_text)

        except requests.RequestException as e:
            logger.exception(f"LLM request error: {e}")
            return ""


    def _strip_tagged_blocks(self, text: str):
        if not hasattr(self, "_in_hide"):
            self._in_hide = False
            self._hide_tag = None  # "think" or "tool_call"

        out = []
        i = 0
        while i < len(text):
            if not self._in_hide:
                # 找下一个开标签
                idx_think = text.find("<think>", i)
                idx_tool  = text.find("<tool_call>", i)

                # 都找不到：全追加
                if idx_think == -1 and idx_tool == -1:
                    out.append(text[i:])
                    break

                # 取最近的
                idx = min([x for x in [idx_think, idx_tool] if x != -1])
                out.append(text[i:idx])

                # 进入隐藏区
                if idx == idx_think:
                    self._in_hide = True
                    self._hide_tag = "think"
                    i = idx + len("<think>")
                else:
                    self._in_hide = True
                    self._hide_tag = "tool_call"
                    i = idx + len("<tool_call>")

            else:
                # 在隐藏区：找对应闭标签
                close = "</think>" if self._hide_tag == "think" else "</tool_call>"
                j = text.find(close, i)
                if j == -1:
                    # 本 chunk 剩余都丢弃
                    break
                # 跳过隐藏内容和闭标签
                i = j + len(close)
                self._in_hide = False
                self._hide_tag = None

        return "".join(out)


    @staticmethod
    def _first_sentence_end(text: str) -> int:
        """
        返回最早出现的句末标点索引；找不到返回 -1
        """
        puncts = ["。", "！", "？", ".", "!", "?"]
        positions = [text.find(p) for p in puncts if text.find(p) != -1]
        return min(positions) if positions else -1


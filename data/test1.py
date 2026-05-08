# import os
# import re
# import json
# import requests
# from lxml import etree

# def get_html(url, headers):
#     return requests.post(url, headers=headers)


# def get_info(html, title_tags, content_tags):
#     tree = etree.HTML(html)
    
#     # 提取表头（清洗空文本）
#     titles = tree.xpath(title_tags)
#     titles = [t.strip() for t in titles if t.strip()]
    
#     # 提取内容行
#     c_tags = tree.xpath(content_tags)
    
#     final_data = list()
    
#     for element in c_tags:
#         # ✅ 关键修复：.//text() 只取当前节点下文本，不会全局乱抓
#         text_list = element.xpath('.//text()')
#         # 清洗空字符串、换行、空格
#         text_list = [t.strip() for t in text_list if t.strip()]
        
#         temp_data = dict()
#         # 一一对应，防止越界报错
#         for i in range(min(len(titles), len(text_list))):
#             temp_data[titles[i]] = re.sub(r'\s+', '', text_list[i])
        
#         final_data.append(temp_data)
    
#     return final_data
    
# def write_to_jsonl(data):
#     with open("./data/shandong.jsonl", "w", encoding="utf-8") as f:
#         for item in data:
#             # 关键：dump + \n
#             f.write(json.dumps(item, ensure_ascii=False) + "\n")

# if __name__ == "__main__":
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
#         'Accept-Language': 'zh-CN,zh;q=0.9',
#     }
#     total_data = []
#     for i in range(1, 2):
#         url = 'http://www.sdfeiyi.org/feiyiapi/feiyi.html'
        
#         HTML = get_html(url=url, headers=headers)
#         HTML = HTML.json()
#         print(HTML)

#         # 你当前这个陕西非遗网页 【正确 XPath】
#         # title_tags = '//table[@class="page_table_data_one"]/tr[@class="thead"]//text()'
#         # content_tags = '//table[@class="page_table_data_one"]/tr[not(@class="thead")]'
        
#         # data = get_info(HTML, title_tags=title_tags, content_tags=content_tags)
#         # total_data.extend(data)
#         data = HTML
#         cname = ["编号", "名称", "类别", "级别", "批次", "区域"]
#         ename = ['id', 'title', 'leixing', 'jibie', 'pici', 'danwei']
#         for dic in data:
#             temp_data = dict()
#             for key, value in dic.items():
#                 if key in ename:
#                     temp_data[cname[ename.index(key)]] = re.sub(r'\s+', '', value)
                
#             total_data.append(temp_data)
#         print(data)
#         print(len(data))
#     write_to_jsonl(total_data)
import re
import json
import jieba

with open('./data/stop_word.txt', 'r', encoding='utf-8') as f:
    data = f.read()
    stop_word = data.split('\n')
# data = list(set(data))
# with open('./data/stop_word.txt', 'w', encoding='utf-8') as f:
#     f.write('\n'.join(data))

names = []
key_set = dict()

with open('./data/non_heritage.faiss.meta.json', 'r', encoding='utf-8') as f:
    obj = json.load(f)
    # print(obj)
    for o in obj:
        names.append({o['id']:re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]', '', o['name'])})

# 切词
for idx, name in enumerate(names, 1):
    for key, value in name.items():
        words = jieba.cut(value, cut_all=False, HMM=True)
        for w in words:
            # 过滤空字符串和停用词
            if w.strip() and w not in stop_word:
                key_set.setdefault(w, []).append(idx)
                
with open('./data/KeyWord.json', 'w', encoding='utf-8') as f:
    json.dump(key_set, f, ensure_ascii=False, indent=4)
# data_s = []
# data = []
# with open('./data/henan_source.jsonl', 'r', encoding='utf-8') as f:
#     for line in f:
#         obj = json.loads(line)
#         data_s.append(re.sub(r'[\（\）\[\]]', '', obj['名称']))

# with open("./data/henan.jsonl", 'r', encoding='utf-8') as f:
#     for line in f:
#         obj = json.loads(line)
#         data.append(re.sub(r'[\（\）\[\]]', '', obj['名称']))

# m = []
# for s in data_s:
#     if s not in data:
#         m.append(s)

# print(m, len(m))



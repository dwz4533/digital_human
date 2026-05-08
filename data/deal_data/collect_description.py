import os
import json
import re
import csv
import time
import random
import requests
from lxml import etree
from urllib.parse import quote, urljoin
from datetime import datetime

# 分词
import jieba

from volcenginesdkarkruntime import Ark

# 全局初始化客户端
client = Ark(
    api_key='2ccedc30-724a-41e6-a25c-2659a376a8ad',
    timeout=1800,
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

def ask_LLM(problem: str, system_prompt: str = None, model: str = "doubao-seed-2-0-pro-260215") -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": problem})
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            reasoning_effort="medium",
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        print(f"LLM请求失败: {str(e)}")
        return problem

# ====================== LLM 智能提取项目关键词 ======================
def extract_key_words_by_llm(name, topk=3):
    system_prompt = """
    你是专业的项目信息提取专家，任务是从项目全称中提取3个最核心的业务关键词。
    规则：
    1. 只输出关键词，空格分隔，不要解释、不要序号
    2. 关键词必须是核心业务：道路、管网、学校、医院、产业园、水利等
    3. 过滤：项目、工程、建设、新建、改造、及、和、的、等
    4. 每个关键词2-4个字
    """
    user_prompt = f"请从项目名称提取3个核心关键词：{name}"
    try:
        result = ask_LLM(user_prompt, system_prompt=system_prompt)
        result = re.sub(r'[^\u4e00-\u9fa5\s]', '', result)
        keys = [w.strip() for w in result.split() if len(w.strip()) >= 2]
        keys = list(dict.fromkeys(keys))
        return keys[:topk]
    except:
        return []

# ====================== jieba 分词 ======================
def extract_key_words(name, topk=3):
    name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', name)
    words = jieba.lcut(name)
    stop_words = {"项目", "工程", "建设", "新建", "改造", "及", "和", "的", "等", "个", "万", "元"}
    words = [w for w in words if len(w) >= 2 and w not in stop_words]
    words = list(dict.fromkeys(words))
    return words[:topk]

def get_html(url, headers, timeout=15):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        else:
            print(f"请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None

# ====================== 稳定版：原生百度搜索（无第三方bug） ======================
def get_urls_by_baidusearch_multi(name, num_results=5):
    search_queries = [name]

    # LLM 关键词
    llm_keys = extract_key_words_by_llm(name, topk=3)
    if llm_keys:
        search_queries.append(" ".join(llm_keys))
        if len(llm_keys) >= 1:
            search_queries.append(llm_keys[0])

    # jieba 关键词
    jieba_keys = extract_key_words(name, topk=3)
    if jieba_keys:
        search_queries.append(" ".join(jieba_keys))
        if len(jieba_keys) >= 1:
            search_queries.append(jieba_keys[0])

    search_queries = list(dict.fromkeys([q for q in search_queries if q.strip()]))

    allow_domains = [
        "baike.baidu.com",
        "gov.cn",
        "org.cn",
        "zhihu.com",
        "163.com",
        "sina.com.cn",
        "people.com.cn",
        "xinhuanet.com",
        "toutiao.com",
        "sohu.com",
        "ifeng.com"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }

    all_urls = []

    for q in search_queries:
        if len(all_urls) >= 3:
            break
        try:
            print(f"  百度搜索: {q}")
            url = f"https://www.baidu.com/s?wd={quote(q)}&rn={num_results}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "utf-8"
            html = resp.text

            # 提取百度搜索结果链接
            found = re.findall(r'data-click.*?href="(http.*?)"', html)
            real_urls = []
            for u in found:
                real_urls.append(u)

            # 过滤域名
            for url in real_urls:
                if any(d in url for d in allow_domains) and url not in all_urls:
                    all_urls.append(url)
                    if len(all_urls) >= 3:
                        break

            time.sleep(random.uniform(1.2, 2.0))
        except Exception as e:
            print(f"搜索失败: {e}")
            continue

    all_urls.sort(key=lambda x: 0 if "baike.baidu.com" in x else 1)
    return all_urls[:3]

def extract_text_from_url(url, headers):
    html = get_html(url, headers, timeout=15)
    if not html:
        return ""

    tree = etree.HTML(html)
    texts = []

    if "baike.baidu.com" in url:
        paras = tree.xpath('//div[contains(@class,"para")]//text()')
        texts = paras
    elif "zhihu.com" in url:
        paras = tree.xpath('//div[contains(@class,"RichContent")]//text()')
        texts = paras
    else:
        paras = tree.xpath('//p//text() | //article//text() | //div[contains(@class,"content")]//text()')
        texts = paras

    raw = " ".join([t.strip() for t in texts if t.strip()])
    return clean_useless_text(raw)

def clean_useless_text(text):
    if not text:
        return ""
    text = re.sub(r'</?script.*?>', '', text, flags=re.I)
    text = re.sub(r'</?style.*?>', '', text, flags=re.I)
    text = re.sub(r'window\..*?;|function\(.*?\)|var\s+\w+|http\S+', '', text)
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。！？；：""''（）【】]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text if len(text) >= 80 else ""

def get_information_from_urls(urls, headers):
    all_text = []
    for url in urls:
        print(f"  爬取URL: {url}")
        text = extract_text_from_url(url, headers)
        if text:
            all_text.append(text)
            print(f"    有效文本: {len(text)} 字")
        time.sleep(random.uniform(0.8, 1.5))
    return '---分隔符---'.join(all_text)

def write_back(idx, datum, name):
    path = f'./data/deal_data/{name}_source.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    else:
        data = {}
    data[str(idx)] = datum
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_raw_text(province, idx, raw_text):
    raw_file = f'./data/deal_data/{province}_raw.json'
    if os.path.exists(raw_file):
        with open(raw_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    data[str(idx)] = raw_text
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def write_failed_record(province, idx, name, reason, url=""):
    failed_dir = './data/deal_data/failed_records/'
    if not os.path.exists(failed_dir):
        os.makedirs(failed_dir)
    failed_file = f'{failed_dir}{province}_failed.csv'
    file_exists = os.path.isfile(failed_file)
    with open(failed_file, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['编号', '项目名称', '失败原因', '百科URL', '失败时间'])
        writer.writerow([idx, name, reason, url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

def write_all_failed_summary(province, failed_list):
    failed_dir = './data/deal_data/failed_records/'
    if not os.path.exists(failed_dir):
        os.makedirs(failed_dir)
    summary_file = f'{failed_dir}{province}_failed_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(failed_list, f, ensure_ascii=False, indent=2)

def get_names(province):
    path = f'./data/deal_data/{province}.json'
    all_list = []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for idx in data.keys():
        all_list.append({idx: data[idx]['项目名称']})
    return all_list

def retry_failed(province):
    failed_file = f'./data/deal_data/failed_records/{province}_failed.csv'
    if not os.path.exists(failed_file):
        print(f"没有失败记录")
        return []
    failed_items = []
    with open(failed_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            failed_items.append({'idx': row['编号'], 'name': row['项目名称'], 'reason': row['失败原因']})
    return failed_items

if __name__ == '__main__':
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    provinces = ['henan', 'shan1xi', 'shan3xi', 'gansu']

    for province in provinces:
        search_names = get_names(province)
        success_count = 0
        fail_count = 0
        failed_items = []
        print(f"\n===== 开始处理：{province} =====")

        for item in search_names:
            idx, name = next(iter(item.items()))
            print(f"\n【处理】{idx} {name}")

            urls = get_urls_by_baidusearch_multi(name, num_results=5)

            if not urls:
                fail_count += 1
                write_failed_record(province, idx, name, "无有效URL")
                continue

            text = get_information_from_urls(urls, headers)
            if not text or len(text) < 150:
                fail_count += 1
                write_failed_record(province, idx, name, "文本过短")
                continue

            save_raw_text(province, idx, text)
            write_back(idx, text, province)
            success_count += 1
            time.sleep(random.uniform(1, 2))

        write_all_failed_summary(province, failed_items)
        print(f"\n完成 {province} | 成功：{success_count} | 失败：{fail_count}")
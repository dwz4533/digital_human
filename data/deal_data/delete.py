import re
import json


def remove_long_non_chinese(text, max_len=20):
    """
    删除连续超过 max_len 个的非汉字字符
    """
    result = []
    non_chinese_buf = []  # 缓存当前连续的非汉字字符

    for ch in text:
        # 判断是否为汉字（基本区范围）
        if '\u4e00' <= ch <= '\u9fff':
            # 遇到汉字，先处理之前缓存的非汉字字符
            if non_chinese_buf:
                if len(non_chinese_buf) <= max_len:
                    result.extend(non_chinese_buf)
                non_chinese_buf = []
            result.append(ch)  # 保留汉字
        else:
            # 非汉字字符，先缓存
            non_chinese_buf.append(ch)

    # 处理结尾可能残留的非汉字字符
    if non_chinese_buf and len(non_chinese_buf) <= max_len:
        result.extend(non_chinese_buf)

    return ''.join(result)


path = './data/deal_data/henan_raw.json'

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_data = dict()
low_data_idx = []
for key, value in data.items():
    value = re.sub(r"\s+", '', value)
    if len([0x4E00<= ord(v) <= 0x9FFF for v in value]) < 200:
        low_data_idx.append(key)
        continue
    new_data[key] = remove_long_non_chinese(value)

with open(path, 'w', encoding='utf-8') as fp:
    json.dump(new_data, fp, ensure_ascii=False, indent=4)

import csv

with open('data/deal_data/failed_records/henan_failed.csv', 'r', encoding='utf-8') as fp:
    data = csv.DictReader(fp)
    for row in data:
        low_data_idx.append(row['编号'])

low_data_idx.extend(list(range(int(max(low_data_idx)), 389)))

with open('data/deal_data/index.csv', 'w', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(low_data_idx)
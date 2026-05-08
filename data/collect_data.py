# import os
# import re
# import time
# import requests
# from urllib.parse import urlparse

# SAVE_DIR = r"./data/黄河文化PDF合集"
# TIMEOUT = 30

# # 这里是整理好的链接
# BOOKS = [
#     {
#         "name": "01_Ancient China A History.pdf",
#         "url": "https://library.oapen.org/bitstream/id/60fc5c7c-2525-4559-b6e0-f9780038aa46/9781317503668.pdf",
#     },
#     {
#         "name": "02_The Prehistoric Maritime Frontier of Southeast China.pdf",
#         "url": "https://library.oapen.org/bitstream/id/1640ff31-6598-4d99-a87f-0475dc328cd1/978-981-16-4079-7.pdf",
#     },
#     {
#         "name": "03_Archaeological Research on Cultures in Northeast China.pdf",
#         "url": "https://library.oapen.org/bitstream/20.500.12657/106063/1/9789819771271.pdf",
#     },
#     {
#         "name": "04_The Exercise of the Spatial Imagination in Pre-Modern China.pdf",
#         "url": "https://library.oapen.org/bitstream/20.500.12657/53708/1/9783110749823.pdf",
#     },
#     {
#         "name": "05_Heritage and Romantic Consumption in China.pdf",
#         "url": "https://library.oapen.org/bitstream/id/18bb5c3e-ba7b-4e0f-8c79-4d2a3eb748aa/9789048536825.pdf",
#     },
#     {
#         "name": "06_Rivers of the Anthropocene.pdf",
#         "url": "https://library.oapen.org/bitstream/20.500.12657/31005/1/640458.pdf",
#     },
#     {
#         "name": "07_Urban Life and Intellectual Crisis in Middle-Period China.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/57882/1/9789048554331.pdf",
#     },
#     {
#         "name": "08_Reconsidering Cultural Heritage in East Asia.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/32078/617903.pdf?isAllowed=y&sequence=1",
#     },
#     {
#         "name": "09_China in the World.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/62542/9781478092452.pdf?isAllowed=y&sequence=1",
#     },
#     {
#         "name": "10_Comparative Studies on Chinese and Western Civilizations.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/107650/9789819649945.pdf?sequence=1",
#     },
#     {
#         "name": "11_The Economy of Western Xia.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/49763/9789004461321.pdf?sequence=1",
#     },
#     {
#         "name": "12_The Great Migration from North China to Manchuria.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/41843/1/9780472901753.pdf",
#     },
#     {
#         "name": "13_The Ming Dynasty Its Origins and Evolving Institutions.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/41831/9780472901531.pdf",
#     },
#     {
#         "name": "14_The Origin and Early Development of the Zhou Changes.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/76660/9789004513945.pdf",
#     },
#     {
#         "name": "15_Studies in the History of Chinese Texts.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/86599/9789004540842.pdf",
#     },
#     {
#         "name": "16_Documentation and Argument in Early China.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/50222/9783110708530.pdf?isAllowed=y&sequence=1",
#     },
#     {
#         "name": "17_The Nivison Annals.pdf",
#         "url": "https://library.oapen.org/bitstream/20.500.12657/27403/1/9781501505393.pdf",
#     },
#     {
#         "name": "18_Histories of Spiritual Traditions in China.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/99010/9789004714311_webready_content_text.pdf?isAllowed=y&sequence=1",
#     },
#     {
#         "name": "19_Intangible Cultural Heritage in the Yellow River Basin.pdf",
#         "url": "https://www.mdpi.com/2071-1050/14/17/11073/pdf",
#     },
#     {
#         "name": "20_A Historical Survey of the Yellow River and the River Civilizations.pdf",
#         "url": "https://download.e-bookshelf.de/download/0015/4951/43/L-G-0015495143-0050376311.pdf",
#     },
#     {
#         "name": "21_Colleted Works of Jao Tsung-i.pdf",
#         "url": "https://library.oapen.org/bitstream/id/52243d3a-99fa-47d8-89ad-cecb9d0761ab/9789004522572.pdf",
#     },
#     {
#         "name": "22_Collected Works of Jao Tsung-i Xuantang Anthology.pdf",
#         "url": "https://library.oapen.org/bitstream/20.500.12657/77113/1/9789004522558.pdf",
#     },
#     {
#         "name": "23_Jade-Carving Chisel and Luminous Ocean.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/99009/1/9789004523562_webready_content_text.pdf",
#     },
#     {
#         "name": "24_Understanding Authenticity in Chinese Cultural Heritage.pdf",
#         "url": "https://library.oapen.org/bitstream/id/41c7128d-8d5f-4166-8fca-cb995a7a40d7/9781003290834_DOI%2010.4324_9781003290834-22.pdf",
#     },
#     {
#         "name": "25_Seeking a Future for the Past.pdf",
#         "url": "https://library.oapen.org/bitstream/20.500.12657/86605/1/9780472903764.pdf",
#     },
#     {
#         "name": "26_Writing from Invention to Decipherment.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/94146/9780198908746.pdf?isAllowed=y&sequence=1",
#     },
#     {
#         "name": "27_Bon and Naxi Manuscripts.pdf",
#         "url": "https://library.oapen.org/bitstream/handle/20.500.12657/63503/9783110776478.pdf?isAllowed=y&sequence=1",
#     },
#     {
#         "name": "28_Salt and State.pdf",
#         "url": "https://library.oapen.org/bitstream/id/f67b2eec-ae55-406d-85c4-4abf319ef018/9780472901456.pdf",
#     },
#     {
#         "name": "29_山西省黄河文化保护传承弘扬规划.pdf",
#         "url": "https://wlt.shanxi.gov.cn/xwzx/tzgg/202209/P020241021439100246014.pdf",
#     },
#     {
#         "name": "30_陕西省黄河文化保护传承弘扬规划.pdf",
#         "url": "https://whhlyt.shaanxi.gov.cn/zfxxgk/fdzdgknr/lzyj/tzgg/202103/P020240903544085768960.pdf",
#     },
#     {
#         "name": "31_山东省黄河文化保护传承弘扬规划.pdf",
#         "url": "https://whlyj.taian.gov.cn/module/download/downfile.jsp?filename=f2abc1aa4d744d289a531d6770c23af9.pdf",
#     },
#     {
#         "name": "32_济南市黄河文化保护传承弘扬规划.pdf",
#         "url": "https://www.jinan.gov.cn/jpolicy_file/filedata/2026/02/07/c4d699e77c1144e99a52155929752a1a.pdf",
#     },
#     {
#         "name": "33_山东省黄河流域非物质文化遗产保护传承弘扬规划.pdf",
#         "url": "https://whlyj.taian.gov.cn/module/download/downfile.jsp?classid=0&filename=9e21f127982647f29cc655f868d4b087.pdf",
#     },
#     {
#         "name": "34_陕西黄河文化保护传承弘扬三年行动计划.pdf",
#         "url": "https://whhlyt.shaanxi.gov.cn/zfxxgk/fdzdgknr/lzyj/tzgg/202202/P020240903545618362881.pdf",
#     },
#     {
#         "name": "35_黄河国家文化公园陕西段建设保护规划.pdf",
#         "url": "https://sndrc.shaanxi.gov.cn/sy/xwxx/gggg/202304/P020241105654320857968.pdf",
#     },
#     {
#         "name": "36_黄河流域生态环境保护规划.pdf",
#         "url": "https://www.mee.gov.cn/ywgz/zcghtjdd/ghxx/202206/W020220628597264429830.pdf",
#     },
#     {
#         "name": "37_黄河流域生态保护和高质量发展专项管理办法.pdf",
#         "url": "https://zfxxgk.ndrc.gov.cn/upload/images/20233/202331411314520.pdf",
#     },
#     {
#         "name": "38_十四五规划纲要_含黄河流域相关章节.pdf",
#         "url": "https://www.ndrc.gov.cn/xxgk/zcfb/ghwb/202103/P020210313315693279320.pdf",
#     },
#     {
#         "name": "39_山东省第六批省级非物质文化遗产代表性项目名录.pdf",
#         "url": "https://www.ihchina.cn/Uploads/File/2024/12/23/u676901405c309.pdf",
#     },
#     {
#         "name": "40_山东省省级非物质文化遗产代表性项目名录扩展项目名录.pdf",
#         "url": "https://www.ihchina.cn/Uploads/File/2021/11/23/u619cc944b060a.pdf",
#     },
#     {
#         "name": "41_山西省人民政府办公厅文件_非遗工坊戏曲传承等.pdf",
#         "url": "https://www.ihchina.cn/Uploads/File/2022/12/28/u63abaec805774.pdf",
#     },
#     {
#         "name": "42_山西省十四五文化和旅游产业融合发展规划.pdf",
#         "url": "https://wlt.shanxi.gov.cn/zwgk/xxgk/xxgkml/jwlbf/202201/P020220124569084187321.pdf",
#     },
#     {
#         "name": "43_泰安市黄河流域文化和旅游高质量发展实施意见征求意见稿.pdf",
#         "url": "https://whlyj.taian.gov.cn/module/download/downfile.jsp?classid=0&filename=ef262a1b0e4042a4859245b4f3b7b184.pdf",
#     },
#     {
#         "name": "44_山东省黄河文化保护传承弘扬规划_另一公开入口.pdf",
#         "url": "https://whlyj.taian.gov.cn/module/download/downfile.jsp?classid=0&filename=f5e18bc2d5f64eddb8ff14022ffba90f.pdf",
#     },
#     {
#         "name": "45_World Heritage in China.pdf",
#         "url": "https://unesdoc.unesco.org/ark:/48223/pf0000378344",
#     },
#     {
#         "name": "46_Culture 2030 Rural-Urban Development China at a Glance.pdf",
#         "url": "https://unesdoc.unesco.org/ark:/48223/pf0000368646",
#     },
#     {
#         "name": "47_Asia Conserved Vol IV.pdf",
#         "url": "https://unesdoc.unesco.org/ark:/48223/pf0000374413",
#     },
#     {
#         "name": "48_UNESCO Mission to the Chinese Silk Road as World Cultural Heritage Route.pdf",
#         "url": "https://unesdoc.unesco.org/ark:/48223/pf0000138161",
#     },
#     {
#         "name": "49_Culture for the 2030 Agenda.pdf",
#         "url": "https://unesdoc.unesco.org/ark:/48223/pf0000264687",
#     },
# ]

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/123.0.0.0 Safari/537.36"
#     )
# }


# def sanitize_filename(name: str) -> str:
#     name = re.sub(r'[<>:"/\\\\|?*]', "_", name)
#     name = name.strip().rstrip(".")
#     return name


# def ensure_dir(path: str) -> None:
#     if not os.path.exists(path):
#         os.makedirs(path)


# def guess_ext(content_type: str, url: str) -> str:
#     if "pdf" in content_type.lower():
#         return ".pdf"
#     parsed = urlparse(url)
#     _, ext = os.path.splitext(parsed.path)
#     return ext if ext else ".bin"


# def download_file(session: requests.Session, item: dict, save_dir: str) -> tuple[bool, str]:
#     name = sanitize_filename(item["name"])
#     url = item["url"]
#     path = os.path.join(save_dir, name)

#     if os.path.exists(path) and os.path.getsize(path) > 0:
#         return True, f"已存在，跳过：{name}"

#     try:
#         with session.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT, allow_redirects=True) as r:
#             r.raise_for_status()

#             content_type = r.headers.get("Content-Type", "")
#             if not name.lower().endswith((".pdf", ".html", ".htm", ".bin")):
#                 name += guess_ext(content_type, url)
#                 path = os.path.join(save_dir, name)

#             total = int(r.headers.get("Content-Length", 0))
#             downloaded = 0

#             with open(path, "wb") as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     if chunk:
#                         f.write(chunk)
#                         downloaded += len(chunk)

#             if total > 0 and downloaded == 0:
#                 return False, f"下载为空：{name}"

#             return True, f"下载成功：{name}"

#     except Exception as e:
#         return False, f"{name} | {url} | 错误：{e}"


# def main():
#     ensure_dir(SAVE_DIR)
#     failed_path = os.path.join(SAVE_DIR, "failed.txt")
#     log_path = os.path.join(SAVE_DIR, "download_log.txt")

#     success_count = 0
#     fail_count = 0

#     with requests.Session() as session, \
#          open(failed_path, "w", encoding="utf-8") as failed_file, \
#          open(log_path, "w", encoding="utf-8") as log_file:

#         for idx, item in enumerate(BOOKS, start=1):
#             print(f"[{idx}/{len(BOOKS)}] 正在下载：{item['name']}")
#             ok, msg = download_file(session, item, SAVE_DIR)
#             print(msg)
#             log_file.write(msg + "\n")

#             if ok:
#                 success_count += 1
#             else:
#                 fail_count += 1
#                 failed_file.write(msg + "\n")

#             time.sleep(1)

#     print("\n下载完成")
#     print(f"成功：{success_count}")
#     print(f"失败：{fail_count}")
#     print(f"保存目录：{os.path.abspath(SAVE_DIR)}")


# if __name__ == "__main__":
#     main()

import requests
from lxml import etree

def get_html(url, headers):
    response = requests.get(url=url, headers=headers, timeout=10)
    print(response)
    response.raise_for_status()
    response.encoding = 'utf-8'
    
    html = response.text

    return html

def get_data(html):
    tree = etree.HTML(html)
    
    elements = tree.xpath("//td[@class='tableTd_lcC97']")
    
    all_data = []
    
    for idx, elem in enumerate(elements, 1):
        tag = elem.tag
        
        texts = [el.xpath('string(.)').strip() for el in elem.xpath(".//a | .//span") if el.xpath("string(.)").strip()]
        full_text = ''.join(list(dict.fromkeys(texts)))
        if full_text not in ('序号', '备注', '申报地区或单位', '项目名称', '编号', '-') and not full_text.isdigit():
            all_data.append(full_text)
    
    return all_data

def get_others(html, string):
    tree = etree.HTML(html)
    
    elements = tree.xpath(string)
    
    all_data = []
    for idx, elem in enumerate(elements, 1):
        texts = list(dict.fromkeys([el.xpath('string(.)').strip() for el in elem.xpath(".//a | .//span") if el.xpath("string(.)").strip()]))
        texts = ''.join(texts)   
        
        if texts != '序号 编号 项目名称 申报地区或单位':
            all_data.append(texts.strip())
            texts = ''
    all_data = all_data[8:]
    
    return all_data

import re
import jieba

def is_parenthesized(s):
    s = ''.join(s)
    pattern = r'^[（(][^）)]*[）)]$'
    return bool(re.match(pattern, s))

import re
import jieba

def is_unit_line(word):
    """判断一个词是否为申报单位关键词"""
    unit_keywords = ['文化馆', '村委会', '协会', '剧团', '厂', '公司', '中心',
                     '研究会', '委员会', '村', '镇', '县', '市', '区', '局',
                     '馆', '铺', '团体', '学会', '大学', '厅', '省', '自治区']
    for kw in unit_keywords:
        if kw in word:
            return True
    if word.endswith(('省', '市', '区', '县', '镇', '乡', '村', '厂', '州', '馆', '铺', '委', '团')):
        return True
    return False

def split_data(lines):
    result = {}
    idx = 1
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过标题行、统计行
        if re.match(r'^[一二三四五六七八九十]+、', line):
            continue
        if line.startswith(('序号', '编号', '项目名称', '申报地区', '备注', '保护单位', '类内序号')):
            continue
        # 跳过包含“涉及保护单位”等统计行
        if '涉及保护单位' in line or '扩展项目' in line:
            continue

        # 提取罗马数字编号（支持 Ⅰ-1、Ⅴ7、Ⅷ-10 等格式）
        code_match = re.search(r'([Ⅰ-Ⅹ]-?\d+)', line)
        if not code_match:
            continue
        code = code_match.group(1)
        # 去掉编号部分，剩余内容用于分词
        rest = line[code_match.end():].strip()
        if not rest:
            continue

        # 对剩余部分进行 jieba 分词
        seg_list = list(jieba.cut(rest, cut_all=False))

        name = ''
        unit_parts = []
        i = 0          # 0:项目名称, 1:申报单位
        in_bracket = False

        for word in seg_list:
            # 括号标志（用于避免将括号内的单位关键词误判）
            if '(' in word or '（' in word:
                in_bracket = True
            if ')' in word or '）' in word:
                in_bracket = False

            if i == 0:
                # 收集项目名称，直到遇到单位关键词且不在括号内
                if not in_bracket and is_unit_line(word):
                    i = 1
                    unit_parts.append(word)
                else:
                    name += word
            else:
                unit_parts.append(word)

        # 合并单位部分
        if unit_parts:
            unit_str = ''.join(unit_parts)
            # 按顿号、逗号拆分多个单位
            unit_list = re.split(r'[、，]', unit_str)
            unit_list = [u.strip() for u in unit_list if u.strip()]
            unit_value = unit_list[0] if len(unit_list) == 1 else unit_list
        else:
            unit_value = ''

        # 清理项目名称：去除首尾空格、星号
        name = name.strip(' ﹡*')
        # 过滤无效记录
        if name and unit_value:
            result[idx] = {
                '编号': code,
                '项目名称': name,
                '申报地区或单位': unit_value
            }
            idx += 1
    return result

def structed_data(data):
    result = {}
    idx = 0
    i = 0
    while i < len(data):
        line = data[i].strip()
        if not line:
            i += 1
            continue
        # 判断是否为编号行（包含数字和横杠，且不是单位行）
        if any(ch.isdigit() for ch in line) and '-' in line and not is_unit_line(line):
            code = line
            i += 1
            content = []
            while i < len(data):
                next_line = data[i].strip()
                if next_line and (any(ch.isdigit() for ch in next_line) and '-' in next_line and not is_unit_line(next_line)):
                    break
                if next_line:
                    content.append(next_line)
                i += 1
            # 解析 content
            items = []
            current_name = None
            current_units = []
            for line_content in content:
                if is_unit_line(line_content):
                    current_units.append(line_content)
                else:
                    if current_name is not None:
                        items.append({'name': current_name, 'units': current_units})
                    current_name = line_content
                    current_units = []
            if current_name is not None:
                items.append({'name': current_name, 'units': current_units})
            # 存入结果，跳过申报地区为空的条目
            for item in items:
                units = item['units']
                if not units:   # 申报地区为空，删除
                    continue
                if len(units) == 1:
                    unit_value = units[0]
                else:
                    unit_value = units
                result[idx] = {
                    '编号': code,
                    '项目名称': item['name'],
                    '申报地区或单位': unit_value
                }
                idx += 1
        else:
            i += 1
    return result


import re

def split_multiple_items(line):
    """将一行中包含多个编号项目拆分成多个字符串"""
    pattern = r'(\d*[Ⅰ-ⅩI-X][—\-]?\d+.*?)(?=\d*[Ⅰ-ⅩI-X][—\-]?\d+|$)'
    matches = re.findall(pattern, line)
    if matches:
        return [m.strip() for m in matches if m.strip()]
    return [line.strip()]

def is_title_line(line):
    """判断是否为非数据标题行"""
    line = line.strip()
    if not line:
        return True
    if re.match(r'^[民间传统曲艺杂技生产消费岁时民间信仰知识拓展]', line) and '项' in line:
        return True
    if re.match(r'^[一二三四五六七八九十]+、', line):
        return True
    if line.startswith(('序号', '编号', '项目名称', '申报地区', '备注', '参考资料', '第五批', '为加强', '入选的', '河南省人民政府')):
        return True
    if '非物质文化遗产名录' in line or '传承人' in line or '通知' in line:
        return True
    return False

def extract_code_and_rest(item):
    """提取编号和剩余部分"""
    match = re.search(r'(\d*)([Ⅰ-ⅩI-X][—\-]?\d+)', item)
    if not match:
        return None, item
    code = match.group(2)
    rest = item[match.end():].strip()
    return code, rest

def split_name_and_unit(rest):
    """拆分项目名称和申报单位（优先使用括号内容作为单位）"""
    # 提取最后一个括号内容
    bracket_match = re.search(r'[（(]([^）)]+)[）)]$', rest)
    if bracket_match:
        unit_str = bracket_match.group(1)
        name = rest[:bracket_match.start()].strip()
        name = re.sub(r'[，,、]$', '', name)
        return name, unit_str
    # 无括号，从末尾匹配单位关键词
    unit_keywords = r'(?:省|市|区|县|镇|乡|村|文化馆|协会|公司|中心|剧团|厂|研究会|委员会|保护中心|工作室|合作社|有限公司|艺术团|说唱团|研究所|博物院|歌舞演艺集团|医院|诊所|卫生所|药业|酒业|食品|餐饮|酒店|局|厅|自治区)'
    match = re.search(r'(.*?)(%s[^、，]*)$' % unit_keywords, rest)
    if match:
        name = match.group(1).strip()
        unit_str = match.group(2).strip()
        return name, unit_str
    return rest, ''

def parse_henan_data(lines):
    results = dict()
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if is_title_line(line):
            continue
        items = split_multiple_items(line)
        for item in items:
            code, rest = extract_code_and_rest(item)
            if not code or not rest:
                continue
            name, unit_str = split_name_and_unit(rest)
            if not name or not unit_str:
                continue
            name = re.sub(r'[﹡*\s]+$', '', name)
            unit_list = re.split(r'[、，]', unit_str)
            unit_list = [u.strip() for u in unit_list if u.strip()]
            unit_list = list(dict.fromkeys(unit_list))
            unit_value = unit_list[0] if len(unit_list) == 1 else unit_list
            results[idx] = {
                '编号': code,
                '项目名称': name,
                '申报地区或单位': unit_value
            }
    return results

import re

def parse_shaanxi_clean(lines):
    """
    解析陕西省非遗数据，正确拆分项目名称和申报单位
    """
    # 1. 合并跨行记录
    merged = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过标题行、统计行
        if re.match(r'^[一二三四五六七八九十]+、', line):
            continue
        if line.startswith(('序号', '项目编号', '项目名称', '申报地区')):
            continue
        if re.match(r'^[（(]\d+项[）)]', line):
            continue
        if line in ('民间文学', '传统音乐', '民间舞蹈', '传统戏剧', '曲艺', '竞技', '民间美术', '传统手工技艺', '民俗'):
            continue
        # 包含编号的行作为新记录开始
        if re.search(r'[Ⅰ-ⅩI-V]+[—\-]?\d+', line):
            merged.append(line)
        else:
            if merged:
                merged[-1] += ' ' + line

    # 2. 解析每条记录
    results = {}
    for idx, record in enumerate(merged, 1):
        # 提取编号
        code_match = re.search(r'([Ⅰ-ⅩI-V]+[—\-]?\d+)', record)
        if not code_match:
            continue
        code = code_match.group(1)
        rest = record[code_match.end():].strip()
        if not rest:
            continue

        # 关键：从右向左找到最后一个“市/县/区”的位置
        # 注意：单位通常以“XX市”、“XX县”、“XX区”开头
        last_pos = -1
        for suffix in ['市', '县', '区']:
            pos = rest.rfind(suffix)
            if pos > last_pos:
                last_pos = pos
        if last_pos != -1:
            # 找到最后一个行政区划后缀，将其及其右侧全部内容作为单位
            unit_str = rest[last_pos:].strip()
            name = rest[:last_pos].strip()
            # 进一步修正：如果名称末尾有多余的地名（如“子长唢呐子长”），去除与单位开头重复的部分
            # 提取单位开头的纯地名（例如“子长县” -> “子长”）
            unit_city_match = re.match(r'([^市县区]+)[市县区]', unit_str)
            if unit_city_match:
                city = unit_city_match.group(1)
                if name.endswith(city):
                    name = name[:-len(city)].strip()
        else:
            # 没有找到行政区划，按最后一个空格分割
            parts = rest.rsplit(None, 1)
            if len(parts) == 2:
                name, unit_str = parts
            else:
                name, unit_str = rest, ''

        # 清理项目名称：去除开头的序号、星号、多余空格
        name = re.sub(r'^[★\d\s]+', '', name)
        name = re.sub(r'[﹡*\s]+$', '', name)
        if not name:
            continue

        # 处理申报单位：可能包含多个（用“-”、“、”、“，”或空格分隔）
        if unit_str:
            # 先按“-”分割（陕西数据常见多个单位用短横连接）
            if '-' in unit_str:
                unit_parts = unit_str.split('-')
            else:
                unit_parts = [unit_str]
            final_units = []
            for up in unit_parts:
                up = up.strip()
                if not up:
                    continue
                # 再按顿号、逗号分割
                sub = re.split(r'[、，]', up)
                for s in sub:
                    s = s.strip()
                    if s:
                        final_units.append(s)
            # 去重保留顺序
            final_units = list(dict.fromkeys(final_units))
            unit_value = final_units[0] if len(final_units) == 1 else final_units
        else:
            unit_value = ''

        if name and unit_value:
            results[idx] = {
                '编号': code,
                '项目名称': name,
                '申报地区或单位': unit_value
            }
    return results
        
if __name__ == "__main__":
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36'
    }
    url = 'https://baike.baidu.com/item/%E6%B2%B3%E5%8D%97%E7%9C%81%E7%9C%81%E7%BA%A7%E9%9D%9E%E7%89%A9%E8%B4%A8%E6%96%87%E5%8C%96%E9%81%97%E4%BA%A7%E5%90%8D%E5%BD%95/9595257'
    html = get_html(url, headers)
    # data = get_others(html, "//tbody[@class='tableBody_fpzB1']/tr")
    # print(data)
    # temp_list = parse_shaanxi_clean(data)
    # print(temp_list)
    data = get_others(html, "//div[@class='para_z4tCL content_vE_IE MARK_MODULE']")
    print(data)
    struct_data = parse_henan_data(data)
    
    import json
    # with open('./shanxi1.json', 'w', encoding='utf-8') as fp:
    #     json.dump(temp_list, fp, ensure_ascii=False, indent=4)
        
    with open('./henan2.json', 'w', encoding='utf-8') as fp:
        json.dump(struct_data, fp, ensure_ascii=False, indent=4)
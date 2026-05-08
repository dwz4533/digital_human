import os
import json
import sqlite3

dir_path = './data/'
jsonl_list = [path for path in os.listdir(dir_path) if 'jsonl' in path and 'source' not in path]
print(jsonl_list)

conn = sqlite3.connect(r"./db/long_term_memory.db")
cursor = conn.cursor()

index = 1
# for jsonl in jsonl_list:
#     name = jsonl.split('.')[0]
    # key_value = dict()
    # flag = 1
    # with open(dir_path + jsonl, 'r', encoding='utf-8') as f:
    #     for line in f:
    #         obj = json.loads(line)
    #         if flag:
    #             cursor.execute(
    #                 """CREATE TABLE IF NOT EXISTS heritage(
    #                     id INTEGER PRIMARY KEY,
    #                     province TEXT,
    #                     name TEXT,
    #                     category TEXT,
    #                     level TEXT,
    #                     sn TEXT,
    #                     batch TEXT,
    #                     region TEXT
    #                 )"""
    #             )
    #             flag = 0
    #         for key, value in obj.items():
    #             key_value[key] = value.strip()
    #         cursor.execute(
    #             f"INSERT INTO heritage (id, province, name, category, level, sn, batch, region) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    #             (index,\
    #             name,\
    #             key_value['名称'],\
    #             key_value['类别'],\
    #             key_value.get('级别') or key_value.get('民族'), \
    #             key_value['编号'], \
    #             key_value['批次'],\
    #             key_value['区域'])
    #         )
    #         index += 1
    #         conn.commit()
    
l = []        
for row in cursor.execute(f""" SELECT * FROM memory_store"""):
    print(row)
print(l[1000:1100])
            
            
conn.close()
                
            

# total = dict()
# name = 'gansu'
# for row in cursor.execute(f"""
#                SELECT * FROM {name}
#                """):
#     new_list = dict()
#     idx, new_list['编号'], new_list['项目名称'], new_list['申报地区或单位'], _ = row
#     total[idx] = new_list

# with open(name + '.json', 'w', encoding='utf-8') as fp:
#     json.dump(total, fp, ensure_ascii=False, indent=4)



# for path in json_list:
#     with open(dir_path + path, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     import re
#     table_name = re.sub(r'\d+$', '', path.split('.')[0])
#     print(table_name)
#     for item in data.values():
#         cursor.execute(
#             f"INSERT INTO {table_name} (serial_num, name, declaring_unit) VALUES (?, ?, ?)",
#             (item["编号"], item["项目名称"], ' '.join(item["申报地区或单位"]))
#         )


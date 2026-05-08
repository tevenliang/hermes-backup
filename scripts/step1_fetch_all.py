#!/usr/bin/env python3
"""全量抓取所有页直到无has_more"""
import subprocess, json, re, time, pickle

BASE_TOKEN = 'VNLrbIYoAausDOs5uovcO7fPn0d'
TABLE_ID = 'tbl2vVHnujNPQczd'
VIEW_ID = 'vewLKQab6X'

print('📥 全量抓取所有页...')
all_records = []
all_record_ids = []
offset = 0
limit = 500

while True:
    result = subprocess.run(
        ['lark-cli', 'base', '+record-list',
         '--base-token', BASE_TOKEN,
         '--table-id', TABLE_ID,
         '--view-id', VIEW_ID,
         '--limit', str(limit),
         '--offset', str(offset)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    records = data['data']['data']
    record_ids = data['data']['record_id_list']
    fields = data['data']['fields']
    has_more = data['data']['has_more']

    if not records:
        break

    all_records.extend(records)
    all_record_ids.extend(record_ids)
    print(f'  offset={offset}, +{len(records)} 条, 累计={len(all_records)}, has_more={has_more}')

    if not has_more:
        break
    offset += limit
    time.sleep(0.3)

field_idx = {f: i for i, f in enumerate(fields)}
print(f'\n✅ 全量总记录: {len(all_records)}')

# 按标题去重
title_map = {}
for idx, r in enumerate(all_records):
    rid = all_record_ids[idx]
    full_title = r[field_idx.get('文章标题', 0)] or ''
    title_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', full_title)
    links = re.findall(r'https://feishu\.cn/docx/\w+', full_title)
    url = links[0] if links else ''
    date = r[field_idx.get('添加日期', 3)] or ''
    if title_clean not in title_map:
        title_map[title_clean] = []
    title_map[title_clean].append({'rid': rid, 'url': url, 'date': date})

unique = len(title_map)
dup_groups = sum(1 for t, v in title_map.items() if len(v) > 1)
dup_count = sum(len(v)-1 for t, v in title_map.items() if len(v) > 1)
print(f'去重后独立标题: {unique}')
print(f'重复组: {dup_groups}, 重复记录: {dup_count}')

delete_list = []
for title, versions in title_map.items():
    if len(versions) > 1:
        sorted_v = sorted(versions, key=lambda x: x['date'], reverse=True)
        for v in sorted_v[1:]:
            delete_list.append({'title': title, 'rid': v['rid'], 'date': v['date']})

print(f'\n待删除: {len(delete_list)} 条')
with open('/tmp/all_delete_list.pkl', 'wb') as f:
    pickle.dump(delete_list, f)
print('列表已保存。')

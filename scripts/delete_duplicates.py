#!/usr/bin/env python3
"""批量删除重复记录（保留每组日期最新版本）"""
import subprocess, pickle, time

with open('/tmp/url_status.pkl', 'rb') as f:
    data = pickle.load(f)

url_status = data['url_status']
duplicates = data['duplicates']

# 构建删除列表（每组保留日期最新）
delete_list = []
for title, versions in duplicates.items():
    sorted_v = sorted(versions, key=lambda x: x['date'], reverse=True)
    for v in sorted_v[1:]:  # 保留第0个，删除其余
        delete_list.append({'title': title, 'rid': v['rid'], 'date': v['date']})

print(f'待删除: {len(delete_list)} 条')

# 批量删除（每批10条，休息0.5秒）
BASE_TOKEN = 'VNLrbIYoAausDOs5uovcO7fPn0d'
TABLE_ID = 'tbl2vVHnujNPQczd'
success, failed = 0, 0

for i, d in enumerate(delete_list):
    result = subprocess.run(
        ['lark-cli', 'base', '+record-delete',
         '--base-token', BASE_TOKEN,
         '--table-id', TABLE_ID,
         '--record-id', d['rid'],
         '--yes'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        success += 1
        print(f'✅ [{i+1}/{len(delete_list)}] 删除成功: {d["title"]}')
    else:
        failed += 1
        print(f'❌ [{i+1}/{len(delete_list)}] 删除失败: {d["title"]} | {result.stderr[:100]}')
    if (i + 1) % 10 == 0:
        time.sleep(0.5)

print(f'\n✅ 成功: {success}  ❌ 失败: {failed}')

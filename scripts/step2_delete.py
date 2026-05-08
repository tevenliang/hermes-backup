#!/usr/bin/env python3
"""批量删除重复记录"""
import subprocess, pickle, time

BASE_TOKEN = 'VNLrbIYoAausDOs5uovcO7fPn0d'
TABLE_ID = 'tbl2vVHnujNPQczd'

with open('/tmp/all_delete_list.pkl', 'rb') as f:
    delete_list = pickle.load(f)

print(f'待删除: {len(delete_list)} 条')
success, failed = 0, []

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
        print(f'✅ [{i+1}/{len(delete_list)}] {d["title"][:40]}')
    else:
        failed.append(d)
        print(f'❌ [{i+1}/{len(delete_list)}] {d["title"][:40]} | {result.stderr[:80]}')
    if (i + 1) % 10 == 0:
        time.sleep(0.5)

print(f'\n✅ 成功: {success}  ❌ 失败: {len(failed)}')
if failed:
    print('失败列表:')
    for d in failed:
        print(f'  rid={d["rid"]}  {d["title"]}')

with open('/tmp/failed_deletes.pkl', 'wb') as f:
    pickle.dump(failed, f)

#!/usr/bin/env python3
"""检查飞书文档URL可访问性（使用GET请求）"""
import subprocess
import concurrent.futures
import re
import json
import pickle
import urllib.request

# 读取全部记录
result = subprocess.run(
    ['lark-cli', 'base', '+record-list', '--base-token', 'VNLrbIYoAausDOs5uovcO7fPn0d',
     '--table-id', 'tbl2vVHnujNPQczd', '--view-id', 'vewLKQab6X', '--limit', '500'],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
records = data['data']['data']
fields = data['data']['fields']
record_ids = data['data']['record_id_list']
field_idx = {f: i for i, f in enumerate(fields)}

# 构建 title -> [versions] 映射
title_map = {}
for idx, r in enumerate(records):
    rid = record_ids[idx]
    full_title = r[field_idx['文章标题']] or ''
    title_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', full_title)
    links = re.findall(r'https://feishu\.cn/docx/\w+', full_title)
    url = links[0] if links else ''
    date = r[field_idx['添加日期']] or ''
    if title_clean not in title_map:
        title_map[title_clean] = []
    title_map[title_clean].append({'rid': rid, 'url': url, 'date': date, 'full_title': full_title})

duplicates = {t: v for t, v in title_map.items() if len(v) > 1}

all_items = []
for title, versions in duplicates.items():
    for v in versions:
        if v['url']:
            all_items.append({'title': title, 'rid': v['rid'], 'url': v['url'], 'date': v['date']})

unique_urls = list({item['url'] for item in all_items})
print(f'共 {len(unique_urls)} 个唯一URL需要检测...')

def check_url(url):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return url, resp.status
    except Exception as e:
        err_str = str(e)
        if '404' in err_str or 'Not Found' in err_str:
            return url, 404
        elif 'timeout' in err_str.lower():
            return url, 'timeout'
        else:
            return url, f'error:{err_str[:50]}'

url_status = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(check_url, u): u for u in unique_urls}
    done = 0
    for future in concurrent.futures.as_completed(futures):
        url, status = future.result()
        url_status[url] = status
        done += 1
        print(f'[{done}/{len(unique_urls)}] {status}  {url}')

with open('/tmp/url_status.pkl', 'wb') as f:
    pickle.dump({'url_status': url_status, 'duplicates': duplicates, 'all_items': all_items}, f)
print(f'\n✅ 检查完成，结果已保存到 /tmp/url_status.pkl')

#!/usr/bin/env python3
"""清理多维表格所有跨页重复记录（保留每组日期最新，--limit 200分页）"""
import subprocess, json, re, time

BASE = 'VNLrbIYoAausDOs5uovcO7fPn0d'
TABLE = 'tbl2vVHnujNPQczd'
VIEW = 'vewLKQab6X'

def fetch_all_pages():
    """用 --limit 200 分页抓全量，limit过大会导致记录错乱"""
    all_recs, all_rids = [], []
    offset = 0
    while True:
        r = subprocess.run(
            ['lark-cli', 'base', '+record-list',
             '--base-token', BASE, '--table-id', TABLE, '--view-id', VIEW,
             '--limit', '200', '--offset', str(offset)],
            capture_output=True, text=True
        )
        d = json.loads(r.stdout)
        recs, rids = d['data']['data'], d['data']['record_id_list']
        flds = d['data']['fields']
        has_more = d['data']['has_more']
        all_recs.extend(recs); all_rids.extend(rids)
        print(f'  offset={offset}: +{len(recs)}, 累计={len(all_recs)}, has_more={has_more}')
        if not has_more: break
        offset += 200
        time.sleep(0.3)
    return all_recs, all_rids, flds

def delete_record(rid):
    r = subprocess.run(
        ['lark-cli', 'base', '+record-delete',
         '--base-token', BASE, '--table-id', TABLE,
         '--record-id', rid, '--yes'],
        capture_output=True, text=True
    )
    return r.returncode == 0

def main():
    print('📥 全量抓取（limit=200分页）...')
    all_recs, all_rids, fields = fetch_all_pages()
    fidx = {f: i for i, f in enumerate(fields)}

    title_map = {}
    for idx, rec in enumerate(all_recs):
        rid = all_rids[idx]
        full_title = rec[fidx.get('文章标题', 0)] or ''
        title_clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', full_title)
        date = rec[fidx.get('添加日期', 6)] or ''
        if title_clean not in title_map:
            title_map[title_clean] = []
        title_map[title_clean].append({'rid': rid, 'date': date})

    dup_groups = {t: v for t, v in title_map.items() if len(v) > 1}
    total_dup = sum(len(v) - 1 for v in dup_groups.values())

    print(f'\n总记录: {len(all_recs)}, 独立标题: {len(title_map)}, 重复: {total_dup} 条')
    if total_dup == 0:
        print('✅ 无重复！')
        return

    # 构建删除列表（每组保留日期最新）
    delete_list = []
    for title, versions in dup_groups.items():
        sorted_v = sorted(versions, key=lambda x: x['date'], reverse=True)
        for v in sorted_v[1:]:
            delete_list.append({'title': title, 'rid': v['rid'], 'date': v['date']})

    print(f'待删除: {len(delete_list)} 条\n')
    success, failed = 0, 0
    for i, d in enumerate(delete_list, 1):
        ok = delete_record(d['rid'])
        if ok:
            success += 1
            print(f'✅ [{i}/{len(delete_list)}] {d["title"][:45]}')
        else:
            failed += 1
            print(f'❌ [{i}/{len(delete_list)}] {d["title"][:45]}')
        time.sleep(0.1)

    print(f'\n✅ 成功: {success}  ❌ 失败: {failed}')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""删除所有"最新动态"空文档"""
import subprocess, json

def search_all_news_tokens():
    """通过 docs+search 获取所有最新动态文档 token（正确分页）"""
    all_tokens = []
    page_token = None
    while True:
        args = ['lark-cli', 'docs', '+search', '--query', '最新动态', '--page-size', '20']
        if page_token:
            args += ['--page-token', page_token]
        r = subprocess.run(args, capture_output=True, text=True, timeout=20,
                         cwd='/Users/twliang/.hermes')
        try:
            d = json.loads(r.stdout)
            results = d.get('data', {}).get('results', [])
            for item in results:
                token = item.get('result_meta', {}).get('token', '')
                if token:
                    all_tokens.append(token)
            has_more = d.get('data', {}).get('has_more', False)
            total = d.get('data', {}).get('total', 0)
            print(f'  page: {len(results)} results, total={total}, has_more={has_more}', flush=True)
            if not has_more:
                break
            page_token = d.get('data', {}).get('page_token')
            if not page_token:
                break
        except Exception as e:
            print(f'  search error: {e}')
            break
    return all_tokens

def delete_tokens(tokens):
    """逐个删除 token 列表"""
    deleted = 0
    failed = []
    for i, token in enumerate(tokens):
        r = subprocess.run(
            ['lark-cli', 'drive', '+delete', '--as', 'user',
             '--type', 'docx', '--file-token', token, '--yes'],
            capture_output=True, text=True, timeout=15,
            cwd='/Users/twliang/.hermes'
        )
        if '"ok": true' in r.stdout:
            deleted += 1
        else:
            failed.append(token)
        if (i + 1) % 20 == 0:
            print(f'  进度: {i+1}/{len(tokens)}, 成功{deleted}, 失败{len(failed)}', flush=True)
    return deleted, failed

print('查找所有最新动态文档...')
tokens = search_all_news_tokens()
print(f'共找到 {len(tokens)} 个文档\n')

print(f'开始删除 ({len(tokens)} 个)...')
deleted, failed = delete_tokens(tokens)
print(f'\n完成: 成功 {deleted} / 失败 {len(failed)}')
if failed:
    print(f'失败 token: {failed[:5]}')
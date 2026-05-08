#!/usr/bin/env python3
import subprocess
from datetime import datetime

NOW = datetime.now().strftime('%Y-%m-%d')
CLI = '/root/.openclaw/workspace/skills/tencent-news/tencent-news-cli'

def normalize(text):
    """Normalize ASCII colons to full-width Chinese colons"""
    return text.replace('标题:', '标题：').replace('摘要:', '摘要：').replace('来源:', '来源：').replace('发布时间:', '发布时间：').replace('链接:', '链接：')

def search_tencent(term, limit=3):
    r = subprocess.run([CLI, 'search', term, '--limit', str(limit)],
                      capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return []
    return parse_items(normalize(r.stdout))

def parse_items(text):
    items = []
    current = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '腾讯新闻' in line or '搜索' in line or line.startswith('共 '):
            continue
        if '标题：' in line:
            if current.get('title'):
                items.append(current)
            title = line.split('标题：', 1)[1].strip()
            current = {'title': title}
        elif '摘要：' in line:
            current['summary'] = line.split('摘要：', 1)[1].strip()[:80]
        elif '链接：' in line:
            current['url'] = line.split('链接：', 1)[1].strip()
    if current.get('title'):
        items.append(current)
    return items

def format_topic(icon, name, term):
    out = []
    out.append(f'## {icon} {name}')
    items = search_tencent(term, 3)
    for item in items:
        title = item.get('title', '')
        summary = item.get('summary', '')
        url = item.get('url', '')
        out.append(f'### {title}')
        if summary:
            out.append(f'*{summary}*')
        if url:
            out.append(f'🔗 [查看原文]({url})')
    return '\n'.join(out)

lines = []
lines.append(f'# 📰 每日资讯动态（{NOW}）')
lines.append('')
lines.append('## 【第一部分】自定义话题')
lines.append('')
lines.append(format_topic('🤖', 'AI工具/OpenClaw', 'OpenClaw 2026 最新更新'))
lines.append('')
lines.append(format_topic('📱', '飞书动态', '飞书 2026 最新功能更新'))
lines.append('')
lines.append(format_topic('🌍', '美以伊局势', '伊朗 美国 以色列 战争 2026 最新'))
lines.append('')
lines.append(format_topic('🏀', '文班亚纳', '文班亚纳 NBA'))
lines.append('')
lines.append(format_topic('💻', 'AI Coding', 'AI Coding 2026 最新'))
lines.append('')

# Part 2: hot
r_hot = subprocess.run([CLI, 'hot'], capture_output=True, text=True, timeout=10)
hot_items = []
if r_hot.returncode == 0:
    text = normalize(r_hot.stdout)
    current = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or '腾讯新闻' in line:
            continue
        if '标题：' in line:
            if current.get('title'):
                hot_items.append(current)
            current = {'title': line.split('标题：', 1)[1].strip()}
        elif '摘要：' in line:
            current['summary'] = line.split('摘要：', 1)[1].strip()[:80]
        elif '来源：' in line:
            current['source'] = line.split('来源：', 1)[1].strip()
        elif '发布时间：' in line:
            current['time'] = line.split('发布时间：', 1)[1].strip()
        elif '链接：' in line:
            current['url'] = line.split('链接：', 1)[1].strip()

lines.append('## 【第二部分】🔥 腾讯新闻热点榜')
lines.append('')
for i, item in enumerate(hot_items[:10], 1):
    title = item.get('title', '')
    summary = item.get('summary', '')
    source = item.get('source', '')
    time = item.get('time', '')
    url = item.get('url', '')
    lines.append(f'### {i}. {title}')
    if summary:
        lines.append(f'*{summary}*')
    if source or time:
        lines.append(f'📰 {source} · {time}')
    if url:
        lines.append(f'🔗 [查看原文]({url})')
    lines.append('')

report = '\n'.join(lines)
print(report)
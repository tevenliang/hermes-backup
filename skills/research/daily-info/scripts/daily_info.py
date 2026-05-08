#!/usr/bin/env python3
"""
每日资讯动态 - 改造版 v2
参考 daily-ai-news-skill 四阶段设计：
  Phase 1: 信息收集
  Phase 2: 内容过滤（时间过滤、去重）
  Phase 3: 分类整理（5大类别）
  Phase 4: 格式化输出 + 今日要点
"""
import subprocess, urllib.request, json, re, time
from datetime import datetime, timedelta

NOW = datetime.now()
NOW_STR = NOW.strftime('%Y-%m-%d')
CLI_TENCENT = '/Users/twliang/.tencent-news-cli/bin/tencent-news-cli'
CLI_WECHAT = '/Users/twliang/.hermes/skills/workspace/wechat-article-search/scripts/search_wechat.js'
CUTOFF_HOURS = 48  # 只保留最近48小时内容

# ========== 飞书配置 ==========
FEISHU_APP_ID = "cli_a97cf4a2bef8dcce"
FEISHU_APP_SECRET = "BQEEuScBOAzPa0ywZBpJue4y5wOFuP55"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"
WORKSPACE = "/Users/twliang/.hermes"

# ========== lark-cli 封装 ==========
def lark_cli(cmd_list, data_str=None):
    import subprocess, json
    args = ["lark-cli"] + cmd_list
    if data_str is not None:
        args += ["--data", "-"]
    proc = subprocess.run(args, input=data_str, capture_output=True, text=True, timeout=30, cwd=WORKSPACE)
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except:
            return {"ok": False, "error": proc.stdout}
    return {"ok": False, "error": proc.stderr or proc.stdout}

# ========== 工具函数 ==========

def normalize(text):
    return (text.replace('标题:', '标题：')
              .replace('摘要:', '摘要：')
              .replace('来源:', '来源：')
              .replace('发布时间:', '发布时间：')
              .replace('链接:', '链接：'))

def parse_tencent_search(text):
    items = []
    current = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or '腾讯新闻' in line or '搜索' in line or line.startswith('共 '):
            continue
        if '标题：' in line:
            if current.get('title'):
                items.append(current)
            current = {'title': line.split('标题：', 1)[1].strip(), 'source': '腾讯新闻'}
        elif '摘要：' in line:
            current['summary'] = line.split('摘要：', 1)[1].strip()
        elif '发布时间：' in line:
            current['date'] = line.split('发布时间：', 1)[1].strip()
        elif '链接：' in line:
            current['url'] = line.split('链接：', 1)[1].strip()
    if current.get('title'):
        items.append(current)
    return items

def parse_tencent_hot(text):
    items = []
    current = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or '腾讯新闻' in line:
            continue
        if '标题：' in line:
            if current.get('title'):
                items.append(current)
            current = {'title': line.split('标题：', 1)[1].strip(), 'source': '腾讯新闻热点'}
        elif '摘要：' in line:
            current['summary'] = line.split('摘要：', 1)[1].strip()
        elif '来源：' in line:
            current['author'] = line.split('来源：', 1)[1].strip()
        elif '发布时间：' in line:
            current['date'] = line.split('发布时间：', 1)[1].strip()
        elif '链接：' in line:
            current['url'] = line.split('链接：', 1)[1].strip()
    if current.get('title'):
        items.append(current)
    return items

def search_tencent(term, limit=5):
    r = subprocess.run([CLI_TENCENT, 'search', term, '--limit', str(limit)],
                      capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return []
    return parse_tencent_search(normalize(r.stdout))

def search_wechat(term, limit=3):
    r = subprocess.run(['node', CLI_WECHAT, term, '-n', str(limit)],
                      capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return []
    try:
        data = json.loads(r.stdout)
        items = []
        for it in data if isinstance(data, list) else data.get('results', data.get('data', [])):
            items.append({
                'title': it.get('title', ''),
                'summary': it.get('abstract', it.get('summary', '')),
                'url': it.get('url', it.get('link', '')),
                'source': it.get('account', '微信公众号'),
                'date': it.get('date', it.get('time', '')),
            })
        return items
    except:
        return []

def fetch_wallstreetcn_hot(limit=8):
    try:
        url = f'https://api-one-wscn.awtmt.com/apiv1/content/information-flow?channel=global&accept=article&limit={limit}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
        items = d.get('data', {}).get('items', [])
        result = []
        for it in items:
            rsrc = it.get('resource', {})
            ts = rsrc.get('display_time', 0)
            date = datetime.fromtimestamp(ts).strftime('%m-%d %H:%M') if ts else ''
            result.append({
                'title': rsrc.get('title', ''),
                'summary': rsrc.get('content_short', '')[:100],
                'url': rsrc.get('uri', ''),
                'source': '华尔街见闻',
                'date': date,
            })
        return result
    except Exception as e:
        return []

def fetch_tencent_hot(limit=10):
    r = subprocess.run([CLI_TENCENT, 'hot'], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return []
    items = parse_tencent_hot(normalize(r.stdout))
    return items[:limit]

# ========== Phase 2: 时间过滤 ==========

def is_recent(date_str, cutoff_hours=48):
    """判断内容是否在时间范围内"""
    if not date_str:
        return True  # 没有时间戳的默认保留
    # 尝试解析格式如 "2026-04-27 07:57" 或 "04-27 11:10"
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m-%d %H:%M:%S', '%m-%d %H:%M', '%Y-%m-%d', '%m-%d']:
        try:
            d = datetime.strptime(date_str.strip(), fmt)
            if fmt == '%m-%d %H:%M':
                d = d.replace(year=NOW.year)
            age = (NOW - d).total_seconds() / 3600
            return age <= cutoff_hours
        except:
            pass
    return True  # 解析失败的默认保留

# ========== Phase 3: 分类 ==========

CATEGORIES = {
    '🔥 重大事件': ['战争', '地震', '灾情', '疫情', '爆炸', '死亡', '袭击', '坠机', '大选', '黑天鹅', '突发', '重磅', '枪击', '谈判破裂'],
    '🌏 国际时政': ['美国', '中国', '俄罗斯', '欧盟', '以色列', '伊朗', '中东', '乌克兰', '北约', '外交', '制裁', '峰会', '特朗普', '拜登'],
    '🤖 AI科技': ['AI', 'ChatGPT', '大模型', 'DeepSeek', 'OpenAI', 'Anthropic', 'Google', 'Meta', '微软', '英伟达', '芯片', '模型', '智能体', 'Agent'],
    '💻 科技互联网': ['腾讯', '阿里', '字节', '百度', '京东', '小米', '华为', '苹果', '特斯拉', '车企', '电商', '融资', '创业'],
    '🏀 文体娱乐': ['NBA', '文班', '詹姆斯', '湖人', '勇士', '足球', '欧冠', '电影', '明星', '演唱会'],
}

def categorize(item):
    text = (item.get('title', '') + ' ' + item.get('summary', '')).lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return '📋 综合'

def format_item(item):
    """格式化单条内容"""
    title = item.get('title', '')
    summary = item.get('summary', '')
    url = item.get('url', '')
    source = item.get('source', item.get('author', ''))
    date = item.get('date', '')
    cat = categorize(item)

    parts = []
    parts.append(f"### {title}")
    if summary:
        parts.append(summary)
    meta = ' · '.join(x for x in [source, date] if x)
    if meta:
        parts.append(f"📰 {meta}")
    if url:
        parts.append(f"🔗 [查看原文]({url})")
    parts.append(f"📂 {cat}")
    return '\n'.join(parts)

# ========== Phase 1: 收集所有内容 ==========

def collect_all():
    """收集所有来源内容"""
    all_items = []

    # Part 1: 5个话题
    topics = [
        ('🤖', 'AI工具/OpenClaw', 'OpenClaw 2026 最新更新'),
        ('📱', '飞书动态', '飞书 2026 最新功能更新'),
        ('🌍', '美以伊/国际局势', '伊朗 美国 以色列 战争 最新动态'),
        ('🏀', '文班亚纳/体育', '文班亚纳 NBA 马刺'),
        ('💻', 'AI Coding', 'AI Coding 开发工具 2026'),
    ]

    for icon, name, term in topics:
        for it in search_tencent(term, 5):
            all_items.append(it)
        for it in search_wechat(term, 3):
            all_items.append(it)

    # Part 2: 腾讯热点
    for it in fetch_tencent_hot(10):
        all_items.append(it)

    # Part 3: 华尔街见闻
    for it in fetch_wallstreetcn_hot(8):
        all_items.append(it)

    # 去重（按标题）
    seen = set()
    unique = []
    for it in all_items:
        key = it.get('title', '')
        if key and key not in seen:
            seen.add(key)
            unique.append(it)

    return unique

# ========== Phase 4: 输出 ==========

def build_output():
    all_items = collect_all()
    cutoff = NOW - timedelta(hours=CUTOFF_HOURS)

    # 分类容器
    cats = {cat: [] for cat in list(CATEGORIES.keys()) + ['📋 综合']}
    cats['🔥 今日要点'] = []

    for item in all_items:
        date_str = item.get('date', '')
        # 时间过滤
        if date_str and not is_recent(date_str, CUTOFF_HOURS):
            continue

        cat = categorize(item)
        cats[cat].append(item)

    # 构建输出
    lines = []
    lines.append(f'# 📰 每日资讯动态（{NOW_STR}）')
    lines.append('')
    lines.append(f'> 四阶段：信息收集 → 时间过滤(48h) → 分类整理 → 今日要点')
    lines.append('')

    # Phase 3: 按类别输出
    for cat_name in list(CATEGORIES.keys()) + ['📋 综合']:
        items = cats.get(cat_name, [])
        if not items:
            continue
        lines.append(f'## {cat_name}（{len(items)}条）')
        lines.append('')
        for i, item in enumerate(items, 1):
            lines.append(format_item(item))
            lines.append('')

    # Phase 4: 今日要点
    lines.append('## 🎯 今日要点')
    lines.append('')

    # 从各大类挑最重要的
    highlights = []
    for cat_name in ['🔥 重大事件', '🌏 国际时政', '🤖 AI科技']:
        items = cats.get(cat_name, [])
        if items:
            highlights.append(f"- **{items[0].get('title', '')}**")
            if len(items) > 1:
                highlights.append(f"  ↗ 还有 {len(items)-1} 条相关更新")

    # 文班特别加一条
    wangban = cats.get('🏀 文体娱乐', [])
    if wangban:
        highlights.append(f"- 🏀 **{wangban[0].get('title', '')}**")

    if highlights:
        lines.extend(highlights)
    else:
        lines.append('- 今日资讯已整理完毕，各类别更新见上方详情')

    lines.append('')
    lines.append(f'_生成时间：{NOW.strftime("%H:%M")}_')

    return '\n'.join(lines)

if __name__ == '__main__':
    t0 = time.time()
    output = build_output()
    elapsed = time.time() - t0

    # 写入临时 markdown 文件
    import os
    os.makedirs("/Users/twliang/.hermes/tmp", exist_ok=True)
    md_path = "/Users/twliang/.hermes/tmp/daily_info.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(output)

    # 创建飞书文档
    doc_title = f"每日资讯动态 {NOW_STR}"
    print("[创建飞书文档...]")
    result = lark_cli([
        "docs", "+create",
        "--title", doc_title,
        "--markdown", "@./tmp/daily_info.md",
        "--as", "user",
        "--folder-token", FOLDER_TOKEN,
    ])
    if result.get("ok"):
        doc_url = result.get("data", {}).get("doc_url", "（无URL）")
        print(f"\n{'='*50}")
        print(f"📰 每日资讯动态 {NOW_STR}")
        print(f"🔗 {doc_url}")
        print(f"{'='*50}")
    else:
        print(f"\n❌ 文档创建失败: {result.get('error', 'unknown')}")
    print(f"[耗时 {elapsed:.1f}秒]")
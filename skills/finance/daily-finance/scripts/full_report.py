#!/usr/bin/env python3
"""每日财经动态 - 一次性完整输出"""
import urllib.request, re, json, subprocess, os
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')

# ==================== 基金净值 ====================
funds = {
    '018125': '永赢先进制造',
    '015790': '永赢高端装备',
    '017193': '天弘工业有色',
    '016858': '国金量化多因子',
    '002943': '广发多因子',
    '012922': '易方达全球成长(QDII)',
    '017290': '中欧科创主题',
    '002963': '易方达黄金ETF'
}

fund_results = []
for code, name in funds.items():
    url = f'https://fundgz.1234567.com.cn/js/{code}.js'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read().decode()
            m = re.search(r'\((.+)\)', data)
            if m:
                d = json.loads(m.group(1))
                gsz = d.get('gsz', '-')
                zdf = d.get('gszzl', '-')
                fund_results.append(f"  {name}（{code}）：{gsz}（{zdf}%）")
    except:
        fund_results.append(f"  {name}（{code}）：获取失败")

# ==================== A股指数 ====================
index_results = []
try:
    from thsdk import THS
    with THS() as ths:
        for code, name in [('USHI1A0001','上证指数'),('USZI399001','深证成指'),('USZI399006','创业板指'),('USHI1B0688','科创50')]:
            try:
                resp = ths.market_data_cn(code)
                if not resp.df.empty:
                    row = resp.df.iloc[0]
                    price = float(row['价格'])
                    yesterday = float(row['昨收价'])
                    pct = (price - yesterday) / yesterday * 100
                    index_results.append(f"  {name}：{price:.2f}（{pct:+.2f}%）")
            except:
                index_results.append(f"  {name}：获取失败")
except:
    index_results.append("  同花顺连接失败（游客权限限制）")

# ==================== 板块资讯 ====================
TN = '/root/.openclaw/workspace/skills/tencent-news'
news_results = {}
sectors = [
    ('CPO 共封装光学 2026', '💡 CPO（共封装光学）'),
    ('黄金 价格 2026', '🥇 黄金'),
    ('美股 纳斯达克 标普500 道琼斯 收盘 2026', '🇺🇸 美股'),
    ('恒生指数 收盘 2026', '🇭🇰 港股'),
]
for kw, label in sectors:
    try:
        r = subprocess.run(
            f'cd {TN} && ./tencent-news-cli search "{kw}" --limit 2 2>/dev/null',
            shell=True, capture_output=True, text=True, timeout=20
        )
        lines = r.stdout.strip().split('\n')
        entries = []
        title = ''
        for line in lines:
            line_stripped = line.strip()
            # 跳过标题行和空行
            if not line_stripped or line_stripped.startswith('【') or line_stripped.startswith('共 '):
                continue
            # 解析标题行（可能有 "1. 标题：" 前缀）
            if '标题：' in line_stripped:
                title = line_stripped.split('标题：')[1].strip()
            # 解析摘要行
            elif '摘要:' in line_stripped and title:
                summary = line_stripped.split('摘要:')[1].strip()
                entries.append((title, summary))
                title = ''
        news_results[label] = entries
    except Exception as e:
        news_results[label] = []

# ==================== 输出 ====================
out = []
out.append(f"📊 每日财经动态（{today}）")
out.append("")
out.append("━━━━━━━━━━━━━━━━━━━━━━")
out.append("📈 基金净值")
out.append("━━━━━━━━━━━━━━━━━━━━━━")
for l in fund_results:
    out.append(l)
out.append("")
out.append("━━━━━━━━━━━━━━━━━━━━━━")
out.append("📊 大盘指数")
out.append("━━━━━━━━━━━━━━━━━━━━━━")
out.append("【A股】")
for l in index_results:
    out.append(l)
out.append("")
out.append("━━━━━━━━━━━━━━━━━━━━━━")
out.append("🏭 关注板块动态")
out.append("━━━━━━━━━━━━━━━━━━━━━━")
for label, entries in news_results.items():
    out.append(label)
    if entries:
        for i, (title, summary) in enumerate(entries[:2], 1):
            out.append(f"  {i}. {title}")
            out.append(f"     {summary}")
    else:
        out.append("  暂无最新资讯")
    out.append("")

print('\n'.join(out))

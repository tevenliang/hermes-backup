#!/usr/bin/env python3
"""每日基金净值 - 快速抓取+直接输出"""
import urllib.request, re, json
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')

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

lines = [f"📈 基金净值（{today}）", ""]
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
                lines.append(f"{name}（{code}）：{gsz}（{zdf}%）")
            else:
                lines.append(f"{name}（{code}）：获取失败")
    except Exception as e:
        lines.append(f"{name}（{code}）：获取失败")

print('\n'.join(lines))

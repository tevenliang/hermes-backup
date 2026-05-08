#!/usr/bin/env python3
"""
每日财经信息推送
合并：基金净值 + 基金持仓股票新闻 → 写入单一文档「每日财经动态」
推送时间：工作日 08:00
"""

import urllib.request
import urllib.error
import re
import json
import sys
from datetime import datetime

FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FEISHU_USER_ID = "ou_d4b39b86c8715f79b2c5b070c4e55393"
FEISHU_DOC_TOKEN = "WswedVkvpoeXCLxmp87c9vK8nCK"   # 每日财经动态（合并文档）

FUNDS = {
    '018125': '永赢先进制造智选混合C',
    '015790': '永赢高端装备智选混合C',
    '017193': '天弘中证工业有色金属ETF联接C',
    '016858': '国金量化多因子股票C',
    '002943': '广发多因子混合',
    '012922': '易方达全球成长精选混合(QDII)C',
    '017290': '中欧科创主题混合(LOF)C',
    '002963': '易方达黄金ETF联接C',
}
FUND_TYPES = {
    '018125': '混合', '015790': '混合', '017193': 'ETF联接',
    '016858': '股票', '002943': '混合', '012922': 'QDII',
    '017290': 'LOF', '002963': '黄金ETF',
}
FUND_SEQ = ['018125', '015790', '017193', '016858', '002943', '012922', '017290', '002963']
FUND_ORDER = {code: i+1 for i, code in enumerate(FUND_SEQ)}
FUND_NAMES_CN = {
    '018125': '永赢先进制造智选混合C（018125）',
    '015790': '永赢高端装备智选混合C（015790）',
    '017193': '天弘中证工业有色金属ETF联接C（017193）',
    '016858': '国金量化多因子股票C（016858）',
    '002943': '广发多因子混合（002943）',
    '012922': '易方达全球成长精选混合(QDII)C（012922）',
    '017290': '中欧科创主题混合(LOF)C（017290）',
    '002963': '易方达黄金ETF联接C（002963）',
}

# ==================== 飞书基础方法 ====================

def get_token():
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())["tenant_access_token"]

def send_feishu(message):
    try:
        token = get_token()
        payload = json.dumps({
            "receive_id": FEISHU_USER_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message})
        }).encode()
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            data=payload, method="POST"
        )
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read()).get("code") == 0
    except Exception as e:
        print(f"  飞书发送失败: {e}", file=sys.stderr)
        return False

def get_doc_root_id(doc_token, token):
    """获取文档根 block_id（直接用 doc_token，即 page block，支持添加 children）"""
    return doc_token

def clear_doc_content(doc_token, token):
    """清空文档所有子 blocks（必须带 document_revision_id=-1 才能获取真实children）"""
    deleted_count = 0
    while True:
        # 必须带 document_revision_id=-1 否则只返回 page block 本身，没有 children
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks?document_revision_id=-1&page_size=500"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {token}")
        try:
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read()).get("data", {})
            items = data.get("items", [])
        except Exception as e:
            print(f"    ⚠️ 获取文档块失败: {e}")
            break

        # 找根节点的直接子块（parent_id == doc_token）
        root_children = [
            b["block_id"] for b in items
            if b.get("parent_id") == doc_token
        ]

        if not root_children:
            break

        for block_id in root_children:
            del_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{block_id}"
            del_req = urllib.request.Request(del_url, method="DELETE")
            del_req.add_header("Authorization", f"Bearer {token}")
            try:
                urllib.request.urlopen(del_req, timeout=15)
                deleted_count += 1
            except Exception:
                pass
    print(f"    🗑️ 清空文档完成，删除了 {deleted_count} 个块")

def append_blocks_with_retry(doc_token, blocks, token, retries=3, timeout=60, batch_size=50):
    """追加 blocks 到文档（分批写入，每批最多50个block）"""
    root_id = get_doc_root_id(doc_token, token)
    total = len(blocks)
    for i in range(0, total, batch_size):
        batch = blocks[i:i+batch_size]
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{root_id}/children"
        payload = json.dumps({"children": batch, "index": -1}).encode()
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, data=payload, method="POST")
                req.add_header("Authorization", f"Bearer {token}")
                req.add_header("Content-Type", "application/json")
                resp = urllib.request.urlopen(req, timeout=timeout)
                result = json.loads(resp.read())
                if result.get("code") == 0:
                    break
                else:
                    print(f"    ⚠️ 写入失败，code={result.get('code')}，重试 {attempt+1}/{retries}")
            except Exception as e:
                print(f"    ⚠️ 超时/异常 ({attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                import time
                time.sleep(5 * (attempt + 1))  # 递增等待
        else:
            return False
    return True

# 兼容旧名
append_blocks = append_blocks_with_retry

# ==================== 数据获取 ====================

def get_fund_nav_api(code, name):
    try:
        url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode("utf-8")
        m = re.search(r'\((\{.*\})\)', text)
        if m:
            data = json.loads(m.group(1))
            gsz = float(data.get('gsz', 0))
            gszzl = float(data.get('gszzl', 0))
            return {"code": code, "name": data.get('name', name),
                    "nav": gsz, "change_today": gszzl, "date": data.get('gztime', '')}
    except:
        pass
    return None

def get_fund_yesterday_change(code):
    import datetime
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://fund.eastmoney.com/'}
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=5"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        records = data.get('Data', {}).get('LSJZList', [])
        if records:
            return float(records[0].get('JZZZL', 0))
    except:
        pass
    return None

def get_fund_holdings(code, fund_name):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=5&year=2025&month=12"
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode('utf-8').replace('\n', '').replace('\r', '')
        pattern = r"<td>(\d+)</td><td><a href='//quote\.eastmoney\.com/unify/r/(\d+)\.(\d+)'[^>]*>([^<]+)</a></td><td class='tol'><a[^>]*>([^<]+)</a>"
        matches = re.findall(pattern, text)
        holdings = []
        for seq, mkt, stock_code, _, name in matches[:5]:
            mkt_code = int(mkt)
            if mkt_code == 0:
                full_code = f"{stock_code}.SZ"
            elif mkt_code == 1:
                full_code = f"{stock_code}.SH"
            elif mkt_code == 116:
                full_code = f"hk{stock_code}"
            else:
                full_code = f"{mkt}.{stock_code}"
            holdings.append({'code': full_code, 'name': name, 'fund': fund_name})
        return holdings
    except:
        return []

def get_stock_news(stock_code):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        code_raw = stock_code.replace('.SH', '').replace('.SZ', '').replace('hk', '')
        if stock_code.startswith('hk'):
            return []
        url = f'https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1&page_size=3&page_index=1&ann_type=SHA%2CSZA&client_source=web&stock_list={code_raw}'
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        items = data.get('data', {}).get('list', [])
        return [{'title': i.get('title', '')[:50], 'date': i.get('notice_date', '')[:10],
                 'art_code': i.get('art_code', '')} for i in items]
    except:
        return []

# ==================== 文档写入 ====================

def write_combined_doc(fund_data_list, news_data_by_fund, date_str, token):
    """
    写入合并文档：每个日期一个完整section
    结构：日期标题 → 基金净值表格 → 持仓新闻（按基金分组）
    """
    clear_doc_content(FEISHU_DOC_TOKEN, token)

    blocks = []

    # 大标题
    blocks.append({
        "block_type": 3,
        "heading1": {
            "elements": [{"text_run": {"content": f"📊 每日财经动态"}}],
            "style": {"align": 1, "folded": False}
        }
    })
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": "由贾维斯自动维护 | 闻哥的财经情报站", "text_element_style": {"bold": True}}}],
            "style": {"align": 1, "folded": False}
        }
    })
    blocks.append({"block_type": 22, "divider": {}})

    # ===== Part 1: 日期 + 基金净值 =====
    blocks.append({
        "block_type": 4,
        "heading2": {
            "elements": [{"text_run": {"content": f"📅 {date_str} · 基金净值"}}],
            "style": {"align": 1, "folded": False}
        }
    })

    # 表头
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {
                "content": "代码        名称                             净值            昨日涨跌      今日估算",
                "text_element_style": {"bold": True}
            }}],
            "style": {"align": 1, "folded": False}
        }
    })

    for fund in fund_data_list:
        name = fund.get("name", "")[:22]
        code = fund.get("code", "")
        nav = fund.get("nav", "-")
        cy = fund.get("change_yesterday", 0)
        ct = fund.get("change_today", 0)
        cy_str = f"{cy:+.2f}%" if isinstance(cy, (int, float)) else "-"
        ct_str = f"{ct:+.2f}%" if isinstance(ct, (int, float)) else "-"
        nav_str = f"{nav:.4f}" if isinstance(nav, (int, float)) and nav else "-"
        emoji_y = "🔴" if (isinstance(cy, (int, float)) and cy < 0) else "🟢" if (isinstance(cy, (int, float)) and cy > 0) else "⚪"
        blocks.append({
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": f"{emoji_y}{code}  {name:<24}  {nav_str:>10}  {cy_str:>10}  {ct_str:>10}"}}],
                "style": {"align": 1, "folded": False}
            }
        })

    blocks.append({"block_type": 22, "divider": {}})

    # ===== Part 2: 持仓股票新闻 =====
    blocks.append({
        "block_type": 4,
        "heading2": {
            "elements": [{"text_run": {"content": f"📰 {date_str} · 持仓股票最新公告"}}],
            "style": {"align": 1, "folded": False}
        }
    })
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {
                "content": "数据来源：东方财富基金持仓披露 + 上市公司公告 | 涉及基金：永赢先进制造、永赢高端装备、天弘工业有色、国金量化、广发多因子、中欧科创（黄金ETF/QDII无持仓数据）",
                "text_element_style": {"italic": True}
            }}],
            "style": {"align": 1, "folded": False}
        }
    })

    chinese_nums = '零一二三四五六七八九'
    has_news = False
    for fund_code in FUND_SEQ:
        items = news_data_by_fund.get(fund_code, [])
        if not items:
            continue
        has_news = True
        order = FUND_ORDER.get(fund_code, 0)
        blocks.append({
            "block_type": 5,
            "heading3": {
                "elements": [{"text_run": {"content": f"{chinese_nums[order]}、{FUND_NAMES_CN.get(fund_code, fund_code)}"}}],
                "style": {"align": 1, "folded": False}
            }
        })
        for item in items:
            name = item.get('name', '')[:10]
            code = item.get('code', '')
            title = item.get('title', '')[:36]
            date = item.get('date', '')
            art_code = item.get('art_code', '')
            url = f"https://np-anotice-stock.eastmoney.com/#/detail?art_code={art_code}&ann_type=SHA%2CSZA&client_source=web&page=1"
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {
                        "content": f"  • {name:<10} {code:<14} {title:<36} {date}",
                        "link": {"url": url}
                    }}],
                    "style": {"align": 1, "folded": False}
                }
            })

    if not has_news:
        blocks.append({
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": "（今日无持仓公告更新）"}}],
                "style": {"align": 1, "folded": False}
            }
        })

    blocks.append({"block_type": 22, "divider": {}})
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": f"🤖 由贾维斯自动生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}", "text_element_style": {"italic": True}}}],
            "style": {"align": 1, "folded": False}
        }
    })

    return append_blocks(FEISHU_DOC_TOKEN, blocks, token)

# ==================== 主程序 ====================

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"📊 每日财经推送开始... ({today})")

    # --- Part 1: 基金净值 ---
    print("\n=== 基金净值 ===")
    fund_data_list = []
    for code, name in FUNDS.items():
        print(f"  → {name}...", end=" ", flush=True)
        data = get_fund_nav_api(code, name)
        if data:
            yest = get_fund_yesterday_change(code)
            if yest is not None:
                data["change_yesterday"] = yest
            fund_data_list.append(data)
            ct = data.get("change_today", 0)
            cy = data.get("change_yesterday", 0)
            print(f"净值={data.get('nav','-')}, 昨日={cy:+.2f}%, 今日估算={ct:+.2f}%")
        else:
            print("获取失败")

    # --- Part 2: 持仓新闻（按基金分组）---
    print("\n=== 持仓股票新闻 ===")
    news_data_by_fund = {}  # fund_code -> list of news items
    for code, fund_name in FUNDS.items():
        print(f"  → {fund_name} 持仓...", end=" ", flush=True)
        holdings = get_fund_holdings(code, fund_name)
        print(f"获取 {len(holdings)} 只")
        for h in holdings:
            news = get_stock_news(h['code'])
            if news:
                for n in news[:2]:
                    if code not in news_data_by_fund:
                        news_data_by_fund[code] = []
                    news_data_by_fund[code].append({
                        'fund': fund_name,
                        'name': h['name'],
                        'code': h['code'],
                        'title': n['title'],
                        'date': n['date'],
                        'art_code': n.get('art_code', '')
                    })

    # --- 构建飞书推送消息 ---
    msg = f"📊 每日财经动态 {today}\n"
    msg += "=" * 38 + "\n"

    msg += "\n💹 基金净值\n" + "-" * 38 + "\n"
    categories = {}
    for f in fund_data_list:
        cat = FUND_TYPES.get(f.get("code", ""), "其他")
        categories.setdefault(cat, []).append(f)
    for cat, funds in categories.items():
        msg += f"【{cat}】\n"
        for fund in funds:
            name = fund.get("name", "")[:20]
            code = fund.get("code", "")
            nav = fund.get("nav", "-")
            cy = fund.get("change_yesterday", 0)
            ct = fund.get("change_today", 0)
            cy_str = f"{cy:+.2f}%" if isinstance(cy, (int, float)) else "-"
            ct_str = f"{ct:+.2f}%" if isinstance(ct, (int, float)) else "-"
            nav_str = f"{nav:.4f}" if isinstance(nav, (int, float)) and nav else "-"
            emoji_y = "🔴" if (isinstance(cy, (int, float)) and cy < 0) else "🟢" if (isinstance(cy, (int, float)) and cy > 0) else "⚪"
            msg += f"{emoji_y} {name}({code}) 净值:{nav_str} 昨日:{cy_str} 今日估算:{ct_str}\n"

    if news_data_by_fund:
        msg += "\n📰 持仓股票最新公告\n" + "-" * 38 + "\n"
        for fund_code in FUND_SEQ:
            items = news_data_by_fund.get(fund_code, [])
            if not items:
                continue
            msg += f"【{FUND_NAMES_CN.get(fund_code, fund_code).split('（')[0]}】\n"
            for item in items[:3]:
                msg += f"  • {item['name']}({item['code']}) — {item['title']}\n"
                msg += f"    📅 {item['date']}\n"

    msg += "\n---\n🤖 由贾维斯自动生成"

    # --- 发送飞书 ---
    print(f"\n📱 发送飞书消息...")
    ok = send_feishu(msg)
    print(f"{'✅' if ok else '❌'} 飞书推送: {'成功' if ok else '失败'}")

    # --- 写文档 ---
    print(f"📝 写入飞书文档...")
    token = get_token()
    ok_doc = write_combined_doc(fund_data_list, news_data_by_fund, today, token)
    print(f"{'✅' if ok_doc else '❌'} 文档写入: {'成功' if ok_doc else '失败'}")

    print(f"\n✅ 完成 {now_str}")


if __name__ == "__main__":
    main()

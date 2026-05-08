#!/usr/bin/env python3
"""
每日财经资讯 - 重构版 v4（lark-cli 迁移）
1. 基金净值（昨日确认 + 今日估算）
2. 大盘指数（A股 + 港股 + 美股）
3. 关注板块行情（黄金、CPO、电网、AI应用）
4. 创建飞书文档（user 身份） + 写入多维表格
"""
import subprocess
import re
import json
import time
import urllib.request
from datetime import datetime, timedelta

# ========== 配置 ==========
FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"

# ========== 基金数据（手动维护昨日净值）==========
FUNDS = [
    ("018125", "永赢先进制造"),
    ("015790", "永赢高端装备"),
    ("017193", "天弘工业有色"),
    ("016858", "国金量化多因子"),
    ("002943", "广发多因子"),
    ("012922", "易方达全球成长(QDII)"),
    ("017290", "中欧科创主题"),
    ("002963", "易方达黄金ETF"),
]

# 手动维护昨日净值（每日更新）
YEST_NAVS = {
    "018125": "2.2185", "015790": "1.4380", "017193": "1.9128",
    "016858": "3.3407", "002943": "5.0754", "012922": "3.2003",
    "017290": "2.8130", "002963": "3.3435",
}
YEST_CHG = {
    "018125": "+0.44%", "015790": "+1.50%", "017193": "-1.06%",
    "016858": "-0.85%", "002943": "-0.75%", "012922": "+0.33%",
    "017290": "-0.58%", "002963": "+0.65%",
}

# ========== 大盘指数配置（腾讯行情接口）==========
INDICES = [
    ("sh000001", "上证指数"),
    ("sz399001", "深证成指"),
    ("sz399006", "创业板指"),
    ("hkHSI",   "恒生指数"),
    ("hk800000","国企指数"),
    ("usDJI",   "道琼斯"),
    ("usIXIC",  "纳斯达克"),
    ("usINX",   "标普500"),
]

# ========== 关注板块配置（thsdk URFI代码，Linux路径）==========
BLOCKS = [
    ("URFI885530", "黄金概念"),
    ("URFI886033", "共封装光学(CPO)"),
    ("URFI885311", "智能电网"),
    ("URFI886108", "AI应用"),
]

# ========== lark-cli 封装 ==========
def lark_cli(cmd_list, data_str=None):
    args = ["lark-cli"] + cmd_list
    if data_str is not None:
        args += ["--data", "-"]
    proc = subprocess.run(
        args,
        input=data_str,
        capture_output=True, text=True, timeout=20
    )
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except:
            return {"ok": False, "error": proc.stdout}
    return {"ok": False, "error": proc.stderr or proc.stdout}

# ========== 文档操作 ==========
def create_doc(title):
    """用 lark-cli 创建文档（user 身份）"""
    # 先生成一个 markdown 内容用于初始化
    data = lark_cli([
        "docs", "+create",
        "--title", title,
        "--markdown", "# " + title,
        "--as", "user",
        "--folder-token", FOLDER_TOKEN
    ])
    if data.get("ok"):
        return data["data"]["doc_id"], data["data"]["doc_url"]
    print(f"  ❌ 创建文档失败: {data}")
    return None, None

def insert_blocks(doc_token, blocks):
    """分批插入 blocks（lark-cli api --as user）"""
    for i in range(0, len(blocks), 50):
        batch = blocks[i:i+50]
        payload_str = json.dumps({"children": batch}, ensure_ascii=False)
        result = lark_cli(
            ["api", "POST",
             f"/open-apis/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
             "--as", "user"],
            data_str=payload_str
        )
        if result.get("code") != 0:
            print(f"  insert error: {result.get('msg')}")
        time.sleep(0.3)

def write_cell_text(doc_token, cell_id, text):
    """向表格单元格写入文本"""
    block = {
        "block_type": 2,
        "text": {
            "elements": [{"type": "text_run", "text_run": {"content": str(text)}}],
            "style": {}
        }
    }
    payload_str = json.dumps({"children": [block]}, ensure_ascii=False)
    result = lark_cli(
        ["api", "POST",
         f"/open-apis/docx/v1/documents/{doc_token}/blocks/{cell_id}/children",
         "--as", "user"],
        data_str=payload_str
    )
    return result.get("code") == 0

def create_table_block(doc_token, row_size, col_count):
    """创建表格并返回 cell_ids"""
    payload_str = json.dumps({
        "children": [{
            "block_type": 31,
            "table": {"property": {"row_size": row_size, "column_size": col_count}}
        }]
    }, ensure_ascii=False)
    result = lark_cli(
        ["api", "POST",
         f"/open-apis/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
         "--as", "user"],
        data_str=payload_str
    )
    if result.get("code") != 0:
        return [None] * (row_size * col_count)
    children = result.get("data", {}).get("children", [])
    cells = children[0].get("table", {}).get("cells", []) if children else []
    return cells

def make_table(doc_token, rows_data, col_count):
    """创建表格并写入数据"""
    n_rows = len(rows_data)
    cell_ids = create_table_block(doc_token, n_rows, col_count)
    for r_idx, row in enumerate(rows_data):
        for c_idx, cell_text in enumerate(row):
            idx = r_idx * col_count + c_idx
            if idx < len(cell_ids) and cell_ids[idx]:
                write_cell_text(doc_token, cell_ids[idx], str(cell_text))
    return True

# ========== Block 构造 ==========
def make_text(text):
    return {"block_type": 2, "text": {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_heading(text, level=1):
    key = ["heading1", "heading2", "heading3"][level - 1]
    return {"block_type": level + 2, key: {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

# ========== 数据获取 ==========
def fetch_fund_data():
    """从天天基金获取今日估算净值"""
    fund_data = {}
    for code, name in FUNDS:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode()
            m = re.search(r'\((.+)\)', raw)
            if m:
                d = json.loads(m.group(1))
                fund_data[code] = {
                    "name": name,
                    "yest_nav": YEST_NAVS.get(code, "-"),
                    "yest_chg": YEST_CHG.get(code, "-"),
                    "today_est": d.get("gsz", "-"),
                    "today_chg": d.get("gszzl", "-") + "%",
                }
        except Exception as e:
            print(f"  {code} 获取失败: {e}")
            fund_data[code] = {"name": name, "yest_nav": YEST_NAVS.get(code, "-"),
                               "yest_chg": YEST_CHG.get(code, "-"),
                               "today_est": "-", "today_chg": "-"}
    return fund_data

def parse_tencent_index(code):
    """从腾讯行情接口解析指数数据"""
    url = f"https://qt.gtimg.cn/q={code}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as r:
        raw = r.read().decode("gbk", errors="replace")
    m = re.search(r'"([^"]+)"', raw)
    if not m:
        return None
    fields = m.group(1).split("~")
    if len(fields) < 35:
        return None
    return {
        "name": fields[1],
        "price": fields[3],
        "yest_close": fields[4],
        "chg_amount": fields[31],
        "chg_pct": fields[32],
        "time": fields[30] if len(fields) > 30 else "",
    }

def fetch_block_data():
    """通过 thsdk 获取关注板块涨幅（使用 tevengg 账号）"""
    import thsdk
    block_data = {}
    # 建立代码->名称的映射
    code_to_name = {code: name for code, name in BLOCKS}
    codes = list(code_to_name.keys())
    try:
        ths = thsdk.THS({'username': 'tevengg', 'password': 'asp4fun123'})
        ths.connect()
        result = ths.market_data_block(codes, '扩展')
        if result.success:
            for _, row in result.df.iterrows():
                code = row['代码']
                name = code_to_name.get(code, code)
                block_data[code] = {
                    "name": name,
                    "chg": f"{row.get('涨幅', 0):+.2f}%",
                    "chg5": f"{row.get('5日涨幅', 0):+.2f}%",
                    "chg10": f"{row.get('10日涨幅', 0):+.2f}%",
                }
    except Exception as e:
        print(f"  板块数据获取失败: {e}")
    for code, name in BLOCKS:
        if code not in block_data:
            block_data[code] = {"name": name, "chg": "-", "chg5": "-", "chg10": "-"}
    return block_data

# ========== 主流程 ==========
def main():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    doc_title = f"每日财经-{now.strftime('%Y%m%d')}-{now.strftime('%H%M')}"

    print(f"=== 每日财经资讯 {today_str} ===")

    # 1. 获取基金数据
    print("📊 获取基金净值...")
    fund_data = fetch_fund_data()
    for code, d in fund_data.items():
        print(f"  {d['name']}: 估算{d['today_est']}（{d['today_chg']}）")

    # 2. 获取大盘指数
    print("\n🌏 获取大盘指数...")
    index_data = {}
    for code, name in INDICES:
        try:
            d = parse_tencent_index(code)
            if d:
                index_data[code] = d
                print(f"  {name}: {d['price']}（{d['chg_pct']}%）")
        except Exception as e:
            print(f"  {name} 失败: {e}")

    # 3. 获取板块数据
    print("\n📦 获取关注板块...")
    block_data = fetch_block_data()
    for code, d in block_data.items():
        print(f"  {d['name']}: {d['chg']}")

    # 4. 创建文档
    print(f"\n📄 创建文档: {doc_title}")
    doc_token, doc_url = create_doc(doc_title)
    if not doc_token:
        return
    print(f"✅ 文档创建: {doc_token}")

    # 5. 写入标题
    insert_blocks(doc_token, [
        make_heading(f"📈 {doc_title}", 1),
        make_text(f"生成时间：{time_str}"),
        make_text(""),
    ])

    # 6. 基金净值表
    insert_blocks(doc_token, [make_text(""), make_heading("一、基金净值", 2)])
    fund_rows = [["基金名称", "昨日确认净值", "昨涨跌幅", "今日估算净值"]]
    for code, d in fund_data.items():
        fund_rows.append([
            d["name"],
            d["yest_nav"],
            d["yest_chg"],
            f"{d['today_est']}（{d['today_chg']}）"
        ])
    make_table(doc_token, fund_rows, 4)
    print(f"✅ 基金净值表写入完成 ({len(fund_rows)} 行)")

    # 7. 大盘指数表
    insert_blocks(doc_token, [make_text(""), make_heading("二、大盘指数", 2)])
    for market_prefixes, label in [(("sh", "sz"), "A股"), (("hk",), "港股"), (("us",), "美股")]:
        market_indices = [(c, n) for c, n in INDICES if c.startswith(market_prefixes)]
        if not market_indices:
            continue
        rows = [["指数名称", "最新点位", "涨跌幅", "涨跌额"]]
        for code, name in market_indices:
            d = index_data.get(code, {})
            pct = d.get("chg_pct", "-")
            amt = d.get("chg_amount", "-")
            rows.append([
                name,
                d.get("price", "-"),
                f"{pct}%" if pct != "-" else "-",
                f"{amt}" if amt != "-" else "-"
            ])
        insert_blocks(doc_token, [make_heading(label, 3)])
        make_table(doc_token, rows, 4)
        print(f"✅ {label} 指数表写入完成 ({len(rows)} 行)")

    # 8. 关注板块表
    insert_blocks(doc_token, [make_text(""), make_heading("三、关注板块", 2)])
    block_rows = [["板块名称", "今日涨跌幅", "5日涨幅", "10日涨幅"]]
    for code, name in BLOCKS:
        bd = block_data.get(code, {})
        block_rows.append([
            name,
            bd.get("chg", "-"),
            bd.get("chg5", "-"),
            bd.get("chg10", "-"),
        ])
    make_table(doc_token, block_rows, 4)
    print(f"✅ 关注板块表写入完成 ({len(block_rows)} 行)")

    # 9. 底部备注
    insert_blocks(doc_token, [
        make_text(""),
        make_text("注：基金净值为估算值，实际净值以基金公司确认为准；大盘指数数据仅供参考。"),
    ])

    print(f"\n🎉 全部完成！\n📄 文档：{doc_url}")

if __name__ == "__main__":
    main()

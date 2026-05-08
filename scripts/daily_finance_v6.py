#!/usr/bin/env python3
"""
每日财经资讯 - v6（持仓缓存版）
- 大盘/基金净值：腾讯行情+天天基金
- 持仓股：从Feishu Bitable读取（实时），文本块格式写入文档
- 数据源：腾讯行情+天天基金+飞书持仓多维表格
"""
import urllib.request, re, json, time, os
from datetime import datetime

# ========== 配置 ==========
APP_ID = "cli_a947b541d8785bd9"
APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
BITABLE_APP = "P4o3bUtsIaoUttsmIslcjEkunre"
TABLE_ID = "tblK6q2DRm2V3pQO"
HOLDINGS_BITABLE_TOKEN = "SYgZb5RGHalBU7sctGscDRIpnzg"
HOLDINGS_TABLE_ID = "tbl8hhmWssnxpmFg"
HOLDINGS_FILE = "data/fund_holdings.json"

# ========== 基金列表 ==========
FUNDS = [
    ("018125", "永赢先进制造"),
    ("015790", "永赢高端装备"),
    ("017193", "天弘工业有色"),
    ("016858", "国金量化多因子"),
    ("002943", "广发多因子"),
    ("012922", "易方达全球成长"),
    ("017290", "中欧科创主题"),
    ("002963", "易方达黄金ETF"),
]

# ========== 持仓数据（从Feishu Bitable读取）==========
def load_holdings():
    """从基金持仓多维表格读取持仓数据"""
    try:
        t = get_token()
        if not t:
            print("  ⚠️ token失败，使用空持仓")
            return {}, {}
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{HOLDINGS_BITABLE_TOKEN}/tables/{HOLDINGS_TABLE_ID}/records?page_size=100"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {t}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        if data.get("code") != 0:
            print(f"  ⚠️ 持仓读取失败: {data.get('msg')}")
            return {}, {}
        records = data.get("data", {}).get("items", [])
        holdings = {}
        fund_names = {}
        for rec in records:
            fields = rec.get("fields", {})
            fcode = str(fields.get("基金代码", ""))
            fname = fields.get("基金名称", "")
            sname = fields.get("股票名称", "")
            scode = str(fields.get("股票代码", ""))
            market = fields.get("市场", "sz")
            if not fcode or not sname:
                continue
            if market == "sz": qcode = f"sz{scode}"
            elif market == "sh": qcode = f"sh{scode}"
            elif market == "hk": qcode = f"hk{scode}"
            elif market == "us": qcode = scode
            else: qcode = f"sz{scode}"
            if fcode not in holdings:
                holdings[fcode] = []
                fund_names[fcode] = fname
            holdings[fcode].append((qcode, scode, sname))
        total = sum(len(v) for v in holdings.values())
        print(f"  持仓读取: {total}只股票 ({len(holdings)}只基金)")
        return holdings, fund_names
    except Exception as e:
        print(f"  持仓读取异常: {e}")
        return {}, {}

# ========== 大盘指数 ==========
INDICES = [
    ("sh000001","A股 · 上证指数"),("sz399001","A股 · 深证成指"),
    ("sz399006","A股 · 创业板指"),("sh000688","A股 · 科创50"),
    ("hkHSI","港股 · 恒生指数"),("hk800000","港股 · 国企指数"),
    ("usDJI","美股 · 道琼斯"),("usIXIC","美股 · 纳斯达克"),("usINX","美股 · 标普500"),
]

# ========== 飞书 API ==========
def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("tenant_access_token", "")

def api_post(url, payload, token, retries=2):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise

def create_doc(token, title):
    d = api_post("https://open.feishu.cn/open-apis/docx/v1/documents", {"title": title}, token)
    if d.get("code") != 0:
        raise Exception(f"create_doc: {d.get('msg')}")
    return d["data"]["document"]["document_id"]

def insert_texts(token, doc_token, blocks, parent_id=None):
    if parent_id is None:
        parent_id = doc_token
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{parent_id}/children"
    for i in range(0, len(blocks), 50):
        batch = blocks[i:i+50]
        d = api_post(url, {"children": batch}, token)
        if d.get("code") != 0:
            print(f"  insert error: {d.get('msg')}")
        time.sleep(0.3)

def create_table(token, doc_token, rows, col_count, parent_id=None):
    if parent_id is None:
        parent_id = doc_token
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{parent_id}/children"
    d = api_post(url, {"children": [{
        "block_type": 31,
        "table": {"property": {"row_size": len(rows), "column_size": col_count}}
    }]}, token)
    if d.get("code") != 0:
        raise Exception(f"create_table: {d.get('msg')}")
    cells = d["data"]["children"][0].get("table", {}).get("cells", [])
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            idx = r_idx * col_count + c_idx
            if idx < len(cells):
                cell_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{cells[idx]}/children"
                try:
                    api_post(cell_url, {"children": [{
                        "block_type": 2,
                        "text": {"elements": [{"type": "text_run", "text_run": {"content": str(val)}}], "style": {}}
                    }]}, token, retries=1)
                    time.sleep(0.08)
                except:
                    pass
    return d["data"]["children"][0]["block_id"]

def write_bitable(token, title, url_link, date_str):
    date_ms = int(datetime.strptime(date_str, "%Y-%m-%d").timestamp() * 1000)
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP}/tables/{TABLE_ID}/records"
    return api_post(url, {"fields": {"文档标题": {"link": url_link, "text": title}, "创建日期": date_ms}}, token)

# ========== Block 构造 ==========
def T(text):
    return {"block_type": 2, "text": {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def H(text, level=1):
    key = ["heading1","heading2","heading3"][level-1]
    return {"block_type": level+2, key: {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_text_table(rows):
    """文本块格式表格（持仓股用，避免逐格API）"""
    blocks = []
    for row in rows:
        blocks.append(T("\t".join(str(v) for v in row)))
    return blocks

# ========== 数据获取 ==========
def get_price(qcode):
    """获取单只股票行情"""
    url = f"https://qt.gtimg.cn/q={qcode}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com"})
        with urllib.request.urlopen(req, timeout=4) as r:
            raw = r.read().decode("gbk", errors="replace")
        m = re.search(r'"([^"]+)"', raw)
        if m:
            f = m.group(1).split("~")
            if len(f) > 32:
                return {"name": f[1], "price": f[3], "chg_pct": f[32]}
    except:
        pass
    return {}

def fetch_fund_data():
    data = {}
    for code, name in FUNDS:
        try:
            url = f"https://fundgz.1234567.com.cn/js/{code}.js"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode()
            m = re.search(r'\((.+)\)', raw)
            if m:
                d = json.loads(m.group(1))
                data[code] = {"name": name, "nav": d.get("dwjz","-"), "gsz": d.get("gsz","-"), "gszzl": d.get("gszzl","-")}
        except Exception as e:
            print(f"  {code} 净值失败: {e}")
            data[code] = {"name": name, "nav": "-", "gsz": "-", "gszzl": "-"}
    return data

# ========== 主流程 ==========
def main():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    print(f"=== 每日财经 v6 {today_str} ===")

    # 加载持仓
    holdings, fund_names = load_holdings()

    # 1. 大盘指数
    print("📊 大盘指数...")
    idx_data = {}
    for code, name in INDICES:
        try:
            url = f"https://qt.gtimg.cn/q={code}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                raw = r.read().decode("gbk", errors="replace")
            m = re.search(r'"([^"]+)"', raw)
            if m:
                f = m.group(1).split("~")
                if len(f) > 32:
                    idx_data[code] = {"name": f[1], "price": f[3], "chg_amt": f[31], "chg_pct": f[32]}
                    print(f"  ✅ {name}: {f[3]} ({f[32]}%)")
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    # 2. 基金净值
    print("💰 基金净值...")
    fund_data = fetch_fund_data()

    # 3. 持仓股行情（只查价格，不爬持仓）
    print("📦 持仓股行情...")
    price_map = {}
    for fcode, stocks in holdings.items():
        for qcode, scode, sname in stocks:
            p = get_price(qcode)
            if p:
                price_map[qcode] = p
            time.sleep(0.25)
    print(f"  获取到 {len(price_map)} 只行情")

    # 4. 飞书写入
    print("🔐 飞书写入...")
    token = get_token()
    if not token:
        print("❌ token失败"); return

    doc_token = create_doc(token, f"每日财经动态 {today_str}")
    doc_url = f"https://feishu.cn/docx/{doc_token}"
    print(f"✅ 文档: {doc_token}")

    insert_texts(token, doc_token, [H("📈 每日财经动态", 1), T(f"生成时间：{today_str} {time_str}"), T("")])

    # 第一部分：大盘
    insert_texts(token, doc_token, [T(""), H("一、大盘信息", 2)])
    for prefixes, label in [(("sh","sz"),"A股"),(("hk",),"港股"),(("us",),"美股")]:
        idxs = [(c,n) for c,n in INDICES if c.startswith(prefixes)]
        rows = [["指数名称","最新点位","涨跌幅","涨跌额"]]
        for code, full_name in idxs:
            d = idx_data.get(code, {})
            pct = d.get("chg_pct","-")
            amt = d.get("chg_amt","-")
            rows.append([full_name.split(" · ")[-1], d.get("price","-"),
                         f"{pct}%" if pct not in ("-","") else "-", amt if amt != "-" else "-"])
        insert_texts(token, doc_token, [H(label, 3)])
        create_table(token, doc_token, rows, 4)
    print("✅ 大盘完成")

    # 第二部分：基金净值
    insert_texts(token, doc_token, [T(""), H("二、基金净值", 2)])
    rows = [["基金名称","昨日确认净值","今日估算","估算涨跌%"]]
    for code, name in FUNDS:
        d = fund_data.get(code, {})
        rows.append([name, d.get("nav","-"), d.get("gsz","-"),
                     d.get("gszzl","-")+"%" if d.get("gszzl","-") != "-" else "-"])
    create_table(token, doc_token, rows, 4)
    print("✅ 基金净值完成")

    # 第三部分：持仓股
    insert_texts(token, doc_token, [T(""), H("三、基金Top5重仓股行情", 2)])
    insert_texts(token, doc_token, [T("📌 数据来源：东方财富（季度持仓）+ 腾讯行情（实时价格）")])
    for fcode, fname in FUNDS:
        stocks = holdings.get(fcode, [])
        display_name = fund_names.get(fcode, fname)
        insert_texts(token, doc_token, [H(f"{display_name}（{fcode}）", 3)])
        if not stocks:
            insert_texts(token, doc_token, [T("　（黄金ETF，持仓为黄金期货，无股票数据）")])
            continue
        rows = [["代码","名称","最新价","涨跌幅"]]
        for qcode, scode, sname in stocks:
            p = price_map.get(qcode, {})
            price = p.get("price", "-")
            pct = p.get("chg_pct", "-")
            rows.append([scode, sname, price if price not in ("-","") else "-",
                         f"{pct}%" if pct not in ("-","") else "-"])
        insert_texts(token, doc_token, make_text_table(rows))
        time.sleep(0.2)
    print("✅ 持仓股完成")

    # 备注
    insert_texts(token, doc_token, [
        T(""),
        T("注：基金净值仅为估算值，实际净值以基金公司确认为准；重仓股数据为季度披露，仅供参考。"),
    ])

    # 多维表格
    result = write_bitable(token, f"每日财经动态 {today_str}", doc_url, today_str)
    if result.get("code") == 0:
        print(f"✅ 多维表格写入成功")
    else:
        print(f"⚠️ 多维表格失败: {result.get('msg')}")

    print(f"\n🎉 完成\n📄 {doc_url}")

if __name__ == "__main__":
    main()

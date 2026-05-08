#!/usr/bin/env python3
"""
每日财经资讯 v5（lark-cli + ontology + finflow/thsdk）
1. 大盘指数（finflow A股/港股 + thsdk 纳指）
2. 关注板块（thsdk market_data_block）
3. 基金净值（天天基金API）
4. 基金Top5持仓（ontology + finflow实时行情）
5. 异动股票资讯（腾讯新闻CLI）
"""
import subprocess, re, json, time, os, urllib.request
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ========== 配置 ==========
FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"
WORKSPACE = "/root/.openclaw/workspace"
ONTOLOGY_SCRIPT = "/root/.openclaw/workspace/skills/ontology/scripts/ontology.py"
TENCENT_NEWS_CLI = "/root/.openclaw/workspace/skills/tencent-news/tencent-news-cli"

# 板块配置（thsdk URFI代码）
BLOCKS = [
    ("URFI885530", "黄金概念"),
    ("URFI886033", "共封装光学(CPO)"),
    ("URFI885311", "智能电网"),
]

# ========== lark-cli 封装 ==========
def lark_cli(cmd_list, data_str=None, cwd=WORKSPACE):
    args = ["lark-cli"] + cmd_list
    if data_str is not None:
        args += ["--data", "-"]
    proc = subprocess.run(args, input=data_str, capture_output=True, text=True, timeout=30, cwd=cwd)
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except:
            return {"ok": False, "error": proc.stdout}
    return {"ok": False, "error": proc.stderr or proc.stdout}

# ========== finflow 数据校验工具 ==========
def sanitize_finfow_data(raw_data):
    """
    校验 finflow 返回的数据，自动修正明显错误。
    规则：changePercent 应与 (price-preclose)/preclose 一致，偏差大于1%视为错误，直接用价格计算。
    """
    data = raw_data.get("data", {})
    price = float(data.get("price", 0))
    preclose = float(data.get("preclose", 0))
    reported_pct = float(data.get("changePercent", 0))

    if preclose > 0 and price > 0:
        correct_pct = round((price - preclose) / preclose * 100, 2)
        if abs(reported_pct - correct_pct) > 1:  # 偏差超过1%认为是错误数据
            data["changePercent"] = correct_pct
    return raw_data


# ========== 1. 大盘指数（finflow + thsdk + 东方财富历史K线）==========
EM_ASTOCK_MAP = {
    "SH000001": ("1.000001", "上证指数"),
    "SZ399001": ("0.399001", "深证成指"),
    "SZ399006": ("0.399006", "创业板指"),
    "SH000688": ("1.000688", "科创50"),
}

def _get_em_yesterday(secid):
    """查东方财富历史K线，返回 (date, close, yest_chg_pct) 或 None"""
    try:
        url = (f"http://push2his.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
               f"&klt=101&fqt=1&end=20260428&lmt=3")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "http://quote.eastmoney.com/"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        klines = d.get("data", {}).get("klines", [])
        if len(klines) >= 2:
            prev = klines[-2].split(",")   # [-2] = yesterday
            prev_close = float(prev[2])
            prev_yest_close = float(klines[-1].split(",")[2])  # day-before-yesterday close
            yest_pct = round((prev_close - prev_yest_close) / prev_yest_close * 100, 2)
            return prev[0], prev_close, yest_pct
        return None
    except:
        return None

MARKET_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")

def _load_market_cache():
    """加载最近一个交易日的市场缓存，返回 {代码: {昨日价, 昨日涨跌幅}} 或空字典"""
    try:
        os.makedirs(MARKET_CACHE_DIR, exist_ok=True)
        # 找最新的缓存文件（market_cache_YYYY-MM-DD.json）
        files = [f for f in os.listdir(MARKET_CACHE_DIR) if f.startswith("market_cache_") and f.endswith(".json")]
        if not files:
            return {}
        latest = sorted(files)[-1]
        with open(os.path.join(MARKET_CACHE_DIR, latest), "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f"  [缓存] 读取 {latest}")
        return cache
    except Exception:
        return {}

def _save_market_cache(indices):
    """保存当日市场指数快照到缓存文件"""
    try:
        os.makedirs(MARKET_CACHE_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        cache = {idx["代码"]: {"昨日价": idx.get("最新价", "-"), "昨日涨跌幅": idx.get("最新涨跌幅", "-")} for idx in indices}
        cache["_date"] = today
        cache_file = os.path.join(MARKET_CACHE_DIR, f"market_cache_{today}.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"  [缓存] 已保存 {cache_file}")
    except Exception as e:
        print(f"  [缓存] 保存失败: {e}")

def get_market_indices():
    """获取7个大盘指数，优先从昨日缓存读取历史数据"""
    cache = _load_market_cache()
    results = []
    finflow_codes = [
        ("上证指数", "SH000001"),
        ("深证成指", "SZ399001"),
        ("创业板指", "SZ399006"),
        ("科创50",   "SH000688"),
        ("恒生指数", "HKHSI"),
        ("恒生科技", "HKHSTECH"),
    ]
    for name, code in finflow_codes:
        yest_close, yest_pct = "-", "-"
        try:
            r = subprocess.run(["finflow", "quote", code], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                d = sanitize_finfow_data(json.loads(r.stdout))
                data = d.get("data", {})
                price_val = float(data.get("price", 0))
                preclose_val = float(data.get("preclose", 0))
                today_pct = round((price_val - preclose_val) / preclose_val * 100, 2) if preclose_val else 0
                # A股：尝试东方财富历史接口查昨日涨跌幅
                if code in EM_ASTOCK_MAP:
                    secid, _ = EM_ASTOCK_MAP[code]
                    em = _get_em_yesterday(secid)
                    if em:
                        yest_close = round(float(em[1]), 2)
                        yest_pct = em[2]
                    else:
                        yest_close = round(preclose_val, 2)
                        # 兜底：从缓存读
                        if code in cache:
                            yest_close = cache[code].get("昨日价", yest_close)
                            cached_pct = cache[code].get("昨日涨跌幅")
                            if isinstance(cached_pct, (int, float)):
                                yest_pct = cached_pct
                else:
                    # 港股：直接从缓存读昨日数据（finflow 无历史）
                    yest_close = round(preclose_val, 2)
                    if code in cache:
                        yest_close = cache[code].get("昨日价", yest_close)
                        cached_pct = cache[code].get("昨日涨跌幅")
                        if isinstance(cached_pct, (int, float)):
                            yest_pct = cached_pct
                results.append({
                    "指数名称": name, "代码": code,
                    "昨日价": yest_close, "昨日涨跌幅": (f"{yest_pct:+.2f}%") if isinstance(yest_pct, float) else yest_pct,
                    "最新价": round(price_val, 2), "最新涨跌幅": today_pct,
                })
        except:
            results.append({"指数名称": name, "代码": code, "昨日价": "-", "昨日涨跌幅": "-", "最新价": "-", "最新涨跌幅": "-"})

    # 纳指（thsdk）
    try:
        import thsdk
        ths = thsdk.THS({"username": "tevengg", "password": "asp4fun123"})
        ths.connect()
        r = ths.market_data_us("UNQQNDAQ", "基础数据")
        if r.success:
            row = r.df.iloc[0]
            price = float(row["价格"])
            preclose = float(row["昨收价"])
            pct = round((price - preclose) / preclose * 100, 2) if preclose else 0
            yest_close = round(preclose, 2)
            yest_pct = "-"
            if "IXIC" in cache:
                yest_close = cache["IXIC"].get("昨日价", yest_close)
                cached_pct = cache["IXIC"].get("昨日涨跌幅")
                if isinstance(cached_pct, (int, float)):
                    yest_pct = cached_pct
            results.append({"指数名称": "纳斯达克", "代码": "IXIC", "昨日价": yest_close, "昨日涨跌幅": (f"{yest_pct:+.2f}%") if isinstance(yest_pct, float) else yest_pct, "最新价": round(price, 2), "最新涨跌幅": pct})
        else:
            results.append({"指数名称": "纳斯达克", "代码": "IXIC", "昨日价": "-", "昨日涨跌幅": "-", "最新价": "-", "最新涨跌幅": "-"})
        ths.disconnect()
    except:
        results.append({"指数名称": "纳斯达克", "代码": "IXIC", "昨日价": "-", "昨日涨跌幅": "-", "最新价": "-", "最新涨跌幅": "-"})

    _save_market_cache(results)
    return results

    return results

# ========== 2. 关注板块ETF（飞书多维表格 + finflow）==========
ETABLE_APP_TOKEN = "SYgZb5RGHalBU7sctGscDRIpnzg"
ETABLE_TABLE_ID = "tblPBNcI1BiNLg7G"

def get_etf_table():
    """通过 lark-cli user 身份读取飞书多维表格ETF数据"""
    import subprocess
    # lark-cli --as user 有完整的飞书权限，用它来读 bitable
    cmd = [
        "lark-cli",
        "api", "GET",
        "/open-apis/bitable/v1/apps/SYgZb5RGHalBU7sctGscDRIpnzg/tables/tblPBNcI1BiNLg7G/records",
        "--params", '{"page_size":100}',
        "--as", "user"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, cwd="/root/.openclaw/workspace")
    if proc.returncode != 0:
        print(f"  [WARN] lark-cli bitable failed: {proc.stderr[:100]}")
        return []
    try:
        result = json.loads(proc.stdout)
        if not result.get("ok"):
            print(f"  [WARN] lark-cli bitable not ok: {result.get('error', {})}")
            return []
        # lark-cli 返回格式: {"data": {"items": [...]}}
        data = result.get("data", {})
        items = data.get("items", data.get("records", []))
        etfs = []
        for rec in items:
            fields = rec.get("fields", {})
            sector = fields.get("所属板块")
            name = fields.get("ETF或基金名称")
            code = fields.get("ETF或基金代码")
            if sector and name and code:
                etfs.append({"sector": sector, "name": name, "code": str(int(code))})
        return etfs
    except Exception as e:
        print(f"  [WARN] ETF表格解析失败: {e}")
        return []
        return etfs
    except Exception as e:
        print(f"  [WARN] ETF表格解析失败: {e}")
        return []

def fetch_etf_quote(code):
    """用finflow获取ETF行情，返回(preclose, open, price)"""
    try:
        # 判断交易所：159开头→深圳，515/518开头→上海
        if code.startswith("159"):
            market_code = "SZ" + code
        else:
            market_code = "SH" + code
        r = subprocess.run(["finflow", "quote", market_code], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            d = sanitize_finfow_data(json.loads(r.stdout))
            data = d.get("data", {})
            preclose = float(data.get("preclose", 0))
            open_price = float(data.get("open", 0))
            price = float(data.get("price", 0))
            return preclose, open_price, price
    except:
        pass
    return None, None, None

def get_sector_etfs():
    """获取ETF数据：所属板块、ETF名称、ETF代码、昨收价、昨涨跌幅、现价、最新涨跌幅"""
    import os, json

    # 尝试从 sectors.json 读取 ETF 配置
    sectors_file = "/root/.openclaw/workspace/skills/daily-finance/sectors.json"
    etf_map = {}  # sector_name -> [(name, code), ...]
    if os.path.exists(sectors_file):
        with open(sectors_file) as f:
            cfg = json.load(f)
        for sec in cfg.get("sectors", []):
            if sec.get("etfs"):
                etf_map[sec["name"]] = sec["etfs"]

    # 兜底默认数据（来源：飞书表格 tblPBNcI1BiNLg7G）
    if not etf_map:
        etf_map = {
            "CPO": [
                ("富国中证通信设备 ETF", "159583"),
                ("国泰中证全指通信设备", "515880"),
                ("华夏中证通信 ETF", "515050"),
                ("华夏创业板人工智能 ETF", "159381"),
            ],
            "智能电网": [
                ("华夏中证电网设备 ETF", "159326"),
                ("易方达恒生 A 股电网设备 ETF", "561380"),
                ("广发中证电力 ETF", "159867"),
            ],
            "黄金": [
                ("华安黄金 ETF", "518880"),
                ("华安黄金股 ETF", "159321"),
            ],
        }

    results = []
    order = {"CPO": 0, "智能电网": 1, "黄金": 2}
    for sector, etf_list in etf_map.items():
        for name, code in etf_list:
            preclose, open_price, price = fetch_etf_quote(code)
            if preclose and preclose > 0:
                yest_pct = round((open_price - preclose) / preclose * 100, 2) if open_price else 0
                today_pct = round((price - preclose) / preclose * 100, 2) if price else 0
                results.append({
                    "所属板块": sector,
                    "ETF名称": name,
                    "ETF代码": code,
                    "昨日收盘价": round(preclose, 3),
                    "昨日涨跌幅": f"{yest_pct:+.2f}%",
                    "最新价": round(price, 3),
                    "最新涨跌幅": f"{today_pct:+.2f}%",
                })
            else:
                results.append({
                    "所属板块": sector,
                    "ETF名称": name,
                    "ETF代码": code,
                    "昨日收盘价": "-", "昨日涨跌幅": "-",
                    "最新价": "-", "最新涨跌幅": "-",
                })
            time.sleep(0.2)

    results.sort(key=lambda x: (order.get(x["所属板块"], 99), x["ETF名称"]))
    return results

# ========== 3. 基金净值（东方财富历史 + 1234567今日估算）==========
def _get_last_nav(code):
    """
    从东方财富历史NAV接口获取最近交易日净值和涨跌幅。
    返回 (nav_date, nav_value, nav_pct) 或 (None, None, None)。
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        url = f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=5&startDate={start}&endDate={today}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://fund.eastmoney.com/"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        items = d.get("Data", {}).get("LSJZList", [])
        if not items:
            return None, None, None
        # 第一条 = 最近交易日
        latest = items[0]
        nav_date = latest["FSRQ"]
        nav_val = float(latest["DWJZ"])
        nav_pct = float(latest["JZZZL"])  # 当日涨跌幅
        return nav_date, nav_val, nav_pct
    except:
        return None, None, None

def get_fund_navs():
    """
    基金净值：
    - 昨日净值、昨日涨跌幅：东方财富历史NAV接口（实际确认数据）
    - 最新净值、最新涨跌幅：1234567今日估算
    """
    funds = [
        ("018125", "永赢先进制造C"),
        ("015790", "永赢高端装备C"),
        ("017193", "天弘工业有色C"),
        ("016858", "国金量化多因子C"),
        ("002943", "广发多因子C"),
        ("012922", "易方达全球成长(QDII)C"),
        ("017290", "中欧科创主题(LOF)C"),
        ("002963", "易方达黄金ETF联接C"),
    ]
    results = []
    for code, name in funds:
        # 1. 东方财富历史NAV（获取昨日/上一交易日确认净值和涨跌幅）
        nav_date, nav_val, nav_pct = _get_last_nav(code)

        # 2. 1234567今日估算
        try:
            url = f"https://fundgz.1234567.com.cn/js/{code}.js"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode()
            m = re.search(r"\((.+)\)", raw)
            d = json.loads(m.group(1)) if m else {}
            gsz = d.get("gsz", "")
            gszzl = d.get("gszzl", "")
        except:
            gsz, gszzl = "", ""

        results.append({
            "基金代码": code,
            "基金名称": name,
            "昨日净值": f"{nav_val:.4f}" if nav_val is not None else "-",
            "昨日涨跌幅": (f"{nav_pct:+.2f}%") if nav_pct is not None else "-",
            "最新净值": gsz if gsz else "-",
            "最新涨跌幅": (gszzl + "%") if gszzl else "-",
        })
        time.sleep(0.2)
    return results

# ========== 4. 基金Top5持仓（飞书多维表格 + finflow）==========
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": "cli_a947b541d8785bd9", "app_secret": "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read()).get("tenant_access_token", "")

def get_holdings_from_bitable():
    """从飞书多维表格读取基金持仓数据（基金持仓数据库 > 基金持仓股票）"""
    app_token = "SYgZb5RGHalBU7sctGscDRIpnzg"
    table_id = "tbl8hhmWssnxpmFg"
    token = get_feishu_token()
    if not token:
        return {}
    
    records = []
    page_token = None
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_size=100"
        if page_token:
            url += f"&page_token={page_token}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if data.get("code") == 0:
            records.extend(data.get("data", {}).get("items", []))
            if not data.get("data", {}).get("has_more"):
                break
            page_token = data.get("data", {}).get("page_token")
        else:
            print(f"  [WARN] 多维表格读取失败: {data.get('msg')}")
            break
    
    # 转换为 fund_code -> [(stock_name, stock_code, pct), ...]
    holdings_json = {}
    for rec in records:
        f = rec.get("fields", {})
        fc = str(f.get("基金代码", "")).strip()
        stock_name = f.get("股票名称", "")
        stock_code = f.get("股票代码", "")
        pct = f.get("持仓比例")
        if fc and stock_name and pct:
            if fc not in holdings_json:
                holdings_json[fc] = []
            holdings_json[fc].append((stock_name, stock_code, float(pct)))
    
    print(f"  [INFO] 从多维表格读取到 {len(records)} 条持仓记录")
    return holdings_json

def get_holdings_table():
    """从飞书多维表格读取持仓数据，用 finflow 获取实时行情，构造表格"""
    # 基金元信息
    fund_names = {
        "018125": "永赢先进制造C", "015790": "永赢高端装备C",
        "017193": "天弘工业有色C", "016858": "国金量化多因子C",
        "002943": "广发多因子C", "012922": "易方达全球成长C",
        "017290": "中欧科创主题C", "002963": "易方达黄金ETF联接C",
    }
    fund_codes = list(fund_names.keys())

    # 🔑 从飞书多维表格读取持仓数据（替代已删除的 fund_holdings.json）
    holdings_json = get_holdings_from_bitable()

    # holdlings_json now comes from bitable: {fc -> [(stock_name, stock_code, pct), ...]}
    # No parsing needed, it's already structured
    holdings = {fc: [] for fc in fund_codes}
    for fc in fund_codes:
        if fc in holdings_json:
            for stock_name, stock_code, pct in holdings_json[fc]:
                holdings[fc].append((stock_name, pct))

    # 从持仓名称匹配股票代码（用于 finflow 行情）
    # 手动映射表：基金持仓名称 -> (市场, 代码)
    stock_code_map = {
        "新泉股份": ("SH", "603179"), "斯菱智驱": ("SZ", "301229"),
        "德昌电机控股": ("HK", "00579"), "宁波华翔": ("SH", "002048"),
        "五洲新春": ("SH", "603667"), "航天电子": ("SH", "600879"),
        "中国卫星": ("SH", "600118"), "天银机电": ("SZ", "300342"),
        "国博电子": ("SH", "688375"), "中国卫通": ("SH", "601698"),
        "洛阳钼业": ("SH", "603993"), "北方稀土": ("SH", "600111"),
        "中国铝业": ("SH", "601600"), "云铝股份": ("SZ", "000807"),
        "厦门钨业": ("SH", "600549"), "佰维存储": ("SH", "688525"),
        "大族激光": ("SZ", "002008"), "天孚通信": ("SZ", "301165"),
        "源杰科技": ("SH", "688498"), "阳光电源": ("SZ", "300274"),
        "宁德时代": ("SZ", "300750"), "中国平安": ("SH", "601318"),
        "新易盛": ("SZ", "300502"), "中际旭创": ("SZ", "300308"),
        "金诚信": ("SH", "603979"), "恒玄科技": ("SH", "688608"),
        "寒武纪": ("SH", "688256"), "阿里巴巴": ("HK", "09988"),
        "海光信息": ("SH", "688041"), "中芯国际": ("HK", "00981"),
        "紫金矿业": ("SH", "601899"), "华友钴业": ("SH", "603799"),
    }

    # 构造 (code, name) 列表用于行情查询
    all_stocks = []
    for fc in fund_codes:
        for name, pct in holdings[fc]:
            if name not in [s[0] for s in all_stocks]:
                code = stock_code_map.get(name, (None, None))
                all_stocks.append((name, code[1] if code[1] else None, pct))

    # 构造统一持仓列表：(name, market_code, pct)  去重
    seen_names = set()
    all_stocks = []  # (name, market_code, holding_pct)
    for fc in fund_codes:
        for name, pct in holdings[fc]:
            if name not in seen_names and name in stock_code_map:
                seen_names.add(name)
                market, code = stock_code_map[name]
                all_stocks.append((name, market, code, pct))

    # 批量获取股票行情（finflow，支持并发）
    def fetch_stock(name, market, code, holding_pct):
        try:
            if market == "HK":
                market_code = code  # finflow 用原始代码
            elif market == "SH":
                market_code = "SH" + code
            elif market == "SZ":
                market_code = "SZ" + code
            else:
                return name, code, None, holding_pct

            r = subprocess.run(
                ["finflow", "quote", market_code],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                d = sanitize_finfow_data(json.loads(r.stdout))
                data = d.get("data", {})
                price_val = float(data.get("price", 0))
                preclose_val = float(data.get("preclose", 0))
                return name, code, {
                    "preclose": preclose_val,
                    "price": price_val,
                    "open": float(data.get("open", 0)),
                    "change_pct": round((price_val - preclose_val) / preclose_val * 100, 2) if preclose_val else 0,
                }, holding_pct
        except:
            pass
        return name, code, None, holding_pct

    stock_prices = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_stock, *s): s for s in all_stocks}
        for future in as_completed(futures):
            name, code, price_data, holding_pct = future.result()
            if price_data and code:
                stock_prices[name] = (code, price_data, holding_pct)

    # 构造持仓表格
    table_rows = []
    for fc in fund_codes:
        fund_name = fund_names[fc]
        for name, holding_pct in holdings[fc]:
            if name in stock_prices:
                code, pd, _ = stock_prices[name]
                preclose = pd["preclose"]
                price = pd["price"]
                open_price = pd["open"]
                today_pct = pd["change_pct"]
                # 昨日涨跌幅 = (今开 - 昨收) / 昨收 * 100
                if preclose and preclose > 0 and open_price > 0:
                    yest_pct = round((open_price - preclose) / preclose * 100, 2)
                else:
                    yest_pct = "-"
                # 格式化
                sign_t = "+" if today_pct > 0 else ""
                today_str = f"{sign_t}{today_pct:.2f}%" if isinstance(today_pct, float) else today_pct
                yest_str = f"{yest_pct:+.2f}%" if isinstance(yest_pct, float) else yest_pct
                table_rows.append({
                    "所属基金": fund_name,
                    "股票名称": name,
                    "股票代码": code,
                    "昨日收盘价": round(preclose, 2) if preclose else "-",
                    "昨日涨跌幅": yest_str,
                    "今日价格": round(price, 2) if price else "-",
                    "今日涨跌幅": today_str,
                    "_today_pct_raw": today_pct if isinstance(today_pct, float) else 0,
                })
            else:
                table_rows.append({
                    "所属基金": fund_name,
                    "股票名称": name,
                    "股票代码": stock_code_map.get(name, ("",""))[1] or "-",
                    "昨日收盘价": "-", "昨日涨跌幅": "-",
                    "今日价格": "-", "今日涨跌幅": "-",
                    "_today_pct_raw": 0,
                })
    return table_rows

# ========== 5. 异动股票资讯（东方财富妙想）==========
def get_stock_news(stock_code, stock_name, count=3):
    import sys
    sys.path.insert(0, "/root/.openclaw/workspace/skills/mx-finance-search")
    from scripts.get_data import query_financial_news
    import asyncio

    async def fetch():
        query = f"{stock_name} {stock_code} 异动 原因"
        result = await query_financial_news(
            query=query,
            output_dir="/tmp",
            save_to_file=False,
        )
        content = result.get("content", "")
        if not content:
            return []
        try:
            # content 是 JSON 字符串，解析取前 count 条
            data = json.loads(content)
            items = data.get("data", [])
            news_list = []
            for item in items[:count]:
                title = item.get("title", "")
                body = item.get("content", "")[:200]  # 摘要前200字
                date = item.get("date", "")
                url = item.get("jumpUrl", "")
                news_list.append((title, body, date, url))
            return news_list
        except Exception as e:
            return []

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(fetch())
        finally:
            loop.close()
    except Exception as e:
        return []

# ========== 主函数 ==========
def main():
    t0 = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%H%M")
    doc_title = f"📈 每日财经-{today_str[:4]}{today_str[5:7]}{today_str[8:10]}-{now_str}"
    tmp_md = "/root/.openclaw/workspace/tmp/daily_finance.md"
    # lark-cli 要求相对路径，所以先写入 workspace 目录下的临时文件

    print(f"[{datetime.now().strftime('%H:%M:%S')}] === 每日财经 v5 开始 ===")

    print("[1/5] 大盘指数...")
    indices = get_market_indices()
    print(f"  → {len(indices)} 个指数")

    print("[2/5] 关注板块ETF...")
    sectors = get_sector_etfs()
    print(f"  → {len(sectors)} 个板块")

    print("[3/5] 基金净值...")
    funds = get_fund_navs()
    print(f"  → {len(funds)} 只基金")

    print("[4/5] 基金Top5持仓...")
    table_rows = get_holdings_table()
    print(f"  → {len(table_rows)} 条记录")

    print("[5/5] 异动检测...")
    news_items = {}
    for row in table_rows:
        try:
            pct = abs(row.get("_today_pct_raw", 0))
            if pct > 5.0:
                code, name = row["股票代码"], row["股票名称"]
                news = get_stock_news(code, name, count=3)
                news_items[code] = (name, news)
        except:
            pass
    print(f"  → {len(news_items)} 只异动股（>5%）")

    # ========== 生成 Markdown ==========
    md_lines = []
    md_lines.append(f"# 📈 每日财经 {today_str}")
    md_lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md_lines.append("")

    # 1. 大盘指数
    md_lines.append("## 一、大盘指数")
    md_lines.append("")
    md_lines.append("| 指数名称 | 代码 | 昨日价 | 昨日涨跌幅 | 最新价 | 最新涨跌幅 |")
    md_lines.append("|---|---|---|---|---|---|")
    for idx in indices:
        pct = idx.get("最新涨跌幅", "-")
        sign = "+" if isinstance(pct, (int, float)) and pct > 0 else ""
        pct_str = f"{sign}{pct}%" if isinstance(pct, (int, float)) else pct
        md_lines.append(f"| {idx['指数名称']} | {idx['代码']} | {idx.get('昨日价','-')} | {idx.get('昨日涨跌幅','-')} | {idx.get('最新价','-')} | {pct_str} |")
    md_lines.append("")

    # 2. 关注板块ETF
    md_lines.append("## 二、关注板块ETF")
    md_lines.append("")
    md_lines.append("| 所属板块 | ETF名称 | ETF代码 | 昨日收盘价 | 昨日涨跌幅 | 最新价 | 最新涨跌幅 |")
    md_lines.append("|---|---|---|---|---|---|---|")
    for sec in sectors:
        md_lines.append(f"| {sec['所属板块']} | {sec['ETF名称']} | {sec['ETF代码']} | {sec.get('昨日收盘价','-')} | {sec.get('昨日涨跌幅','-')} | {sec.get('最新价','-')} | {sec.get('最新涨跌幅','-')} |")
    md_lines.append("")

    # 3. 基金净值
    md_lines.append("## 三、基金净值")
    md_lines.append("")
    md_lines.append("| 基金代码 | 基金名称 | 昨日净值 | 昨日涨跌幅 | 最新净值 | 最新涨跌幅 |")
    md_lines.append("|---|---|---|---|---|---|")
    for f in funds:
        md_lines.append(f"| {f['基金代码']} | {f['基金名称']} | {f.get('昨日净值','-')} | {f.get('昨日涨跌幅','-')} | {f.get('最新净值','-')} | {f.get('最新涨跌幅','-')} |")
    md_lines.append("")

    # 4. 基金Top5持仓
    md_lines.append("## 四、基金Top5持仓")
    md_lines.append("")
    md_lines.append("| 所属基金 | 股票名称 | 股票代码 | 昨日收盘价 | 昨日涨跌幅 | 今日价格 | 今日涨跌幅 |")
    md_lines.append("|---------|---------|---------|---------|---------|---------|---------|")
    for row in table_rows:
        md_lines.append(
            f"| {row['所属基金']} | {row['股票名称']} | {row['股票代码']} | "
            f"{row['昨日收盘价']} | {row['昨日涨跌幅']} | {row['今日价格']} | {row['今日涨跌幅']} |"
        )
    md_lines.append("")

    # 5. 异动股票资讯
    md_lines.append("## 五、异动股票最新资讯")
    md_lines.append("")
    if news_items:
        for code, (name, news_list) in news_items.items():
            md_lines.append(f"### {name} ({code})")
            for title, body, date, url in news_list:
                link_str = f' [查看原文]({url})' if url else ''
                md_lines.append(f"- **{title}**{link_str}")
                if body:
                    md_lines.append(f"  {body.strip()}")
            md_lines.append("")
    else:
        md_lines.append("今日无明显异动股票（涨跌幅>5%）。")
        md_lines.append("")

    # lark-cli 创建文档（要求相对路径）
    md_in_workspace = "/root/.openclaw/workspace/tmp/daily_finance.md"
    with open(md_in_workspace, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print("[创建飞书文档...]")
    result = lark_cli([
        "docs", "+create",
        "--title", doc_title,
        "--markdown", "@./tmp/daily_finance.md",
        "--as", "user",
        "--folder-token", FOLDER_TOKEN,
    ], cwd=WORKSPACE)
    if result.get("ok"):
        doc_url = result.get("data", {}).get("doc_url", "（无URL）")
        print(f"✅ 文档创建成功: {doc_url}")
    else:
        print(f"❌ 文档创建失败: {result.get('error', 'unknown')}")

    print(f"\n🎉 完成！耗时 {time.time()-t0:.1f}秒")

if __name__ == "__main__":
    main()

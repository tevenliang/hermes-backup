#!/usr/bin/env python3
"""
每日财经资讯 v8（腾讯行情 + thsdk + 东方财富 + 飞书多维表格）
1. 大盘指数（腾讯行情 A股/港股/纳指 + 东方财富历史K线）
2. 关注板块ETF（腾讯行情 + 本地JSON，MCP预填充）
3. 基金净值（东方财富历史NAV + 1234567今日估算）
4. 基金Top5持仓（飞书多维表格 + thsdk/腾讯行情）
5. 异动股票资讯（thsdk 同花顺问财 + 快讯）
"""
import subprocess, re, json, time, os, urllib.request, signal, thsdk as _thsdk
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError


# ========== thsdk 超时封装 ==========
def _ths_timeout(seconds=10):
    """Decorator: 让 thsdk 调用在指定秒数内超时，避免卡住"""
    def wrapper(func):
        def wrapped(*args, **kwargs):
            def target():
                return func(*args, **kwargs)
            import threading
            t = threading.Thread(target=target)
            t.daemon = True
            t.start()
            t.join(timeout=seconds)
            if t.is_alive():
                raise TimeoutError(f"thsdk call timed out after {seconds}s")
            # 结果由 target() 写入外层变量，异常也由外层抛出
        return wrapped
    return wrapper


def _call_thsdk(func, *args, seconds=10, **kwargs):
    """带超时的 thsdk 调用，失败返回 None"""
    import threading, sys
    result = [None]
    exc = [None]
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exc[0] = e
    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout=seconds)
    if t.is_alive():
        print(f"  [WARN] thsdk 调用超时 ({seconds}s)")
        return None
    if exc[0]:
        raise exc[0]
    return result[0]

# ========== 配置 ==========
FEISHU_APP_ID = "cli_a97cf4a2bef8dcce"
FEISHU_APP_SECRET = "BQEEuScBOAzPa0ywZBpJue4y5wOFuP55"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"
WORKSPACE = "/Users/twliang/.hermes"
TENCENT_NEWS_CLI = "/Users/twliang/.hermes/skills/workspace/tencent-news/tencent-news-cli"

# ========== 同花顺账号配置 ==========
THS_OPS = {
    "username": "tevengg",
    "password": "asp4fun123",
    "mac": "0a0fa2817774",
}

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


# ========== 腾讯行情 API ==========
def _qq_quote(codes):
    """批量获取腾讯行情，返回 {normalized_code: {name, price, preclose, pct, open}}"""
    url = f"https://qt.gtimg.cn/q={codes}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode("gbk")
    results = {}
    for line in raw.strip().split("\n"):
        parts = line.split("~")
        if len(parts) > 35:
            raw_key = parts[0]  # e.g. v_sh000001="1
            # 解析出标准代码：如 sh000001, hkHSI, usNDX
            # 格式：v_{CODE}="{MARKET_NUM}  → 取第二段=前的部分
            inner = raw_key.split("=")[0]          # v_sh000001
            code = inner.lstrip("v_")              # sh000001
            # 对于 sh000001_1 → 去掉尾部 _数字（腾讯对A股指数的编码后缀）
            if code[-2:] in ("_1", "_51", "_100", "_200"):
                code = code[:-2]
            results[code] = {
                "name": parts[1],
                "price": parts[3],
                "preclose": parts[4],
                "open": parts[5],
                "pct": parts[32],
            }
    return results


# ========== 1. 大盘指数（腾讯行情 + thsdk 纳指 + 东方财富历史K线）==========
EM_ASTOCK_MAP = {
    "sh000001": ("1.000001", "上证指数"),
    "sz399001": ("0.399001", "深证成指"),
    "sz399006": ("0.399006", "创业板指"),
    "sh000688": ("1.000688", "科创50"),
}

QQ_INDEX_NAMES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
    "hkHSI": "恒生指数",
    "hkHSTECH": "恒生科技指数",
}

MARKET_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")


def _load_market_cache():
    """加载最近一个交易日的市场缓存"""
    try:
        os.makedirs(MARKET_CACHE_DIR, exist_ok=True)
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
    """保存当日市场指数快照"""
    try:
        os.makedirs(MARKET_CACHE_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        cache = {}
        for idx in indices:
            code = idx.get("代码", "")
            cache[code] = {
                "昨日价": idx.get("最新价", "-"),
                "昨日涨跌幅": idx.get("最新涨跌幅", "-"),
            }
        cache["_date"] = today
        with open(os.path.join(MARKET_CACHE_DIR, f"market_cache_{today}.json"), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"  [缓存] 已保存")
    except Exception as e:
        print(f"  [缓存] 保存失败: {e}")


def _get_em_yesterday(secid):
    """查东方财富历史K线，返回 (date, close, yest_chg_pct) 或 None"""
    try:
        today = datetime.now().strftime("%Y%m%d")
        url = (f"http://push2his.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
               f"&klt=101&fqt=1&end={today}&lmt=3")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "http://quote.eastmoney.com/"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read().decode())
        klines = d.get("data", {}).get("klines", [])
        if len(klines) >= 2:
            prev = klines[-2].split(",")
            prev_close = float(prev[2])
            prev_yest_close = float(klines[-1].split(",")[2])
            yest_pct = round((prev_close - prev_yest_close) / prev_yest_close * 100, 2)
            return prev[0], prev_close, yest_pct
        return None
    except:
        return None


def get_market_indices():
    """获取7个大盘指数：A股+港股用腾讯行情，纳指用thsdk"""
    cache = _load_market_cache()
    results = []

    # A股 + 港股指数（腾讯行情）
    qq_codes = "sh000001,sz399001,sz399006,sh000688,hkHSI,hkHSTECH"
    qq_data = _qq_quote(qq_codes)

    index_configs = [
        ("sh000001", "上证指数", "1.000001"),
        ("sz399001", "深证成指", "0.399001"),
        ("sz399006", "创业板指", "0.399006"),
        ("sh000688", "科创50",   "1.000688"),
        ("hkHSI",    "恒生指数", None),
        ("hkHSTECH", "恒生科技指数", None),
    ]

    for qq_code, name, em_secid in index_configs:
        d = qq_data.get(qq_code, {})
        price_str = d.get("price", "0")
        preclose_str = d.get("preclose", "0")
        today_pct_str = d.get("pct", "0")

        try:
            price = float(price_str)
            preclose = float(preclose_str)
            today_pct = float(today_pct_str)
        except (ValueError, TypeError):
            results.append({"指数名称": name, "代码": qq_code, "昨日价": "-", "昨日涨跌幅": "-", "最新价": "-", "最新涨跌幅": "-"})
            continue

        # 昨日涨跌幅：通过东方财富历史K线获取
        yest_close, yest_pct = preclose, "-"
        if em_secid:
            em = _get_em_yesterday(em_secid)
            if em:
                yest_close = round(float(em[1]), 2)
                yest_pct = em[2]
            else:
                if qq_code in cache:
                    yest_close = cache[qq_code].get("昨日价", preclose)
                    cached = cache[qq_code].get("昨日涨跌幅")
                    if isinstance(cached, (int, float)):
                        yest_pct = cached
        else:
            # 港股：直接从缓存读
            if qq_code in cache:
                yest_close = cache[qq_code].get("昨日价", preclose)
                cached = cache[qq_code].get("昨日涨跌幅")
                if isinstance(cached, (int, float)):
                    yest_pct = cached

        results.append({
            "指数名称": name,
            "代码": qq_code,
            "昨日价": yest_close,
            "昨日涨跌幅": (f"{yest_pct:+.2f}%") if isinstance(yest_pct, float) else yest_pct,
            "最新价": round(price, 2),
            "最新涨跌幅": today_pct,
        })

    # 纳斯达克：直接用腾讯行情（usNDX=纳斯达克100，比thsdk的IXIC更准确）
    qq_nasdaq = _qq_quote("usNDX")
    d = qq_nasdaq.get("usNDX", {})
    try:
        price = float(d.get("price", 0))
        preclose = float(d.get("preclose", 0))
        pct = float(d.get("pct", 0))
        yest_close = preclose
        yest_pct = "-"
        if "IXIC" in cache:
            yest_close = cache["IXIC"].get("昨日价", preclose)
            cached = cache["IXIC"].get("昨日涨跌幅")
            if isinstance(cached, (int, float)):
                yest_pct = cached
        if price > 0:
            results.append({
                "指数名称": "纳斯达克", "代码": "IXIC",
                "昨日价": round(yest_close, 2),
                "昨日涨跌幅": (f"{yest_pct:+.2f}%") if isinstance(yest_pct, float) else yest_pct,
                "最新价": round(price, 2), "最新涨跌幅": pct,
            })
        else:
            results.append({"指数名称": "纳斯达克", "代码": "IXIC", "昨日价": "-", "昨日涨跌幅": "-", "最新价": "-", "最新涨跌幅": "-"})
    except (ValueError, TypeError):
        results.append({"指数名称": "纳斯达克", "代码": "IXIC", "昨日价": "-", "昨日涨跌幅": "-", "最新价": "-", "最新涨跌幅": "-"})

    _save_market_cache(results)
    return results


# ========== 2. 关注板块ETF（本地JSON + 腾讯行情）==========
# ETF 数据来源：由 cron job 通过 MCP 读取飞书多维表格后写入本地 JSON
# JSON 路径：{SKILL_CACHE_DIR}/etf_list.json
# 若 JSON 不存在或读取失败，使用硬编码兜底数据
ETABLE_APP_TOKEN = "SYgZb5RGHalBU7sctGscDRIpnzg"
ETABLE_ETF_TABLE = "tblPBNcI1BiNLg7G"
ETF_LIST_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "etf_list.json")


def get_etf_list():
    """从本地 JSON 文件读取ETF列表（由 cron job 通过 MCP 预先写入）"""
    try:
        if os.path.exists(ETF_LIST_JSON):
            with open(ETF_LIST_JSON, "r", encoding="utf-8") as f:
                etfs = json.load(f)
            if etfs:
                print(f"  [INFO] 从 etf_list.json 加载 {len(etfs)} 条ETF记录")
                return etfs
    except Exception as e:
        print(f"  [WARN] ETF JSON 读取失败: {e}")
    return []


def _code_to_qq(code):
    """将ETF代码转换为腾讯行情代码，如 159583->sz159583, 515050->sh515050"""
    code = str(code).strip()
    if code.startswith("159") or code.startswith("150") or code.startswith("501"):
        return f"sz{code}"
    return f"sh{code}"


def get_sector_etfs():
    """获取ETF数据：从飞书表格读取配置，用腾讯行情获取实时数据"""
    etf_list = get_etf_list()
    if not etf_list:
        # 兜底硬编码（来源：飞书表格 tblPBNcI1BiNLg7G）
        etf_list = [
            {"sector": "CPO",      "name": "富国中证通信设备 ETF",       "code": "159583"},
            {"sector": "CPO",      "name": "国泰中证全指通信设备",         "code": "515880"},
            {"sector": "CPO",      "name": "华夏中证通信 ETF",             "code": "515050"},
            {"sector": "CPO",      "name": "华夏创业板人工智能 ETF",        "code": "159381"},
            {"sector": "智能电网", "name": "华夏中证电网设备 ETF",          "code": "159326"},
            {"sector": "智能电网", "name": "易方达恒生 A 股电网设备 ETF",   "code": "561380"},
            {"sector": "智能电网", "name": "广发中证电力 ETF",              "code": "159867"},
            {"sector": "黄金",    "name": "华安黄金 ETF",                  "code": "518880"},
            {"sector": "黄金",    "name": "华安黄金股 ETF",                "code": "159321"},
        ]

    # 批量获取腾讯行情
    qq_codes = ",".join(_code_to_qq(e["code"]) for e in etf_list)
    qq_data = _qq_quote(qq_codes)

    results = []
    order = {"CPO": 0, "智能电网": 1, "黄金": 2}
    for etf in etf_list:
        code = str(etf["code"]).strip()
        qq_code = _code_to_qq(code)
        d = qq_data.get(qq_code, {})

        price_str = d.get("price", "0")
        preclose_str = d.get("preclose", "0")
        open_str = d.get("open", "0")
        pct_str = d.get("pct", "0")

        try:
            price = float(price_str)
            preclose = float(preclose_str)
            open_p = float(open_str)
            today_pct = float(pct_str)
            yest_pct = round((open_p - preclose) / preclose * 100, 2) if preclose and open_p else 0
            results.append({
                "所属板块": etf["sector"],
                "ETF名称": etf["name"],
                "ETF代码": code,
                "昨日收盘价": round(preclose, 3),
                "昨日涨跌幅": f"{yest_pct:+.2f}%",
                "最新价": round(price, 3),
                "最新涨跌幅": f"{today_pct:+.2f}%",
            })
        except (ValueError, TypeError):
            results.append({
                "所属板块": etf["sector"],
                "ETF名称": etf["name"],
                "ETF代码": code,
                "昨日收盘价": "-", "昨日涨跌幅": "-",
                "最新价": "-", "最新涨跌幅": "-",
            })

    results.sort(key=lambda x: (order.get(x["所属板块"], 99), x["ETF名称"]))
    return results


# ========== 3. 基金净值（东方财富历史 + 1234567今日估算）==========
def _get_last_nav(code):
    """从东方财富历史NAV接口获取最近交易日净值和涨跌幅"""
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
        latest = items[0]
        return latest["FSRQ"], float(latest["DWJZ"]), float(latest["JZZZL"])
    except:
        return None, None, None


def get_fund_navs():
    """基金净值：昨日净值（东方财富历史）+ 今日估算净值（1234567）"""
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
        nav_date, nav_val, nav_pct = _get_last_nav(code)
        gsz, gszzl = "", ""
        try:
            url = f"https://fundgz.1234567.com.cn/js/{code}.js"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode()
            m = re.search(r"\((.+)\)", raw)
            if m:
                d = json.loads(m.group(1))
                gsz = d.get("gsz", "")
                gszzl = d.get("gszzl", "")
        except:
            pass
        results.append({
            "基金代码": code, "基金名称": name,
            "昨日净值": f"{nav_val:.4f}" if nav_val else "-",
            "昨日涨跌幅": (f"{nav_pct:+.2f}%") if nav_pct is not None else "-",
            "最新净值": gsz if gsz else "-",
            "最新涨跌幅": (gszzl + "%") if gszzl else "-",
        })
        time.sleep(0.15)
    return results


# ========== 4. 基金Top5持仓（飞书多维表格 + thsdk/腾讯行情）==========
FEISHU_APP_TOKEN = "SYgZb5RGHalBU7sctGscDRIpnzg"
FEISHU_HOLDINGS_TABLE = "tbl8hhmWssnxpmFg"


def _get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read()).get("tenant_access_token", "")


def get_holdings_from_bitable():
    """从飞书多维表格读取基金持仓数据（tbl8hhmWssnxpmFg）"""
    token = _get_feishu_token()
    if not token:
        return {}
    records = []
    page_token = None
    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_HOLDINGS_TABLE}/records?page_size=100"
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
            holdings_json[fc].append((stock_name, str(stock_code).strip(), float(pct)))
    print(f"  [INFO] 从多维表格读取到 {len(records)} 条持仓记录")
    return holdings_json


# A股 THSCODE 转换
def _to_ths_code(market, code):
    """转换为 thsdk THSCODE"""
    code = str(code).strip()
    if market == "SH":
        return f"USHA{code}"
    elif market == "SZ":
        return f"USZA{code}"
    return None


# 腾讯行情个股查询
def _qq_stock_quote(market, code):
    """用腾讯行情获取个股报价"""
    try:
        if market == "HK":
            qq_code = f"hk{code}"
        elif market == "SH":
            qq_code = f"sh{code}"
        elif market == "SZ":
            qq_code = f"sz{code}"
        else:
            return None
        d = _qq_quote(qq_code).get(qq_code, {})
        price_str = d.get("price", "0")
        preclose_str = d.get("preclose", "0")
        open_str = d.get("open", "0")
        pct_str = d.get("pct", "0")
        price = float(price_str)
        preclose = float(preclose_str)
        open_p = float(open_str)
        pct = float(pct_str)
        return {"price": price, "preclose": preclose, "open": open_p, "pct": pct}
    except:
        return None


def get_holdings_table():
    """基金Top5持仓：从飞书表格读取持仓，用腾讯/thsdk获取实时行情"""
    fund_names = {
        "018125": "永赢先进制造C",
        "015790": "永赢高端装备C",
        "017193": "天弘工业有色C",
        "016858": "国金量化多因子C",
        "002943": "广发多因子C",
        "012922": "易方达全球成长C",
        "017290": "中欧科创主题C",
        "002963": "易方达黄金ETF联接C",
    }
    fund_codes = list(fund_names.keys())

    # 从飞书多维表格读取持仓
    holdings_json = get_holdings_from_bitable()

    # 持仓映射：fund_code -> [(stock_name, stock_code, pct), ...]
    holdings = {fc: [] for fc in fund_codes}
    for fc in fund_codes:
        if fc in holdings_json:
            for stock_name, stock_code, pct in holdings_json[fc]:
                holdings[fc].append((stock_name, stock_code, pct))

    # 手动映射：持仓名称 -> (市场, 代码)
    stock_code_map = {
        "新泉股份":   ("SH", "603179"),
        "斯菱智驱":   ("SZ", "301229"),
        "德昌电机控股":("HK", "00579"),
        "宁波华翔":   ("SH", "002048"),
        "五洲新春":   ("SH", "603667"),
        "航天电子":   ("SH", "600879"),
        "中国卫星":   ("SH", "600118"),
        "天银机电":   ("SZ", "300342"),
        "国博电子":   ("SH", "688375"),
        "中国卫通":   ("SH", "601698"),
        "洛阳钼业":   ("SH", "603993"),
        "北方稀土":   ("SH", "600111"),
        "中国铝业":   ("SH", "601600"),
        "云铝股份":   ("SZ", "000807"),
        "厦门钨业":   ("SH", "600549"),
        "佰维存储":   ("SH", "688525"),
        "大族激光":   ("SZ", "002008"),
        "天孚通信":   ("SZ", "301165"),
        "源杰科技":   ("SH", "688498"),
        "阳光电源":   ("SZ", "300274"),
        "宁德时代":   ("SZ", "300750"),
        "中国平安":   ("SH", "601318"),
        "新易盛":     ("SZ", "300502"),
        "中际旭创":   ("SZ", "300308"),
        "金诚信":     ("SH", "603979"),
        "恒玄科技":   ("SH", "688608"),
        "寒武纪":     ("SH", "688256"),
        "阿里巴巴":   ("HK", "09988"),
        "海光信息":   ("SH", "688041"),
        "中芯国际":   ("HK", "00981"),
        "紫金矿业":   ("SH", "601899"),
        "华友钴业":   ("SH", "603799"),
    }

    # 收集所有需要查询的股票
    all_stocks = []
    for fc in fund_codes:
        for name, code_str, pct in holdings.get(fc, []):
            if name not in [s[0] for s in all_stocks] and name in stock_code_map:
                market, code = stock_code_map[name]
                all_stocks.append((name, market, code, pct))

    # 批量查询行情（thsdk for A股, 腾讯 for HK）
    import threading as _threading
    stock_prices = {}

    # A股：thsdk批量（带超时保护，失败则跳过）
    a_stocks = [(n, m, c, p) for n, m, c, p in all_stocks if m in ("SH", "SZ")]
    if a_stocks:
        ths_codes = [_to_ths_code(m, c) for _, m, c, _ in a_stocks]
        valid = [(n, ths, p) for (n, m, c, p), ths in zip(a_stocks, ths_codes) if ths]
        try:
            for name, ths_code, holding_pct in valid:
                result = [None]
                def _ths_job():
                    try:
                        with _thsdk.THS(THS_OPS) as ths:
                            result[0] = ths.market_data_cn(ths_code, "基础数据")
                    except Exception as e:
                        result[0] = e
                t = _threading.Thread(target=_ths_job)
                t.daemon = True
                t.start()
                t.join(timeout=8)
                if t.is_alive():
                    print(f"  [WARN] thsdk A股超时: {name}")
                    continue
                r = result[0]
                if isinstance(r, Exception):
                    print(f"  [WARN] thsdk A股异常: {name} {r}")
                    continue
                if r and r.success and not r.df.empty:
                    row = r.df.iloc[0]
                    price = float(row["价格"])
                    preclose = float(row["昨收价"])
                    open_p = float(row["开盘价"])
                    pct = round((price - preclose) / preclose * 100, 2) if preclose else 0
                    stock_prices[name] = {
                        "preclose": preclose, "price": price,
                        "open": open_p, "pct": pct, "holding_pct": holding_pct
                    }
                time.sleep(0.15)
        except Exception as e:
            print(f"  [WARN] thsdk A股查询失败: {e}")

    # HK股：腾讯批量
    hk_stocks = [(n, c, p) for n, m, c, p in all_stocks if m == "HK"]
    if hk_stocks:
        qq_codes = ",".join(f"hk{c}" for _, c, _ in hk_stocks)
        qq_data = _qq_quote(qq_codes)
        for name, code, holding_pct in hk_stocks:
            qq_code = f"hk{code}"
            d = qq_data.get(qq_code, {})
            try:
                price = float(d.get("price", 0))
                preclose = float(d.get("preclose", 0))
                open_p = float(d.get("open", 0))
                pct = float(d.get("pct", 0))
                stock_prices[name] = {
                    "preclose": preclose, "price": price,
                    "open": open_p, "pct": pct, "holding_pct": holding_pct
                }
            except (ValueError, TypeError):
                pass

    # 构造持仓表格
    table_rows = []
    for fc in fund_codes:
        fund_name = fund_names[fc]
        for name, code_str, holding_pct in holdings.get(fc, []):
            if name in stock_prices:
                pd = stock_prices[name]
                preclose = pd["preclose"]
                price = pd["price"]
                open_p = pd["open"]
                today_pct = pd["pct"]
                if preclose and preclose > 0 and open_p > 0:
                    yest_pct = round((open_p - preclose) / preclose * 100, 2)
                else:
                    yest_pct = "-"
                sign_t = "+" if today_pct > 0 else ""
                today_str = f"{sign_t}{today_pct:.2f}%" if isinstance(today_pct, float) else today_pct
                yest_str = f"{yest_pct:+.2f}%" if isinstance(yest_pct, float) else yest_pct
                table_rows.append({
                    "所属基金": fund_name,
                    "股票名称": name,
                    "股票代码": code_str,
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
                    "股票代码": code_str or "-",
                    "昨日收盘价": "-", "昨日涨跌幅": "-",
                    "今日价格": "-", "今日涨跌幅": "-",
                    "_today_pct_raw": 0,
                })
    return table_rows


# ========== 5. 异动股票资讯（同花顺问财 + 快讯）==========
import re as _re

_wencai_cache = {"items": None}


def _load_wencai_anomalies():
    """用问财NLP查询今日异动（涨停、非ST），只查一次缓存"""
    if _wencai_cache["items"] is not None:
        return _wencai_cache["items"]
    try:
        with _thsdk.THS(THS_OPS) as ths:
            # 查询今日涨停股
            resp = ths.wencai_nlp("今日涨停，非ST")
            _wencai_cache["items"] = resp.data or []
    except Exception as e:
        print(f"  [WARN] 问财异动查询失败: {e}")
        _wencai_cache["items"] = []
    return _wencai_cache["items"]


def get_stock_news(stock_code, stock_name, count=3):
    """用同花顺快讯筛选包含该股票名称的新闻，并返回问财异动列表中该股的记录"""
    results = []
    try:
        # 1. 问财异动匹配：涨停、竞价异动等
        anomalies = _load_wencai_anomalies()
        if anomalies:
            # 匹配股票名称或代码
            kw = stock_name
            code_digits = _re.sub(r'\D', '', str(stock_code))
            for item in anomalies:
                name = str(item.get("name", "") or "")
                code = str(item.get("code", "") or "")
                reason = str(item.get("reason", "") or item.get("title", "") or "")
                text = f"{name} {code} {reason}"
                if kw in text or (len(code_digits) >= 4 and code_digits in code):
                    results.append((f"[异动] {name} {code}", reason[:150], "", "同花顺问财"))
                    if len(results) >= count:
                        _wencai_cache["items"] = None  # 消耗后清缓存，下次重新查
                        return results

        # 2. 快讯兜底：同花顺7x24快讯
        try:
            with _thsdk.THS(THS_OPS) as ths:
                resp = ths.news()
            all_news = resp.data or []
        except Exception as e:
            print(f"  [WARN] 同花顺快讯拉取失败: {e}")
            all_news = []

        if all_news:
            keywords = [stock_name]
            code_digits = _re.sub(r'\D', '', str(stock_code))
            if len(code_digits) >= 4:
                keywords.append(code_digits)
            for item in all_news:
                title = item.get("Title", "")
                props_str = item.get("Properties", "")
                props = dict(_re.findall(r'(\w+)=([^\n]+)', props_str))
                body = props.get("summ", "")
                source = props.get("source", "同花顺快讯")
                text = f"{title} {body}"
                if any(kw in text for kw in keywords):
                    results.append((title, body[:150], "", source))
                    if len(results) >= count:
                        break
    except Exception as e:
        print(f"  [WARN] 资讯获取失败 {stock_name}: {e}")
    return results[:count]


# ========== 主函数 ==========
def main():
    t0 = time.time()
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%H%M")
    doc_title = f"📈 每日财经-{today_str[:4]}{today_str[5:7]}{today_str[8:10]}-{now_str}"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] === 每日财经 v6 开始 ===")

    print("[1/5] 大盘指数...")
    indices = get_market_indices()
    print(f"  → {len(indices)} 个指数")

    print("[2/5] 关注板块ETF...")
    sectors = get_sector_etfs()
    print(f"  → {len(sectors)} 个ETF")

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

    # 写入临时文件
    md_in_workspace = "/Users/twliang/.hermes/tmp/daily_finance.md"
    os.makedirs(os.path.dirname(md_in_workspace), exist_ok=True)
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
        print(f"\n{'='*50}")
        print(f"📄 每日财经 {datetime.now().strftime('%Y-%m-%d')}")
        print(f"🔗 {doc_url}")
        print(f"{'='*50}")
    else:
        print(f"\n❌ 文档创建失败: {result.get('error', 'unknown')}")

    print(f"🎉 完成！耗时 {time.time()-t0:.1f}秒")


if __name__ == "__main__":
    main()

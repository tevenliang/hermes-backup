#!/opt/homebrew/bin/python3.11
"""
客户新闻追踪 - 核心执行脚本
从飞书知识库表读取客户 → 查询新闻 → 创建飞书文档 → 回填 bitable

依赖：lark-cli（已在 ~/.lark-cli/config.json 配置好）
      TAVILY_API_KEY（环境变量或 config.json）

用法：
  python3 fetch_and_sync.py [--dry-run] [--company "企业名称"] [--date=YYYY-MM-DD]
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, date
from typing import Optional

# ============================================================
# 配置（优先读 config.json）
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR  = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "config", "config.json")

# 已知字段 ID
FIELD_IDS = {
    "Customer": "fldueSOrU3",
    "企业新闻": "fldC80mDeb",
    "企业新闻最后更新": "fldCeGnPG2",
}


def load_config():
    defaults = {
        "bitable": {"app_token": "BO6kb2c7haHY2FsLJCecH1mrnhe",
                    "table_id":  "tblDEBAW1NOq61Ch"},
        "lark":    {"folder_token": "K312fSiL0lApa8dLCARczd1jnUO"},
        "tavily":  {"api_key": ""},
    }
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user = json.load(f)
        defaults.update(user)
    except Exception:
        pass
    return defaults


CFG = load_config()
APP_TOKEN    = CFG["bitable"]["app_token"]
TABLE_ID     = CFG["bitable"]["table_id"]
FOLDER_TOKEN = CFG["lark"]["folder_token"]
TAVILY_KEY   = CFG.get("tavily", {}).get("api_key", "") or os.environ.get("TAVILY_API_KEY", "")
DRY_RUN      = "--dry-run" in sys.argv

# 日期覆盖（用于回填历史日期）
DATE_OVERRIDE = None
RESUME_FROM = None  # --resume-from N: 从第 N 家继续（1-based）
LIMIT = None  # --limit N: 最多处理 N 家
for arg in sys.argv:
    if arg.startswith("--date="):
        DATE_OVERRIDE = arg.split("=", 1)[1]
    if arg.startswith("--resume-from="):
        RESUME_FROM = int(arg.split("=", 1)[1])
    if arg.startswith("--limit="):
        LIMIT = int(arg.split("=", 1)[1])


def get_run_date():
    if DATE_OVERRIDE:
        return datetime.strptime(DATE_OVERRIDE, "%Y-%m-%d").date()
    return date.today()


# ============================================================
# 工具函数
# ============================================================

def run_lark(args: list[str]) -> dict:
    """执行 lark-cli 命令，返回 parsed JSON。"""
    cmd = ["lark-cli"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            cwd="/Users/twliang/.hermes"
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        output = result.stdout.strip()
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw": output}
    except subprocess.TimeoutExpired:
        return {"error": "命令超时"}
    except FileNotFoundError:
        return {"error": "lark-cli 未找到，请安装：npm install -g @larksuite/cli"}


def safe_filename(name: str) -> str:
    """生成安全的文件名。"""
    s = re.sub(r"[^\w\u4e00-\u9fff]", "_", name)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:30]


def search_news_eastmoney(company: str) -> list[dict]:
    """用东方财富妙想搜索企业新闻（优先数据源）。"""
    try:
        import subprocess, json, os

        env = os.environ.copy()
        env["EM_API_KEY"] = "em_psgou6ovS8WeuFqkUe4CXYn15iSi00di"
        script = "/Users/twliang/.hermes/skills/finance/mx-finance-search/scripts/get_data.py"

        result = subprocess.run(
            ["/opt/homebrew/bin/python3.11", script, f"{company}最新资讯"],
            capture_output=True, text=True, timeout=30, env=env
        )
        if result.returncode != 0:
            return []

        # stdout 前面有打印行（如"默认输出目录"、"Saved: ..."），JSON 从 { 开始
        stdout = result.stdout
        json_start = stdout.find("{")
        if json_start == -1:
            return []
        try:
            data = json.loads(stdout[json_start:])
        except Exception:
            return []

        items = data.get("data", [])
        if not items:
            return []

        # 取前 3 条，只保留有内容的记录
        results = []
        for item in items[:5]:
            content = item.get("content", "") or ""
            if len(content) < 50:
                continue
            results.append({
                "title": item.get("title", ""),
                "url": item.get("jumpUrl", ""),
                "content": content[:800]
            })
            if len(results) >= 3:
                break
        return results
    except Exception:
        return []


def search_news_tavily(company: str, api_key: str = None) -> list[dict]:
    """用 Tavily API 搜索企业新闻，限最近一周。"""
    if not api_key:
        api_key = TAVILY_KEY
    if not api_key:
        return []

    try:
        import urllib.request
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        query = f"{company} 新闻"
        params = json.dumps({
            "query": query,
            "search_depth": "basic",
            "max_results": 3,
            "max_date": week_ago
        }).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=params,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        return [
            {
                "title": r["title"],
                "url": r["url"],
                "content": r.get("content", "")[:500]
            }
            for r in results
        ]
    except Exception:
        return []


# ============================================================
# 核心流程
# ============================================================

def step1_read_bitable() -> list[dict]:
    """读取知识库表，按 Customer 字段返回企业记录列表。"""
    print("Step 1: 读取飞书知识库表...")
    res = run_lark([
        "base", "+record-list",
        "--as", "bot",
        "--base-token", APP_TOKEN,
        "--table-id", TABLE_ID,
        "--limit", "200"
    ])

    if "error" in res:
        print(f"   读取失败: {res['error']}")
        sys.exit(1)

    raw = res.get("data", {}).get("data", [])
    records = res.get("data", {}).get("record_id_list", [])
    field_names = res.get("data", {}).get("fields", [])

    name_to_idx = {fname: i for i, fname in enumerate(field_names)}

    companies = []
    for i, row in enumerate(raw):
        record_id = records[i] if i < len(records) else None
        cust_idx = name_to_idx.get("Customer")
        if cust_idx is not None and cust_idx < len(row):
            name = str(row[cust_idx]).strip() if row[cust_idx] else ""
        else:
            name = ""
        if not name:
            continue
        companies.append({
            "name": name,
            "record_id": record_id,
        })

    print(f"   共读取 {len(companies)} 家企业")
    return companies


def step2_fetch_news(company) -> Optional[dict]:
    """查询企业新闻，返回 {title, content, url} 或 None（无新闻则跳过）。"""
    name = company["name"]
    print(f"   查询 {name} 的新闻...")

    # 优先：东方财富妙想
    news_items = search_news_eastmoney(name)
    source = "东方财富"
    if not news_items:
        # 兜底：Tavily
        news_items = search_news_tavily(name, TAVILY_KEY)
        source = "Tavily"

    if not news_items:
        print(f"   无新闻（东方财富+Tavily 均无结果），跳过")
        return None

    item = news_items[0]
    print(f"   [{source}] {item['title'][:40]}...")
    return {
        "title": item["title"],
        "content": item["content"],
        "url": item["url"],
        "source": source,
    }


def step3_create_doc(company, news) -> Optional[str]:
    """创建飞书文档，返回 doc_token。"""
    name = company["name"]
    run_date = get_run_date()
    date_str = run_date.strftime("%Y-%m-%d")

    content = f"""# {name} 最新动态

> 更新时间：{date_str} {datetime.now().strftime('%H:%M')}

## 核心新闻
{news.get('title', name + ' 最新动态')}

{news.get('content', '')}

## 原文链接
{news.get('url', '')}

---
*由 Javis 自动生成 · {date_str}*
"""

    if DRY_RUN:
        print(f"   [DRY-RUN] 跳过创建文档: {name}")
        return f"dryrun_{safe_filename(name)}"

    # 写入到 scripts 目录
    tmp_path = "/Users/twliang/.hermes/skills/workspace/客户新闻追踪/scripts/customer_news_tmp.md"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 用 stdin 传入 markdown 内容，避免路径解析问题
    with open(tmp_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    import subprocess as sp_run
    proc = sp_run.run(
        ["lark-cli", "docs", "+create",
         "--as", "user",
         "--title", f"{name} 最新动态",
         "--folder-token", FOLDER_TOKEN,
         "--markdown", "-"],
        input=markdown_content,
        text=True,
        capture_output=True,
        cwd="/Users/twliang/.hermes"
    )
    res_raw = proc.stdout.strip()
    try:
        res = json.loads(res_raw)
    except:
        res = {"raw": res_raw}

    try:
        os.remove(tmp_path)
    except Exception:
        pass

    if "error" in res:
        print(f"   文档创建失败: {res['error']}")
        return None

    try:
        doc_token = res["data"].get("doc_id") or res["data"]["doc"]["doc_id"]
        print(f"   文档创建成功: {doc_token}")
        return doc_token
    except (KeyError, TypeError):
        print(f"   解析 doc_id 失败: {res}")
        return None


def step4_update_bitable(company: dict, doc_token: str):
    """回填 bitable：企业新闻(URL) + 企业新闻最后更新(日期)。"""
    record_id = company["record_id"]
    if not record_id:
        print(f"   无 record_id，跳过回填")
        return

    if DRY_RUN:
        print(f"   [DRY-RUN] 跳过回填: record_id={record_id}")
        return

    doc_url = f"https://www.feishu.cn/docx/{doc_token}" if doc_token and not doc_token.startswith("dryrun") else ""
    run_date = get_run_date()
    date_str = run_date.strftime("%Y-%m-%d")

    fields_json = {}
    if doc_url:
        fields_json[FIELD_IDS["企业新闻"]] = doc_url
    fields_json[FIELD_IDS["企业新闻最后更新"]] = date_str

    res = run_lark([
        "base", "+record-upsert",
        "--as", "bot",
        "--base-token", APP_TOKEN,
        "--table-id", TABLE_ID,
        "--record-id", record_id,
        "--json", json.dumps(fields_json, ensure_ascii=False)
    ])

    if "error" in res:
        print(f"   回填失败: {res['error']}")
    else:
        print(f"   bitable 回填成功")


def main():
    run_date = get_run_date()
    print(f"\n{'='*50}")
    print(f"  客户新闻追踪  {'[DRY-RUN]' if DRY_RUN else ''}")
    print(f"  {run_date.strftime('%Y-%m-%d')}")
    print(f"{'='*50}\n")

    companies = step1_read_bitable()
    if not companies:
        print("知识库表为空，退出")
        sys.exit(1)

    target = None
    for arg in sys.argv:
        if arg.startswith("--company="):
            target = arg.split("=", 1)[1]

    if target:
        companies = [c for c in companies if target in c["name"]]
        print(f"   筛选企业: {target}，共 {len(companies)} 条")

    success, failed, skipped = 0, 0, 0
    processed = 0

    for i, company in enumerate(companies):
        # 断点续传：跳过已处理的企业
        if RESUME_FROM is not None and (i + 1) < RESUME_FROM:
            continue
        # 数量限制
        if LIMIT is not None and processed >= LIMIT:
            break
        print(f"\n[{i+1}/{len(companies)}] 处理: {company['name']}")
        try:
            news = step2_fetch_news(company)
            if not news:
                skipped += 1
                continue
            processed += 1
            doc_token = step3_create_doc(company, news)
            if doc_token:
                step4_update_bitable(company, doc_token)
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   异常: {e}")
            failed += 1
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"  完成: 成功 {success} 家 / 失败 {failed} 家 / 无新闻跳过 {skipped} 家")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()

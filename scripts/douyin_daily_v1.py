#!/usr/bin/env python3
"""
每日抖音博主动态 - 重构版（lark-cli）
Usage:
    python3 douyin_daily.py              # 自动化模式：创建飞书文档
    python3 douyin_daily.py --direct     # 对话模式：直接输出内容到 stdout
"""
import json, time, os, re, sys, subprocess
from datetime import datetime, timedelta

# ========== 配置 ==========
FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"

GETNOTE_API_KEY = "gk_live_c17ca17f43b3e387.239acb0d412b328f585cb83afbd85179f83d3ac232015983"
GETNOTE_CLIENT_ID = "cli_3802f9db08b811f197679c63c078bacc"

# 知识库
KNOWLEDGE_BASES = [
    {"topic_id": "40DwN71Y", "name": "抖音常看", "is_vip": True},
    {"topic_id": "EJleDrPn", "name": "抖音",    "is_vip": False},
]
REQUEST_DELAY = 0.15
MAX_RETRIES = 3

# 状态文件
STATE_FILE = "/root/.openclaw/scripts/douyin_state.json"
CACHE_FILE = "/root/.openclaw/scripts/douyin_content_cache.json"
CACHE_TTL_SECONDS = 30 * 60

# ── lark-cli 封装 ──────────────────────────────
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

# ── 缓存读写 ───────────────────────────────────
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_cached(key, cache):
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry.get("_fetched_at", 0) > CACHE_TTL_SECONDS:
        return None
    return entry.get("contents")

# ========== 文档操作（lark-cli）==========
def create_doc(title):
    """用 lark-cli 创建文档（user 身份）"""
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

def create_shortcut(doc_token, title):
    """创建快捷方式到 FOLDER_TOKEN"""
    result = lark_cli([
        "drive", "+create-shortcut",
        "--file-token", doc_token,
        "--folder-token", FOLDER_TOKEN,
        "--type", "docx",
        "--as", "user"
    ])
    if not result.get("ok"):
        print(f"  ⚠️ 快捷方式创建失败: {result.get('error', {}).get('message', '')}")
    return result.get("ok")

# ========== 共用数据拉取 ==========
def fetch_posts(target_dates):
    """拉取新帖子数据，返回 new_posts + blogger_count"""
    state = load_state()
    processed_posts = set(state.get("processed_posts", []))
    content_cache = load_cache()
    new_posts = []
    blogger_count = 0

    for kb in KNOWLEDGE_BASES:
        topic_id = kb["topic_id"]
        kb_name = kb["name"]
        is_vip = kb["is_vip"]

        url = f"https://openapi.biji.com/open/api/v1/resource/knowledge/bloggers?topic_id={topic_id}"
        data = api_get_with_retry(url)
        bloggers = data.get("data", {}).get("bloggers", []) if data.get("success") else []

        for blogger in bloggers:
            author = blogger.get("account_name", "未知博主")
            follow_id = blogger.get("follow_id")
            if not follow_id:
                continue

            cache_key = f"{topic_id}:{follow_id}"
            contents = get_cached(cache_key, content_cache)

            if contents is None:
                time.sleep(REQUEST_DELAY)
                contents_url = f"https://openapi.biji.com/open/api/v1/resource/knowledge/blogger/contents?topic_id={topic_id}&follow_id={follow_id}"
                contents_data = api_get_with_retry(contents_url)
                contents = contents_data.get("data", {}).get("contents", []) if contents_data.get("success") else []
                content_cache[cache_key] = {"_fetched_at": time.time(), "contents": contents}
                save_cache(content_cache)

            blogger_count += 1

            for post in contents:
                create_date = (post.get("post_create_time") or "")[:10]
                if create_date not in target_dates:
                    continue
                post_id = post.get("post_id_alias") or post.get("post_id") or ""
                if post_id in processed_posts:
                    continue
                new_posts.append({
                    "is_vip": is_vip,
                    "author": author,
                    "post": post,
                    "post_date": create_date,
                    "post_id": post_id,
                })

    return new_posts, blogger_count, processed_posts

def api_get_with_retry(url, retries=MAX_RETRIES):
    headers = {
        "Authorization": f"Bearer {GETNOTE_API_KEY}",
        "X-Client-Id": GETNOTE_CLIENT_ID,
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if attempt < retries - 1:
                time.sleep(0.3)
                continue
            return {"success": False}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.3)
                continue
            return {"success": False}
    return {"success": False}

import urllib.request
import urllib.error

# ========== Block 构造 ==========
def make_text(text):
    return {"block_type": 2, "text": {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_heading(text, level=1):
    key = ["heading1", "heading2", "heading3"][level - 1]
    return {"block_type": level + 2, key: {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_bullet(text):
    return {"block_type": 12, "bullet": {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_link(text, url):
    """可点击超链接"""
    return {
        "block_type": 2,
        "text": {
            "elements": [{
                "type": "text_run",
                "text_run": {
                    "content": text,
                    "text_element_style": {"link": {"url": url}}
                }
            }],
            "style": {}
        }
    }

# ========== 飞书文档构造 ==========
def build_blocks(new_posts):
    blocks = []
    vip_posts = [p for p in new_posts if p["is_vip"]]
    normal_posts = [p for p in new_posts if not p["is_vip"]]

    if vip_posts:
        blocks.append(make_heading("⭐️ 抖音常看", 1))
        authors_vip = {}
        for p in vip_posts:
            author = p["author"]
            if author not in authors_vip:
                authors_vip[author] = []
            authors_vip[author].append(p)

        for author, posts in sorted(authors_vip.items()):
            blocks.append(make_heading(f"【{author}】", 2))
            for p in posts:
                post = p["post"]
                title = post.get("post_title") or post.get("post_name", "无标题")
                summary = post.get("post_summary", "").strip()
                post_url = post.get("post_url", "")

                blocks.append(make_heading(title, 3))
                if summary:
                    for line in summary.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        # 去掉开头的 "- " 或 "* "，统一当普通文本
                        if line.startswith("- ") or line.startswith("* "):
                            line = line[2:]
                        blocks.append(make_text(line))
                if post_url:
                    blocks.append(make_link("🔗 原文链接", post_url))

    if normal_posts:
        blocks.append(make_heading("📌 抖音", 1))
        authors_normal = {}
        for p in normal_posts:
            author = p["author"]
            if author not in authors_normal:
                authors_normal[author] = []
            authors_normal[author].append(p)

        for author, posts in sorted(authors_normal.items()):
            blocks.append(make_heading(f"【{author}】", 2))
            for p in posts:
                post = p["post"]
                title = post.get("post_title") or post.get("post_name", "无标题")
                summary = post.get("post_summary", "").strip()
                post_url = post.get("post_url", "")

                blocks.append(make_heading(title, 3))
                if summary:
                    for line in summary.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        # 去掉开头的 "- " 或 "* "，统一当普通文本
                        if line.startswith("- ") or line.startswith("* "):
                            line = line[2:]
                        blocks.append(make_text(line))
                if post_url:
                    blocks.append(make_link("🔗 原文链接", post_url))

    return blocks

# ========== 状态文件 ==========
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"processed_posts": []}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ========== 主逻辑 ==========
def main():
    t0 = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    target_dates = {today, yesterday}
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === 每日抖音动态开始 ===")

    new_posts, blogger_count, processed_posts = fetch_posts(target_dates)

    elapsed = time.time() - t0
    print(f"[INFO] 共扫描 {blogger_count} 个博主，新增 {len(new_posts)} 条，耗时 {elapsed:.1f}秒")

    if not new_posts:
        print("[INFO] 昨天和今天都没有新抖音笔记")
        state = load_state()
        state["processed_posts"] = list(processed_posts)
        save_state(state)
        print(f"[NO_NEW_POSTS] 耗时 {time.time()-t0:.1f}秒")
        return

    blocks = build_blocks(new_posts)
    now = datetime.now()
    doc_title = f"每日抖音动态-{now.strftime('%Y%m%d')}-{now.strftime('%H%M')}"
    doc_token, doc_url = create_doc(doc_title)
    if not doc_token:
        print("[ERROR] 创建飞书文档失败")
        return
    print(f"[INFO] 创建文档成功: {doc_token}")

    insert_blocks(doc_token, blocks)
    print(f"[INFO] 写入 {len(blocks)} 个 blocks")

    create_shortcut(doc_token, doc_title)

    # 更新 processed_posts
    for p in new_posts:
        pid = p.get("post_id", "")
        if pid:
            processed_posts.add(pid)
    state = load_state()
    state["processed_posts"] = list(processed_posts)
    save_state(state)

    elapsed = time.time() - t0
    vip = len([p for p in new_posts if p["is_vip"]])
    normal = len([p for p in new_posts if not p["is_vip"]])
    print(f"\n[DONE] ✅ 每日抖音动态完成！今日新增 {len(new_posts)} 条（⭐️{vip} / 📌{normal}），耗时 {elapsed:.1f}秒")
    print(f"📄 {doc_url}")

def direct_output():
    """对话模式：直接输出昨天+今天所有帖子内容到 stdout，不写飞书，不去重"""
    t0 = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    target_dates = {today, yesterday}

    content_cache = load_cache()
    all_posts = []
    blogger_count = 0

    for kb in KNOWLEDGE_BASES:
        topic_id = kb["topic_id"]
        kb_name = kb["name"]
        is_vip = kb["is_vip"]

        url = f"https://openapi.biji.com/open/api/v1/resource/knowledge/bloggers?topic_id={topic_id}"
        data = api_get_with_retry(url)
        bloggers = data.get("data", {}).get("bloggers", []) if data.get("success") else []

        for blogger in bloggers:
            author = blogger.get("account_name", "未知博主")
            follow_id = blogger.get("follow_id")
            if not follow_id:
                continue

            cache_key = f"{topic_id}:{follow_id}"
            contents = get_cached(cache_key, content_cache)

            if contents is None:
                time.sleep(REQUEST_DELAY)
                contents_url = f"https://openapi.biji.com/open/api/v1/resource/knowledge/blogger/contents?topic_id={topic_id}&follow_id={follow_id}"
                contents_data = api_get_with_retry(contents_url)
                contents = contents_data.get("data", {}).get("contents", []) if contents_data.get("success") else []
                content_cache[cache_key] = {"_fetched_at": time.time(), "contents": contents}
                save_cache(content_cache)

            blogger_count += 1

            for post in contents:
                create_date = (post.get("post_create_time") or "")[:10]
                if create_date not in target_dates:
                    continue
                all_posts.append({
                    "is_vip": is_vip,
                    "author": author,
                    "post": post,
                    "post_date": create_date,
                })

    print(f"[INFO] 共扫描 {blogger_count} 个博主，{len(all_posts)} 条帖子，耗时 {time.time()-t0:.1f}秒")

    format_posts_text(all_posts)

# ========== 对话输出 ==========
def _print_post(post, tag_str):
    title = post.get("post_title") or post.get("post_name", "无标题")
    summary = post.get("post_summary", "").strip()
    post_url = post.get("post_url", "")

    print(f"  📌 {title}")
    if summary:
        for line in summary.split("\n"):
            line = line.strip()
            if line:
                print(f"     {line}")
    if tag_str:
        print(f"     🏷️ {tag_str}")
    if post_url:
        print(f"     🔗 {post_url}")
    print()

def format_posts_text(all_posts):
    vip_posts = [p for p in all_posts if p["is_vip"]]
    normal_posts = [p for p in all_posts if not p["is_vip"]]

    if vip_posts:
        print("\n⭐️ 抖音常看\n")
        by_author = {}
        for p in vip_posts:
            a = p["author"]
            if a not in by_author:
                by_author[a] = []
            by_author[a].append(p)
        for author, posts in sorted(by_author.items()):
            print(f"【{author}】")
            for p in posts:
                post = p["post"]
                tags = post.get("tags", [])
                tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
                _print_post(post, tag_str)

    if normal_posts:
        print("\n📌 抖音\n")
        by_author = {}
        for p in normal_posts:
            a = p["author"]
            if a not in by_author:
                by_author[a] = []
            by_author[a].append(p)
        for author, posts in sorted(by_author.items()):
            print(f"【{author}】")
            for p in posts:
                post = p["post"]
                tags = post.get("tags", [])
                tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
                _print_post(post, tag_str)

if __name__ == "__main__":
    if "--direct" in sys.argv:
        direct_output()
    else:
        main()

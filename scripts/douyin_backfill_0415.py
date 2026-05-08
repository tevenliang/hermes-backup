#!/usr/bin/env python3
"""一次性：补拉 04-15 的抖音动态"""
import json, time, os, urllib.request
from datetime import datetime, timedelta
import urllib.error

FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"

GETNOTE_API_KEY = "gk_live_d0b7a52ca53cc086.fbf5df41108444e8ca551c9cff3d3ce390d9a9406e410930"
GETNOTE_CLIENT_ID = "cli_a1b2c3d4e5f6789012345678abcdef90"

KNOWLEDGE_BASES = [
    {"topic_id": "40DwN71Y", "name": "抖音常看", "is_vip": True},
    {"topic_id": "EJleDrPn", "name": "抖音",    "is_vip": False},
]
REQUEST_DELAY = 0.15
MAX_RETRIES = 3
STATE_FILE = "/root/.openclaw/scripts/douyin_state.json"

TARGET_DATE = "2026-04-15"

def get_headers():
    return {"Authorization": GETNOTE_API_KEY, "X-Client-ID": GETNOTE_CLIENT_ID}

def api_get_with_retry(url, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=get_headers())
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 0.5 * (2 ** attempt)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(0.3)
                continue
            return {"success": False, "data": None}
    return {"success": False, "data": None}

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("tenant_access_token", "")

def create_doc(token, title):
    url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    payload = json.dumps({"title": title}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.loads(r.read().decode())
    if d.get("code") != 0:
        return None
    return d.get("data", {}).get("document", {}).get("document_id", "")

def insert_blocks(token, doc_token, blocks):
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{doc_token}/children"
    for i in range(0, len(blocks), 50):
        batch = blocks[i:i+50]
        payload = json.dumps({"children": batch}).encode()
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
        if d.get("code") != 0:
            print(f"  [WARN] insert error: {d.get('msg')}")
        time.sleep(0.3)

def make_heading(text, level=1):
    key = ["heading1", "heading2", "heading3"][level - 1]
    return {"block_type": level + 2, key: {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_text(text):
    return {"block_type": 2, "text": {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_bullet(text):
    return {"block_type": 12, "bullet": {"elements": [{"type": "text_run", "text_run": {"content": text}}], "style": {}}}

def make_link(text, url):
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

def main():
    t0 = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === 补拉 04-15 抖音动态 ===")

    new_posts = []
    blogger_count = 0

    for kb in KNOWLEDGE_BASES:
        topic_id = kb["topic_id"]
        kb_name = kb["name"]
        is_vip = kb["is_vip"]

        url = f"https://openapi.biji.com/open/api/v1/resource/knowledge/bloggers?topic_id={topic_id}"
        data = api_get_with_retry(url)
        bloggers = data.get("data", {}).get("bloggers", []) if data.get("success") else []
        print(f"[INFO] 知识库「{kb_name}」: {len(bloggers)} 个博主")

        for blogger in bloggers:
            author = blogger.get("account_name", "未知博主")
            follow_id = blogger.get("follow_id")
            if not follow_id:
                continue

            time.sleep(REQUEST_DELAY)
            contents_url = f"https://openapi.biji.com/open/api/v1/resource/knowledge/blogger/contents?topic_id={topic_id}&follow_id={follow_id}"
            contents_data = api_get_with_retry(contents_url)
            contents = contents_data.get("data", {}).get("contents", []) if contents_data.get("success") else []

            blogger_count += 1

            for post in contents:
                post_id = post.get("post_id_alias", "")
                create_date = (post.get("post_create_time") or "")[:10]
                if create_date != TARGET_DATE:
                    continue
                new_posts.append({
                    "is_vip": is_vip,
                    "author": author,
                    "post": post,
                    "post_date": create_date,
                    "post_id": post_id
                })

    print(f"[INFO] 共扫描 {blogger_count} 个博主，04-15 新增 {len(new_posts)} 条")

    if not new_posts:
        print("[INFO] 04-15 无新帖子")
        return

    vip_posts = [p for p in new_posts if p["is_vip"]]
    normal_posts = [p for p in new_posts if not p["is_vip"]]

    blocks = []
    if vip_posts:
        blocks.append(make_heading("⭐️ 抖音常看", 1))
        authors_vip = {}
        for p in vip_posts:
            if p["author"] not in authors_vip:
                authors_vip[p["author"]] = []
            authors_vip[p["author"]].append(p)
        for author, posts in sorted(authors_vip.items()):
            blocks.append(make_heading(f"【{author}】", 2))
            for p in posts:
                post = p["post"]
                title = post.get("post_title") or post.get("post_name", "无标题")
                summary = post.get("post_summary", "").strip()
                post_url = post.get("post_url", "")
                tags = post.get("tags", [])
                tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
                blocks.append(make_heading(title, 3))
                if summary:
                    for line in summary.split("\n"):
                        line = line.strip()
                        if line:
                            blocks.append(make_text(line))
                if tag_str:
                    blocks.append(make_text(f"🏷️ {tag_str}"))
                if post_url:
                    blocks.append(make_link("🔗 原文链接", post_url))

    if normal_posts:
        blocks.append(make_heading("📌 抖音", 1))
        authors_normal = {}
        for p in normal_posts:
            if p["author"] not in authors_normal:
                authors_normal[p["author"]] = []
            authors_normal[p["author"]].append(p)
        for author, posts in sorted(authors_normal.items()):
            blocks.append(make_heading(f"【{author}】", 2))
            for p in posts:
                post = p["post"]
                title = post.get("post_title") or post.get("post_name", "无标题")
                summary = post.get("post_summary", "").strip()
                post_url = post.get("post_url", "")
                tags = post.get("tags", [])
                tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
                blocks.append(make_heading(title, 3))
                if summary:
                    for line in summary.split("\n"):
                        line = line.strip()
                        if line:
                            blocks.append(make_text(line))
                if tag_str:
                    blocks.append(make_text(f"🏷️ {tag_str}"))
                if post_url:
                    blocks.append(make_link("🔗 原文链接", post_url))

    token = get_feishu_token()
    doc_title = f"每日抖音动态 2026-04-15"
    doc_token = create_doc(token, doc_title)
    if not doc_token:
        print("[ERROR] 创建文档失败")
        return
    print(f"[INFO] 文档创建成功: {doc_token}")

    insert_blocks(token, doc_token, blocks)
    print(f"[INFO] 写入 {len(blocks)} 个 blocks")

    doc_link = f"https://feishu.cn/docx/{doc_token}"
    print(f"\n[DONE] ✅ 04-15 抖音动态完成！共 {len(new_posts)} 条（⭐️{len(vip_posts)} / 📌{len(normal_posts)}），耗时 {time.time()-t0:.1f}秒")
    print(f"📄 {doc_link}")

if __name__ == "__main__":
    main()

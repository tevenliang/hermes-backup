#!/usr/bin/env python3
"""
Get笔记每日同步
逻辑：API 从 newest 往旧走，遍历时遇到 processed 里已有的 ID 就停止（它后面的必然更旧，无需再处理）
"""
import json, time, os, re, subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.error

# ========== 配置 ==========
FEISHU_APP_ID = "cli_a97cf4a2bef8dcce"
FEISHU_APP_SECRET = "BQEEuScBOAzPa0ywZBpJue4y5wOFuP55"
GETNOTE_API_KEY = "gk_live_c17ca17f43b3e387.239acb0d412b328f585cb83afbd85179f83d3ac232015983"
GETNOTE_CLIENT_ID = "cli_3802f9db08b811f197679c63c078bacc"

BITABLE_APP_TOKEN = "VNLrbIYoAausDOs5uovcO7fPn0d"
BITABLE_TABLE_ID = "tbl2vVHnujNPQczd"

STATE_FILE = "/Users/twliang/.hermes/scripts/getnote_state.json"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"
WORKSPACE = "/Users/twliang/.hermes"

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

def create_doc_markdown(title, markdown_content):
    safe_name = re.sub(r'[^\w\-]', '_', title[:50])
    md_file = f"tmp_note_{safe_name}.md"
    md_path = os.path.join(WORKSPACE, md_file)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    try:
        return lark_cli([
            "docs", "+create",
            "--title", title[:100],
            "--markdown", f"@{md_file}",
            "--as", "user",
            "--folder-token", FOLDER_TOKEN
        ])
    finally:
        if os.path.exists(md_path):
            os.remove(md_path)

# ========== 多维表格写入 ==========
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("tenant_access_token", "")

def write_bitable_record(title, url_link):
    """写入飞书多维表格（lark-cli generic API）"""
    import subprocess, json
    app_token = "VNLrbIYoAausDOs5uovcO7fPn0d"
    table_id = "tbl2vVHnujNPQczd"
    payload = {
        "records": [{
            "fields": {
                "文章标题": {"link": url_link, "text": title}
            }
        }]
    }
    cmd = [
        "lark-cli", "api", "POST",
        f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
        "--data", json.dumps(payload),
        "--as", "user"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, cwd="/Users/twliang/.hermes")
    if proc.returncode == 0:
        result = json.loads(proc.stdout)
        if result.get("code") == 0:
            print(f"  多维表格写入成功")
        else:
            print(f"  [WARN] 多维表格写入失败: {result.get('msg')}")
    else:
        print(f"  [WARN] 多维表格写入失败: {proc.stderr[:100]}")

# ========== GetNotes API ==========
def get_headers():
    return {"Authorization": GETNOTE_API_KEY, "X-Client-ID": GETNOTE_CLIENT_ID}

def list_notes_page(cursor=""):
    url = f"https://openapi.biji.com/open/api/v1/resource/note/list?since_id={cursor}"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def get_note_detail(note_id, retries=3):
    url = f"https://openapi.biji.com/open/api/v1/resource/note/detail?id={note_id}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=get_headers())
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt)  # 429: wait and retry
                continue
            raise
    return {}  # all retries failed

# ========== Markdown 内容构造 ==========
def build_note_markdown(note, detail, web_url_override=None):
    title = note.get("title", "无标题") or "无标题"
    created = note.get("created_at", "")[:19]
    tags = note.get("tags", [])
    tag_names = [t.get("name", "") if isinstance(t, dict) else str(t) for t in tags]
    tag_str = " ".join(f"#{name}" for name in tag_names if name) if tag_names else ""
    note_type = note.get("note_type", "unknown")
    web_url = web_url_override or (note.get("web_page", {}).get("url", "") if isinstance(note.get("web_page"), dict) else "")
    content = detail.get("content", note.get("content", "")).strip()

    lines = []
    lines.append(f"# 📝 {title}")
    lines.append(f"")
    lines.append(f"**📅 创建时间：** {created}")
    lines.append(f"**📂 类型：** {note_type}")
    if tag_str:
        lines.append(f"**🏷️ {tag_str}**")
    if web_url:
        lines.append(f"**🔗 原文链接：** [查看原文]({web_url})")
    lines.append(f"")
    lines.append(f"## 正文")
    lines.append(f"")

    if content:
        content = content.replace("\\n", "\n")
        raw_lines = content.split("\n")
        j = 0
        while j < len(raw_lines):
            line = raw_lines[j]
            stripped = line.strip()
            if not stripped:
                lines.append("")
                j += 1
                continue
            if stripped.startswith("```"):
                code_lines = []
                j += 1
                while j < len(raw_lines) and raw_lines[j].strip().startswith("```"):
                    code_lines.append(raw_lines[j])
                    j += 1
                lines.append("```")
                lines.extend(code_lines)
                lines.append("```")
                lines.append("")
                j += 1
                continue
            if stripped.startswith(">"):
                lines.append(f"> {stripped.lstrip('> ').replace('*', '')}")
                j += 1
                continue
            if is_md_table_row(stripped):
                table_lines = []
                while j < len(raw_lines) and is_md_table_row(raw_lines[j].strip()):
                    table_lines.append(raw_lines[j].strip())
                    j += 1
                lines.extend(table_lines)
                continue
            if re.match(r'^[-*_]{3,}\s*$', stripped):
                lines.append(stripped)
                j += 1
                continue
            hm = re.match(r'^(#{1,6})\s+(.+)', stripped)
            if hm:
                lines.append(f"{'#' * len(hm.group(1))} {hm.group(2)}")
                j += 1
                continue
            bm = re.match(r'^[-*+]\s+(.+)', stripped)
            if bm:
                lines.append(f"· {bm.group(1)}")
                j += 1
                continue
            om = re.match(r'^\d+\.\s+(.+)', stripped)
            if om:
                lines.append(om.group(1))
                j += 1
                continue
            lines.append(stripped)
            j += 1
    else:
        lines.append("（无正文内容）")
    return "\n".join(lines)

def is_md_table_row(line):
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return False
    inner = stripped[1:-1].strip()
    if not inner or re.match(r'^[|:\-\s]+$', inner):
        return False
    return True

# ========== 状态管理 ==========
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_sync": "", "processed_notes": [], "last_note_id": "0"}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ========== 主逻辑 ==========
def main():
    t0 = time.time()
    script_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === Get笔记同步开始 ===")

    state = load_state()
    processed = set(state.get("processed_notes", []))
    print(f"[INFO] 已处理笔记数: {len(processed)}")

    # 增量同步：从 cursor=0（最新笔记）开始，逐页往旧遍历
    # 遇到第一条 in processed 的笔记就停止（它后面的全部是已处理的，无需再看）
    all_new_notes = []
    cursor = "0"
    page_count = 0
    stop_reason = ""

    # 首次运行（processed 为空）限制只取前 5 页（约50条），建立基线后下次增量同步
    is_first_run = (len(processed) == 0)
    max_pages = 5 if is_first_run else 200

    while True:
        page_count += 1
        if page_count > max_pages:
            stop_reason = f"首次运行限制({max_pages}页)" if is_first_run else "超过200页限制"
            break

        data = list_notes_page(cursor)
        notes = data.get("data", {}).get("notes", []) if data.get("success") else []
        has_more = data.get("data", {}).get("has_more", False)
        next_cursor = str(data.get("data", {}).get("next_cursor", ""))

        if not notes:
            stop_reason = "API返回空"
            break

        print(f"[INFO] 第 {page_count} 页: {len(notes)} 条")

        # 逐条检查：遇到已处理的笔记就停止遍历
        for note in notes:
            nid = str(note.get("id", ""))
            if nid in processed:
                print(f"[INFO] 遇到已处理笔记 ID={nid}，停止遍历")
                stop_reason = f"遇到已处理笔记（{nid}）"
                break
            all_new_notes.append(note)

        if stop_reason:
            break

        if not has_more or not next_cursor or next_cursor == cursor:
            stop_reason = "API没有更多数据"
            break
        cursor = next_cursor

    print(f"[INFO] 遍历完成，共 {page_count} 页，新增笔记: {len(all_new_notes)} 条（{stop_reason}）")

    if not all_new_notes:
        print("[INFO] 没有新笔记")
        state["last_sync"] = script_start
        save_state(state)
        print(f"[DONE] 耗时 {time.time()-t0:.1f}秒")
        return

    # 写入飞书文档
    success_count = 0
    failed_count = 0
    new_processed = list(processed)
    created_doc_urls = []

    # 先并发获取所有笔记详情
    print(f"[INFO] 并发获取 {len(all_new_notes)} 条笔记详情...")
    note_details = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(get_note_detail, str(note.get("id", ""))): note for note in all_new_notes}
        for future in as_completed(futures):
            note = futures[future]
            nid = str(note.get("id", ""))
            try:
                detail_data = future.result()
                detail = detail_data.get("data", {}).get("note", {}) if detail_data.get("success") else {}
                note_details[nid] = (note, detail)
            except Exception as e:
                note_details[nid] = (note, {})

    # 再逐条创建文档
    for i, note in enumerate(all_new_notes, 1):
        nid = str(note.get("id", ""))
        title = note.get("title", "无标题") or "无标题"
        created = note.get("created_at", "")[:19]
        tags = note.get("tags", [])
        tag_names = [t.get("name", "") if isinstance(t, dict) else str(t) for t in tags]
        tag_str = " ".join(f"#{name}" for name in tag_names if name) if tag_names else ""
        note_type = note.get("note_type", "unknown")
        web_url = note.get("web_page", {}).get("url", "") if isinstance(note.get("web_page"), dict) else ""

        print(f"[{i}/{len(all_new_notes)}] 处理: {title[:30]}...")

        note, detail = note_details.get(nid, (note, {}))
        content = detail.get("content", note.get("content", "")).strip()

        attachments = detail.get("attachments", [])
        att_url = attachments[0].get("url", "") if attachments else ""
        web_url = att_url or detail.get("web_page", {}).get("url", "") or web_url

        md_content = build_note_markdown(note, detail, web_url_override=web_url)
        result = create_doc_markdown(title[:120], md_content)

        if result.get("ok"):
            doc_url = result.get("data", {}).get("doc_url", "（无URL）")
            print(f"  文档创建成功: {doc_url}")
            created_doc_urls.append((title, doc_url))
            write_bitable_record(title, doc_url)
            success_count += 1
            new_processed.append(nid)
        else:
            err = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else str(result.get("error", ""))
            print(f"  文档创建失败: {err}（稍后重试）")
            failed_count += 1

        time.sleep(0.5)

    # 更新状态
    if all_new_notes:
        oldest = min(all_new_notes, key=lambda n: n.get("created_at", ""))
        state["last_note_id"] = str(oldest.get("id", state.get("last_note_id", "0")))
    state["last_sync"] = script_start
    state["processed_notes"] = new_processed[-1000:]
    save_state(state)

    elapsed = time.time() - t0
    print(f"\n[DONE] ✅ Get笔记同步完成！新增 {success_count} 条，失败 {failed_count} 条，耗时 {elapsed:.1f}秒")
    if created_doc_urls:
        print("同步的笔记：")
        for title, url in created_doc_urls:
            print(f"  · {title}")
        print("文档链接：")
        for title, url in created_doc_urls:
            print(f"  {url}")
    else:
        print("无新增文档")

if __name__ == "__main__":
    main()
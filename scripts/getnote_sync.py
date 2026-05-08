#!/usr/bin/env python3
"""
Get笔记每日同步 - lark-cli版
使用 lark-cli --as user 创建文档（用户身份，文档归属用户）

1. 从 GetNotes API 获取所有笔记（分页，从新到旧）
2. 过滤出不在 processed 列表中的笔记（新笔记）
3. 每条笔记生成 Markdown 内容
4. 用 lark-cli --as user 创建飞书文档（存入 400 贾维斯文件夹）
5. 更新状态文件

🔑 增量同步逻辑：
- processed 列表（来自上次状态文件）中没有的笔记 → 新笔记，全部捕获
- processed 列表中已有的笔记 → 跳过（防重）
- 不依赖时间过滤（因为上次 bug 导致漏掉的笔记时间可能早于 last_sync）
"""
import json, time, os, re, subprocess, tempfile
from datetime import datetime, timedelta
import urllib.request, urllib.error

# ========== 配置 ==========
FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
GETNOTE_API_KEY = "gk_live_c17ca17f43b3e387.239acb0d412b328f585cb83afbd85179f83d3ac232015983"
GETNOTE_CLIENT_ID = "cli_3802f9db08b811f197679c63c078bacc"

BITABLE_APP_TOKEN = "VNLrbIYoAausDOs5uovcO7fPn0d"
BITABLE_TABLE_ID = "tbl2vVHnujNPQczd"

STATE_FILE = "/root/.openclaw/scripts/getnote_state.json"
FOLDER_TOKEN = "K312fSiL0lApa8dLCARczd1jnUO"
WORKSPACE = "/root/.openclaw/workspace"
MAX_PAGE_SIZE = 500

# ========== lark-cli 封装 ==========
def lark_cli(cmd_list, data_str=None, cwd=WORKSPACE):
    args = ["lark-cli"] + cmd_list
    if data_str is not None:
        args += ["--data", "-"]
    proc = subprocess.run(
        args,
        input=data_str,
        capture_output=True, text=True, timeout=30,
        cwd=cwd
    )
    if proc.returncode == 0:
        try:
            return json.loads(proc.stdout)
        except:
            return {"ok": False, "error": proc.stdout}
    return {"ok": False, "error": proc.stderr or proc.stdout}

def create_doc_markdown(title, markdown_content):
    """用 lark-cli 创建飞书文档（user 身份），markdown 内容写入"""
    safe_name = re.sub(r'[^\w\-]', '_', title[:50])
    md_file = f"tmp_note_{safe_name}.md"
    md_path = os.path.join(WORKSPACE, md_file)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    try:
        result = lark_cli([
            "docs", "+create",
            "--title", title[:100],
            "--markdown", f"@{md_file}",
            "--as", "user",
            "--folder-token", FOLDER_TOKEN
        ])
        return result
    finally:
        if os.path.exists(md_path):
            os.remove(md_path)

# ========== 多维表格写入（知识库）==========
def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode()).get("tenant_access_token", "")

def write_bitable_record(title, url_link):
    """写入多维表格（知识库），标题+链接"""
    token = get_feishu_token()
    if not token:
        print("  [WARN] 无法获取飞书 token，跳过多维表格写入")
        return
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{BITABLE_TABLE_ID}/records"
    fields = {
        "文章标题": {"link": url_link, "text": title},
    }
    payload = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read().decode())
        if result.get("code") == 0:
            record_id = result.get("data", {}).get("record", {}).get("id")
            print(f"  ✅ 多维表格写入成功 (record={record_id})")
        else:
            print(f"  [WARN] 多维表格写入失败: {result.get('msg')}")
    except Exception as e:
        print(f"  [WARN] 多维表格异常: {e}")

# ========== GetNotes API ==========
def get_headers():
    return {"Authorization": GETNOTE_API_KEY, "X-Client-ID": GETNOTE_CLIENT_ID}

def list_notes_page(since_id="0"):
    url = f"https://openapi.biji.com/open/api/v1/resource/note/list?since_id={since_id}"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def get_note_detail(note_id):
    url = f"https://openapi.biji.com/open/api/v1/resource/note/detail?id={note_id}"
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

# ========== Markdown 内容构造 ==========
def build_note_markdown(note, detail, web_url_override=None):
    """将单条笔记构造为 Markdown 格式字符串"""
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
                while j < len(raw_lines):
                    if raw_lines[j].strip().startswith("```"):
                        j += 1
                        break
                    code_lines.append(raw_lines[j])
                    j += 1
                lines.append("```")
                lines.extend(code_lines)
                lines.append("```")
                lines.append("")
                continue

            if stripped.startswith(">"):
                quote_text = stripped.lstrip("> ").replace("*", "")
                lines.append(f"> {quote_text}")
                j += 1
                continue

            if is_md_table_row(stripped):
                table_lines = []
                while j < len(raw_lines) and is_md_table_row(raw_lines[j].strip()):
                    table_lines.append(raw_lines[j].strip())
                    j += 1
                for tline in table_lines:
                    lines.append(tline)
                continue

            if re.match(r'^[-*_]{3,}\s*$', stripped):
                lines.append(stripped)
                j += 1
                continue

            heading_match = re.match(r'^(#{1,6})\s+(.+)', stripped)
            if heading_match:
                level = len(heading_match.group(1))
                lines.append(f"{'#' * level} {heading_match.group(2)}")
                j += 1
                continue

            bullet_match = re.match(r'^[-*+]\s+(.+)', stripped)
            if bullet_match:
                lines.append(f"· {bullet_match.group(1)}")
                j += 1
                continue

            ordered_match = re.match(r'^\d+\.\s+(.+)', stripped)
            if ordered_match:
                lines.append(f"{ordered_match.group(1)}")
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
    if not inner:
        return False
    if re.match(r'^[|:\-\s]+$', inner):
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

    # 用脚本开始时间作为同步边界（不用结束时间，避免新建笔记被误判）
    from datetime import datetime as dt
    sync_cutoff_str = state.get("last_sync", "")
    if sync_cutoff_str:
        try:
            sync_cutoff_dt = dt.strptime(sync_cutoff_str, "%Y-%m-%d %H:%M:%S")
        except:
            sync_cutoff_dt = dt.min
    else:
        sync_cutoff_dt = dt.min

    print(f"[INFO] 增量同步边界: {sync_cutoff_str or '从未同步'}（脚本开始时间: {script_start}）")

    # 1. 从最新笔记开始遍历，用时间过滤找新笔记
    # cursor="0" 从最新开始，API 按 ID 倒序返回
    # 遇到 created_at <= last_sync → 停止（已到边界）
    all_new_notes = []
    cursor = "0"
    page_count = 0

    print(f"[INFO] 从最新笔记开始，sync_cutoff={sync_cutoff_str or '从未同步'}")
    while True:
        page_count += 1
        if page_count > MAX_PAGE_SIZE:
            print(f"[WARN] 超过 {MAX_PAGE_SIZE} 页，停止")
            break

        data = list_notes_page(cursor)
        notes = data.get("data", {}).get("notes", []) if data.get("success") else []
        has_more = data.get("data", {}).get("has_more", False)
        next_cursor = str(data.get("data", {}).get("next_cursor", ""))

        if not notes:
            break

        print(f"[INFO] 第 {page_count} 页: {len(notes)} 条")

        page_has_new = False
        for note in notes:
            nid = str(note.get("id", ""))
            # 用 created_at 时间判断是否是新笔记
            created_str = note.get("created_at", "")[:19]
            try:
                created_dt = dt.strptime(created_str, "%Y-%m-%d %H:%M:%S")
            except:
                created_dt = dt.min

            # 🔑 增量核心：created_at > sync_cutoff_dt → 新笔记
            # created_at <= sync_cutoff_dt → 到边界了，停止翻页
            if created_dt <= sync_cutoff_dt:
                print(f"[INFO] 遇到 {created_str}（<= {sync_cutoff_str}），停止翻页")
                break

            # 新笔记：检查是否已处理过
            if nid in processed:
                # 已处理但时间更新，跳过（不应该出现，但容错处理）
                continue
            all_new_notes.append(note)
            page_has_new = True

        if created_dt <= sync_cutoff_dt:
            break  # 外层 while 也停止

        if not has_more or not next_cursor or next_cursor == "0":
            break
        cursor = next_cursor

    print(f"[INFO] 遍历完成，共 {page_count} 页，新增笔记: {len(all_new_notes)} 条")

    if not all_new_notes:
        print("[INFO] 没有新笔记")
        state["last_sync"] = script_start
        save_state(state)
        print(f"[NO_NEW_NOTES] 耗时 {time.time()-t0:.1f}秒")
        return

    # 2. 用 lark-cli 写入飞书文档（user 身份）
    success_count = 0
    failed_count = 0
    new_processed = list(processed)
    created_doc_urls = []  # 收集所有创建的文档链接

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

        # 获取详情
        detail_data = get_note_detail(nid)
        detail = detail_data.get("data", {}).get("note", {}) if detail_data.get("success") else {}
        content = detail.get("content", note.get("content", "")).strip()

        # 优先从 attachments 取原文链接（link类型笔记才有），web_page.url 备选
        attachments = detail.get("attachments", [])
        att_url = attachments[0].get("url", "") if attachments else ""
        web_url = att_url or detail.get("web_page", {}).get("url", "") or web_url

        # 构造 Markdown 内容
        md_content = build_note_markdown(note, detail, web_url_override=web_url)

        # 用 lark-cli 创建文档（user 身份）
        doc_title = title[:120]
        result = create_doc_markdown(doc_title, md_content)

        if result.get("ok"):
            doc_token = result.get("data", {}).get("doc_id", "")
            doc_url = result.get("data", {}).get("doc_url", "（无URL）")
            print(f"  ✅ 文档创建成功: {doc_url}")
            created_doc_urls.append((doc_title, doc_url))
            write_bitable_record(doc_title, doc_url)
            success_count += 1
        else:
            err = result.get("error", {}).get("message", "") if isinstance(result.get("error"), dict) else str(result.get("error", ""))
            print(f"  ❌ 文档创建失败: {err}")
            failed_count += 1

        new_processed.append(nid)
        time.sleep(0.5)

    # 3. 更新状态
    if all_new_notes:
        newest = max(all_new_notes, key=lambda n: n.get("created_at", ""))
        state["last_note_id"] = str(newest.get("id", state.get("last_note_id", "0")))
    state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["processed_notes"] = new_processed[-1000:]
    save_state(state)

    elapsed = time.time() - t0
    doc_links = "\n".join([f"  - {title}: {url}" for title, url in created_doc_urls]) or "（无）"
    print(f"\n[DONE] ✅ Get笔记同步完成！新增 {success_count} 条，失败 {failed_count} 条，耗时 {elapsed:.1f}秒\n生成的飞书文档：\n{doc_links}")

if __name__ == "__main__":
    main()

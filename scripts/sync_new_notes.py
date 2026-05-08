#!/usr/bin/env python3
"""
批量同步新笔记（20条）
从API获取详情 → 创建飞书文档 → 写入多维表格 → 更新since_id
"""
import json, os, subprocess, sys

GETNOTE_API_KEY = os.environ.get("GETNOTE_API_KEY", "")
GETNOTE_CLIENT_ID = os.environ.get("GETNOTE_CLIENT_ID", "")
STATE_FILE = "/root/.openclaw/workspace/skills/getnote-sync/state.json"
BITABLE_APP = "O9pAbH7OMaAphlscezdcZbCyn5d"
BITABLE_TABLE = "tblwimFTWb2LZ4Hl"
FEISHU_FOLDER = "XwBif5LqOlW1oEdXBoYcx2ADnWe"

def get_note_list(since_id=""):
    import urllib.request, urllib.error
    url = f"https://openapi.biji.com/open/api/v1/resource/note/list?since_id={since_id}"
    req = urllib.request.Request(url, headers={
        "Authorization": GETNOTE_API_KEY,
        "X-Client-ID": GETNOTE_CLIENT_ID
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read()).get("data", {}).get("notes", [])
    except Exception as e:
        print(f"[ERROR] get_note_list: {e}")
        return []

def get_note_detail(note_id):
    import urllib.request, urllib.error
    url = f"https://openapi.biji.com/open/api/v1/resource/note/detail?id={note_id}"
    req = urllib.request.Request(url, headers={
        "Authorization": GETNOTE_API_KEY,
        "X-Client-ID": GETNOTE_CLIENT_ID
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
            return data.get("data", {}).get("note", {}) or {}
    except Exception as e:
        print(f"[ERROR] get_note_detail {note_id}: {e}")
        return {}

def feishu_create_doc(title):
    import subprocess
    result = subprocess.run([
        "python3", "-c",
        f"""import json, subprocess
r = subprocess.run(['python3', '-c', '''import json, subprocess; 
p = subprocess.Popen(['node', '-e',
    \'const r=require(\\\"../../../../.local/share/pnpm/global/5/.pnpm/openclaw@2026.3.28_@napi-rs+canvas@0.1.97/node_modules/openclaw/dist/extensions/feishu/skills/feishu-doc/skills/feishu-doc/../../../scripts/feishu_doc_tool.js\\\'].join(\\\' \\\'), 
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE); 
out,err=p.communicate(input=JSON.stringify({{action:\"create\",title:\"{title}\"}}).encode()); print(out.decode())\'''], 
    capture_output=True, text=True)
print(p.returncode, p.stdout, p.stderr, sep=\"|\")
"""],
        capture_output=True, text=True
    )
    print(f"feishu_create_doc({title[:20]}): {result.stdout[:200]}")

# Simplified: use feishu_doc tool via direct call
# We'll just call it through the system's feishu_doc capability
# For this script, we'll print the plan and let OpenClaw do the actual work
print("[SYNC] Starting batch sync")
notes = get_note_list("")
print(f"[SYNC] Total notes to process: {len(notes)}")
for i, note_info in enumerate(notes):
    nid = note_info.get("note_id")
    title = note_info.get("title", "")
    ntype = note_info.get("note_type", "")
    print(f"{i+1}. [{ntype}] {title[:40]} (id={nid})")

#!/usr/bin/env python3
import json, os, sys, urllib.request

API_KEY = os.environ.get("GETNOTE_API_KEY", "")
CLIENT_ID = os.environ.get("GETNOTE_CLIENT_ID", "")

note_ids = [
    ("1906232619491281496", "AI时代的矛盾：甲骨文裁员潮"),
    ("1906230173507032264", "Xiaomi MiMo Token Plan"),
    ("1906206500722614000", "Notebook LM重大更新解析"),
    ("1906203805628910168", "ClawHub平台13729个技能深度测评"),
    ("1906201674251247160", "Qvaris金融数据Skill"),
]

for nid, expected_title in note_ids:
    url = f"https://openapi.biji.com/open/api/v1/resource/note/detail?id={nid}"
    req = urllib.request.Request(url, headers={
        "Authorization": API_KEY,
        "X-Client-ID": CLIENT_ID
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
            note = data.get("data", {}).get("note", {}) or {}
            title = note.get("title", "NULL")
            ntype = note.get("note_type", "NULL")
            content = note.get("content", "")
            wp = note.get("web_page", {})
            wp_url = wp.get("url", "") if wp else ""
            created = note.get("created_at", "NULL")
            tags = [t.get("name") for t in note.get("tags", [])]
            print(f"ID:{nid}")
            print(f"Title:{title}")
            print(f"Type:{ntype}")
            print(f"ContentLen:{len(content)}")
            print(f"WPUrl:{wp_url}")
            print(f"Created:{created}")
            print(f"Tags:{','.join(tags)}")
            print("---")
    except Exception as e:
        print(f"ERROR {nid}: {e}")
        print("---")

#!/usr/bin/env python3
"""仅推送缓存到飞书，不涉及下载"""
import subprocess, time, os, json

CACHE_DIR = os.path.expanduser("~/douyin_cache/aweme_id")
BASE_TOKEN = "NeDBbyQvTa0xdysDCbRcQZ8cnMf"
TABLE_ID = "tbllE5S5vOhj5W9x"
TODAY_MS = int(time.time() * 1000)
BLOGGER_NAME = "创哥的AI实验室"

METADATA = {
    "7633431608988585256": ("10分钟成为尊贵的爱马仕Agent用户", 734, 145),
    "7620678756050455860": ("ClaudeCode太折腾？这个网页工具让AI编程简单10倍", 474, 16),
}

def write_feishu(aweme_id, title, content, link, duration, digg_count):
    payload = {
        "fields": ["文章标题", "原文内容", "原文链接", "时长", "点赞数", "来源种类", "博主名称", "发布日期"],
        "rows": [[title, content, link, duration, digg, "抖音", BLOGGER_NAME, TODAY_MS]]
    }
    json_file = f"./feishu_payload_{aweme_id}.json"
    with open(json_file, "w") as f:
        json.dump(payload, f, ensure_ascii=False)

    cmd = [
        "lark-cli", "base", "+record-batch-create",
        "--base-token", BASE_TOKEN,
        "--table-id", TABLE_ID,
        "--as", "user",
        "--json", f"@{json_file}"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    os.remove(json_file)
    try:
        resp = json.loads(r.stdout)
        ok = resp.get("ok", False)
        return ok, resp if ok else str(resp)
    except:
        return False, r.stdout[:200]

files = sorted([f for f in os.listdir(CACHE_DIR) if f.endswith(".txt")])
print(f"发现 {len(files)} 个缓存文件")

success = 0
for fn in files:
    aweme_id = fn[:-4]
    if aweme_id not in METADATA:
        print(f"  [{aweme_id}] 无元数据，跳过")
        continue

    title, duration, digg = METADATA[aweme_id]
    cache_path = f"{CACHE_DIR}/{fn}"

    with open(cache_path) as f:
        content = f.read().strip().replace('\n', ' ')

    print(f">>> [{aweme_id}] {title[:30]}... ({len(content)}字)")
    ok, resp = write_feishu(aweme_id, title, content, f"https://www.douyin.com/video/{aweme_id}", duration, digg)
    if ok:
        os.remove(cache_path)
        print(f"  成功，已删除缓存")
        success += 1
    else:
        print(f"  失败: {resp}")
    time.sleep(1)

print(f"\n=== 完成，成功 {success}/{len(files)} 条 ===")

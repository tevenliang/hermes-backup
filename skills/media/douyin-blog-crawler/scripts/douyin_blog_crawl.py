#!/usr/bin/env python3
"""
抖音博主视频爬取 - 断点续传脚本 v2
使用方式: python3 douyin_blog_crawl.py

关键设计：
1. 每次执行前检查飞书已有记录，过滤已存在 aweme_id
2. 获取视频列表后立即处理每个视频（不批量存 URL）
3. play_url 当场用完，过期立刻发现
4. Whisper 超时动态设置：>300s 视频给 900s，否则 600s
5. 顺序执行，不并行（Whisper CPU 密集型）
"""

import subprocess, json, time, os, sys

TMP = "/tmp/douyin_work"
TODAY_MS = int(time.time() * 1000)
os.makedirs(TMP, exist_ok=True)

BASE_TOKEN = "NeDBbyQvTa0xdysDCbRcQZ8cnMf"
TABLE_ID = "tbllE5S5vOhj5W9x"

# 博主列表: (sec_uid, 博主名)
BLOGGERS = [
    ("MS4wLjABAAAAcBGY4RqDTLberZGiFTk-nG_L0hVwrFC7Bii_20YdBgBDGu-9JoA2L6jtkpdnpBpr", "数字游牧人Samuel"),
    ("MS4wLjABAAAAzaye_V0qtP4d7m77UywUBRq7xB9CRiLaeGPfg79hLtQ", "宋鸿兵观天下"),
    ("MS4wLjABAAAAX1iRjBCVyMg-xzgVp1_sm758gj_zTJA9FJJojwcWw0fr-WLAv13_rIkv7jhwIF33", "可喜"),
    ("MS4wLjABAAAAFR2-YXEXvVAcCX8_MiMRl3qsacsdXJiSdWm6AvCCU0k", "创哥的AI实验室"),
]

# 已知已完成的 aweme_id（用于快速跳过，配合 get_existing_ids 使用）
EXTRA_SKIP = {}

H = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"

def run(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr, r.returncode

def get_existing_ids():
    """获取飞书表格中已有 aweme_id"""
    cmd = f'lark-cli base +record-list --base-token {BASE_TOKEN} --table-id {TABLE_ID} --as user 2>/dev/null'
    stdout, _, _ = run(cmd)
    try:
        data = json.loads(stdout)
        ids = set()
        for row in data.get("data", {}).get("data", []):
            url = row[10] if len(row) > 10 else None
            if url:
                ids.add(url.split("/")[-1])
        return ids
    except:
        return set()

def write_feishu(aweme_id, title, content, link, duration, digg_count, blogger_name):
    title_esc = title.replace('"', '\\"')
    content_esc = content.replace('"', '\\"')
    cmd = (
        f'lark-cli base +record-create '
        f'--base-token {BASE_TOKEN} --table-id {TABLE_ID} --as user '
        f'--json \'{{"fields": ["文章标题", "原文内容", "原文链接", "时长", "点赞数", "来源种类", "博主名称", "发布日期"], '
        f'"rows": [[" {title_esc} ", "{content_esc}", "{link}", {duration}, {digg_count}, "抖音", "{blogger_name}", {TODAY_MS}]]}}\' 2>/dev/null'
    )
    stdout, _, _ = run(cmd, timeout=30)
    return stdout

def process_video(v, blogger_name, existing_ids):
    aweme_id = v["aweme_id"]
    title = v["title"]
    duration = v["duration"]
    digg = v["digg_count"]
    play_url = v["play_url"]

    if aweme_id in existing_ids:
        return 0  # 已有，跳过

    mp4 = f"{TMP}/{aweme_id}.mp4"
    mp3 = f"{TMP}/{aweme_id}.mp3"
    txt = f"{TMP}/{aweme_id}.txt"

    print(f"\n  [NEW] {title[:50]}... (时长={duration}s, 点赞={digg})")

    # 下载（立即，不等待）
    _, _, rc = run(
        f'curl -L -o "{mp4}" "{play_url}" '
        f'-H "User-Agent: {H}" -H "Referer: https://www.douyin.com/" '
        f'-H "Accept-Language: zh-CN,zh;q=0.9" --max-time 120 -s',
        timeout=150
    )
    if rc != 0 or not os.path.exists(mp4) or os.path.getsize(mp4) == 0:
        print(f"    下载失败 (rc={rc})，跳过")
        return 0

    # 提取音频
    run(f'ffmpeg -i "{mp4}" -vn -acodec libmp3lame -q:a 2 "{mp3}" -y -loglevel error', timeout=60)

    # Whisper 转写（动态超时）
    wt = 900 if duration > 300 else 600
    run(f'whisper "{mp3}" --model small --language Chinese --output_dir "{TMP}" --output_format txt 2>/dev/null', timeout=wt)

    # 读取转写内容
    content = ""
    if os.path.exists(txt) and os.path.getsize(txt) > 0:
        with open(txt) as f:
            content = f.read().strip().replace('\n', ' ')

    # 写入飞书
    print(f"    写入飞书...")
    write_feishu(aweme_id, title, content, f"https://www.douyin.com/video/{aweme_id}", duration, digg, blogger_name)
    print(f"    完成: {aweme_id}")

    # 清理
    for f in [mp4, mp3, txt]:
        if os.path.exists(f): os.remove(f)

    return 1

def process_blogger(sec_uid, blogger_name, existing_ids):
    print(f"\n{'='*60}")
    print(f"处理博主: {blogger_name}")
    print(f"{'='*60}")

    stdout, _, rc = run(f'opencli douyin user-videos "{sec_uid}" --limit 10 --format json 2>/dev/null')
    if rc != 0 or not stdout.strip():
        print(f"  获取失败")
        return 0

    try:
        videos = json.loads(stdout)
    except:
        print(f"  JSON 解析失败")
        return 0

    print(f"  获取到 {len(videos)} 个视频")

    if len(videos) < 5:
        print(f"  警告：视频数异常(<5)，sec_uid 可能已失效")
        return 0

    count = 0
    for v in videos:
        count += process_video(v, blogger_name, existing_ids)
        # 更新 existing_ids（新增记录后及时同步）
        existing_ids = get_existing_ids()
        time.sleep(1)

    print(f"  {blogger_name} 完成，新增 {count} 条")
    return count

def main():
    existing_ids = get_existing_ids()
    print(f"已有 {len(existing_ids)} 条记录")

    total = 0
    for sec_uid, blogger_name in BLOGGERS:
        extra_skip = EXTRA_SKIP.get(sec_uid, [])
        ids_with_skip = existing_ids | set(extra_skip)
        total += process_blogger(sec_uid, blogger_name, ids_with_skip)

    print(f"\n=== 全部完成，共新增 {total} 条记录 ===")

if __name__ == "__main__":
    main()

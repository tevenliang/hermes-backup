#!/usr/bin/env python3
"""抖音博主断点续爬脚本 - 数字游牧人Samuel/宋鸿兵观天下/可喜/创哥的AI实验室"""

import subprocess
import json
import time
import os
import sys

TMP = "/tmp/douyin_resume"
TODAY_MS = int(time.time() * 1000)
BASE_TOKEN = "NeDBbyQvTa0xdysDCbRcQZ8cnMf"
TABLE_ID = "tbllE5S5vOhj5W9x"

BLOGGERS = [
    ("MS4wLjABAAAAcBGY4RqDTLberZGiFTk-nG_L0hVwrFC7Bii_20YdBgBDGu-9JoA2L6jtkpdnpBpr", "数字游牧人Samuel"),
    ("MS4wLjABAAAAzaye_V0qtP4d7m77UywUBRq7xB9CRiLaeGPfg79hLtQ", "宋鸿兵观天下"),
    ("MS4wLjABAAAAX1iRjBCVyMg-xzgVp1_sm758gj_zTJA9FJJojwcWw0fr-WLAv13_rIkv7jhwIF33", "可喜"),
    ("MS4wLjABAAAAFR2-YXEXvVAcCX8_MiMRl3qsacsdXJiSdWm6AvCCU0k", "创哥的AI实验室"),
]

os.makedirs(TMP, exist_ok=True)

def run(cmd, timeout=300):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout, result.stderr, result.returncode

def get_existing_ids():
    print("获取表格中已有aweme_id...")
    cmd = f'lark-cli base +record-list --base-token {BASE_TOKEN} --table-id {TABLE_ID} --as user 2>/dev/null'
    stdout, _, _ = run(cmd)
    try:
        data = json.loads(stdout)
        existing = []
        for row in data.get("data", {}).get("data", []):
            url = row[10] if len(row) > 10 else None
            if url:
                aid = url.split("/")[-1]
                existing.append(aid)
        print(f"  已有 {len(existing)} 条记录")
        return set(existing)
    except:
        print("  获取已有记录失败，继续处理所有视频")
        return set()

def process_blogger(sec_uid, blogger_name, existing_ids):
    print(f"\n{'='*60}")
    print(f"处理博主: {blogger_name}")
    print(f"{'='*60}")

    # 获取视频列表
    print("获取视频列表...")
    stdout, stderr, rc = run(f'opencli douyin user-videos "{sec_uid}" --limit 10 --format json 2>/dev/null')
    if rc != 0 or not stdout.strip():
        print(f"  获取失败，rc={rc}")
        return 0

    try:
        videos = json.loads(stdout)
    except:
        print("  JSON解析失败")
        return 0

    if len(videos) < 5:
        print(f"  警告：只获取到{len(videos)}个视频，sec_uid可能已失效，跳过")
        return 0

    print(f"  获取到 {len(videos)} 个视频")

    new_count = 0
    for v in videos:
        aweme_id = v["aweme_id"]
        title = v["title"]
        duration = v["duration"]
        digg_count = v["digg_count"]
        play_url = v["play_url"]

        if aweme_id in existing_ids:
            print(f"  [SKIP] {aweme_id} 已存在")
            continue

        print(f"\n  [NEW] {title[:40]}... (时长={duration}s, 点赞={digg_count})")
        mp4 = f"{TMP}/{aweme_id}.mp4"
        mp3 = f"{TMP}/{aweme_id}.mp3"
        txt = f"{TMP}/{aweme_id}.txt"

        # 下载
        print(f"    下载中...")
        h = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        _, _, rc = run(
            f'curl -L -o "{mp4}" "{play_url}" '
            f'-H "User-Agent: {h}" -H "Referer: https://www.douyin.com/" '
            f'-H "Accept-Language: zh-CN,zh;q=0.9" --max-time 120 -s',
            timeout=150
        )
        if rc != 0 or not os.path.exists(mp4) or os.path.getsize(mp4) == 0:
            print(f"    下载失败，跳过")
            continue

        # 提取音频
        print(f"    提取音频...")
        run(f'ffmpeg -i "{mp4}" -vn -acodec libmp3lame -q:a 2 "{mp3}" -y -loglevel error', timeout=60)

        # Whisper转写
        print(f"    转写中...")
        run(f'whisper "{mp3}" --model small --language Chinese --output_dir "{TMP}" --output_format txt 2>/dev/null', timeout=600)

        # 读取转写内容
        content = ""
        if os.path.exists(txt) and os.path.getsize(txt) > 0:
            with open(txt, "r") as f:
                content = f.read().strip().replace('"', '\\"').replace('\n', ' ')

        # 写入飞书
        print(f"    写入飞书...")
        title_esc = title.replace('"', '\\"')
        lark_cmd = (
            f'lark-cli base +record-create '
            f'--base-token {BASE_TOKEN} --table-id {TABLE_ID} --as user '
            f'--json \'{{"fields": ["文章标题", "原文内容", "原文链接", "时长", "点赞数", "来源种类", "博主名称", "发布日期"], '
            f'"rows": [[" {title_esc} ", "{content}", "https://www.douyin.com/video/{aweme_id}", {duration}, {digg_count}, "抖音", "{blogger_name}", {TODAY_MS}]]}}\' 2>/dev/null'
        )
        stdout2, _, _ = run(lark_cmd, timeout=30)
        print(f"    完成: {aweme_id}")

        # 清理临时文件
        for f in [mp4, mp3, txt]:
            if os.path.exists(f):
                os.remove(f)

        new_count += 1
        time.sleep(1)

    print(f"  {blogger_name} 完成，新增 {new_count} 条记录")
    return new_count

def main():
    existing_ids = get_existing_ids()
    total = 0
    for sec_uid, blogger_name in BLOGGERS:
        total += process_blogger(sec_uid, blogger_name, existing_ids)
        # 更新已见到的ID，避免重复处理
        for sec_uid2, blogger_name2 in BLOGGERS:
            if blogger_name2 == blogger_name:
                break

    print(f"\n全部完成，共新增 {total} 条记录")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
创哥的AI实验室 - v5 断点续传版
- 转写结果先落盘 ~/douyin_cache/aweme_id.txt
- 推送飞书成功才删缓存，失败保留，下次自动重试
- 每次运行自动扫描缓存目录，续传中断的任务
"""
import subprocess, json, time, os, sys

CACHE_DIR = os.path.expanduser("~/douyin_cache/aweme_id")
TMP = "/tmp/douyin_resume3"
TODAY_MS = int(time.time() * 1000)

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

BLOGGER_NAME = "创哥的AI实验室"
BASE_TOKEN = "NeDBbyQvTa0xdysDCbRcQZ8cnMf"
TABLE_ID = "tbllE5S5vOhj5W9x"

VIDEOS = [
    {"aweme_id": "7633431608988585256", "title": "10分钟成为尊贵的爱马仕Agent用户", "duration": 734, "digg_count": 145, "play_url": "https://v11-weba.douyinvod.com/b425f7c0d03014bc7a99c0616561fd60/69fc478c/video/tos/cn/tos-cn-ve-15/oEIDp7hkhhM2AByxO3CAfbBAEHCJgOQQUgfF9D/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=446&bt=446&cs=0&ds=4&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=Z2c0aGk0OjxkN2VnODk2OkBpajo1ZGw5cjZwOjMzNGkzM0BgNS9hNC82NjYxXmIuXi81YSNgb2ZgMmQ0LmthLS1kLS9zcw%3D%3D&btag=c0000e00038000&cquery=101r_100B_100H_100K_100o&dy_q=1778129534&feature_id=37f92ebd2877ae8e7eba995d406c5150&l=20260507125214DAB7D280B0696A45F8C2"},
    {"aweme_id": "7620738760430439715", "title": "3领域10场景，我把整个生活外包给了龙虾", "duration": 400, "digg_count": 752, "play_url": "https://v11-weba.douyinvod.com/e766317113ca9d905ec7cbea50c025cc/69fc463e/video/tos/cn/tos-cn-ve-15/oEKRAQ9C7megTA08RZwheJLf3oVMBCWdG1lBDW/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=708&bt=708&cs=0&ds=4&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=NjU5MzM7NDY1Njk1ZGhoO0BpM2R4ZXE5cm03OjMzNGkzM0AuYl5eLmMtXjAxMDU2LWEuYSMzX2trMmRrbS5hLS1kLTBzcw%3D%3D&btag=c0000e00030000&cquery=101r_100B_100H_100K_100o&dy_q=1778129534&feature_id=37f92ebd2877ae8e7eba995d406c5150&l=20260507125214DAB7D280B0696A45F8C2"},
    {"aweme_id": "7620678756050455860", "title": "ClaudeCode太折腾？这个网页工具让AI编程简单10倍", "duration": 474, "digg_count": 16, "play_url": "https://v11-weba.douyinvod.com/b48d5e593ab625431d8c82aea8430685/69fc4688/video/tos/cn/tos-cn-ve-15/f743adc82f6f499ebd283d2344490c15/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=548&bt=548&cs=0&ds=3&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=N2k5ZzY1NDk0OjU3OzQzZEBpMzpkbnE5cnk0OjMzNGkzM0A0Mi1jYDFhNTUxLTUwMmMvYSNiMTNsMmRzNC5hLS1kLS9zcw%3D%3D&btag=c0000e00030000&cquery=100o_101r_100B_100H_100K&dy_q=1778129534&feature_id=f5241e7604dff1d9d6c943fd20bd51a2&l=20260507125214DAB7D280B0696A45F8C2"},
    {"aweme_id": "7618200675683552518", "title": "WPS原生桌面级办公套件，iPad生产力拉满！", "duration": 172, "digg_count": 97, "play_url": "https://v11-weba.douyinvod.com/cb0d07fa07d95cb105291e4f9c1136d0/69fc455a/video/tos/cn/tos-cn-ve-15/ocI5feHIIE2PQEpILELmASGGAO09NCjYeS5Del/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=624&bt=624&cs=0&ds=3&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=ZThkZDNoPGQ0aWQ5NzRnNUBpMzt5anM5cnluOTMzNGkzM0A1Li9hYjQ0Nl8xYjUwYy42YSM0cGRjMmRzZHBhLS1kLWFzcw%3D%3D&btag=c0000e00028000&cquery=101r_100B_100H_100K_100o&dy_q=1778129534&feature_id=f5241e7604dff1d9d6c943fd20bd51a2&l=20260507125214DAB7D280B0696A45F8C2"},
    {"aweme_id": "7615994303940250880", "title": "哪个大冤种还在付费装龙虾？", "duration": 219, "digg_count": 539, "play_url": "https://v11-weba.douyinvod.com/236ededeef7857c30bedc8038cd6b55c/69fc4589/video/tos/cn/tos-cn-ve-15/oAGIDEcigAGsAqyb9iftXpBBsNsjFiAEytDfQx/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=512&bt=512&cs=0&ds=3&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=ZDY6NTc3PDczZWg4aGg1NUBpanVmZWw5cmlxOTMzNGkzM0AvM2JeNmA2NmExYDFfLmIyYSMvNTVpMmRzMGxhLS1kLTBzcw%3D%3D&btag=c0000e00028000&cquery=100o_101r_100B_100H_100K&dy_q=1778129534&feature_id=f5241e7604dff1d9d6c943fd20bd51a2&l=20260507125214DAB7D280B0696A45F8C2"},
    {"aweme_id": "7614104043064921378", "title": "15分钟用OpenClaw搭建一个开挂的人生系统", "duration": 873, "digg_count": 82, "play_url": "https://v11-weba.douyinvod.com/3f937b2b5136f4eaac3b13c2152ce26b/69fc4816/video/tos/cn/tos-cn-ve-15/oUwFfBC9II7a2QseKfwbqEXYTb7vADZiVQEAAB/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=421&bt=421&cs=0&ds=3&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=OTg2ZTo3ZTtkZWY3Zzk8PEBpanJrcnI5cjplOTMzNGkzM0A0Y2I0YWIxXjMxXzExM2I2YSNjcS4zMmRraGlhLS1kLWFzcw%3D%3D&btag=c0000e00038000&cquery=100o_101r_100B_100H_100K&dy_q=1778129534&feature_id=fea919893f650a8c49286568590446ef&l=20260507125214DAB7D280B0696A45F8C2"},
    {"aweme_id": "7609650995936660736", "title": "一个视频将ClaudeCode常用操作一网打尽", "duration": 600, "digg_count": 44, "play_url": "https://v11-weba.douyinvod.com/439b522da20763b6dd1a46bcc77a006b/69fc4706/video/tos/cn/tos-cn-ve-15/fa8678df0ffc49c59eda3a2a3ad45087/?a=6383&ch=10010&cr=3&dr=0&lr=all&cd=0%7C0%7C0%7C3&cv=1&br=382&bt=382&cs=0&ds=3&ft=GZnU0RqeffPdXP~ka1zNvAq-antLjrKo3w8nRkaN.t0fljVhWL6&mime_type=video_mp4&qs=0&rc=Nzg2NDwzZDloM2c5aThkOEBpank3NXE5cmhoOTMzNGkzM0A1YzFeNTAyXjYxX2FjYzMzYSMuZ2ouMmRrZGFhLS1kLWFzcw%3D%3D&btag=c0000e00038000&cquery=100H_100K_100o_101r_100B&dy_q=1778129534&feature_id=fea919893f650a8c49286568590446ef&l=20260507125214DAB7D280B0696A45F8C2"},
]

H = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"

def run(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1

def write_feishu(aweme_id, title, content, link, duration, digg_count):
    title_esc = title.replace('"', '\\"')
    content_esc = content.replace('"', '\\"')
    cmd = (
        f'lark-cli base +record-batch-create '
        f'--base-token {BASE_TOKEN} --table-id {TABLE_ID} --as user '
        f'--json \'{{"fields": ["文章标题", "原文内容", "原文链接", "时长", "点赞数", "来源种类", "博主名称", "发布日期"], '
        f'"rows": [[" {title_esc} ", "{content_esc}", "{link}", {duration}, {digg_count}, "抖音", "{BLOGGER_NAME}", {TODAY_MS}]]}}\' 2>/dev/null'
    )
    stdout, _, rc = run(cmd, timeout=30)
    return rc == 0, stdout

def get_play_url(aweme_id):
    """通过抖音 API 获取视频直链"""
    stdout, _, rc = run(
        f'curl -s "https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={aweme_id}" '
        f'-H "User-Agent: {H}" -H "Referer: https://www.douyin.com/" --max-time 15',
        timeout=20
    )
    if rc != 0:
        return None
    try:
        data = json.loads(stdout)
        aweme_detail = data.get("aweme_detail", {}) or {}
        video = aweme_detail.get("video", {}) or {}
        play_addr = video.get("play_addr", {}) or {}
        urls = play_addr.get("url_list", []) or []
        return urls[0] if urls else None
    except:
        return None

def already_done(aweme_id):
    """检查缓存目录，确认转写已完成"""
    return os.path.exists(f"{CACHE_DIR}/{aweme_id}.txt")

def process_video(v):
    aweme_id = v["aweme_id"]
    title = v["title"]
    duration = v["duration"]
    digg = v["digg_count"]

    cache_txt = f"{CACHE_DIR}/{aweme_id}.txt"
    tmp_mp4 = f"{TMP}/{aweme_id}.mp4"
    tmp_mp3 = f"{TMP}/{aweme_id}.mp3"
    tmp_txt = f"{TMP}/{aweme_id}.txt"

    print(f"\n>>> [{v['index']}/{v['total']}] {title[:40]}...")

    # 步骤1：下载 + 转写（仅在无缓存时）
    if not os.path.exists(cache_txt):
        play_url = v.get("play_url")
        if not play_url:
            print(f"  无直链，跳过")
            return False

        print(f"  下载中...")
        _, _, rc = run(
            f'curl -L -o "{tmp_mp4}" "{play_url}" '
            f'-H "User-Agent: {H}" -H "Referer: https://www.douyin.com/" '
            f'-H "Accept-Language: zh-CN,zh;q=0.9" --max-time 120 -s',
            timeout=150
        )
        if rc != 0 or not os.path.exists(tmp_mp4) or os.path.getsize(tmp_mp4) == 0:
            print(f"  下载失败(rc={rc})，跳过")
            return False

        print(f"  提取音频...")
        run(f'ffmpeg -i "{tmp_mp4}" -vn -acodec libmp3lame -q:a 2 "{tmp_mp3}" -y -loglevel error', timeout=60)

        whisper_t = max(300, min(1200, duration * 2))
        print(f"  转写中 (model=base, timeout={whisper_t}s)...")
        run(f'whisper "{tmp_mp3}" --model base --language Chinese --output_dir "{TMP}" --output_format txt 2>/dev/null', timeout=whisper_t)

        # 转写结果写入缓存
        if os.path.exists(tmp_txt) and os.path.getsize(tmp_txt) > 0:
            with open(tmp_txt) as f:
                content = f.read().strip()
            with open(cache_txt, "w") as f:
                f.write(content)
            print(f"  已缓存 ({len(content)}字)")
        else:
            print(f"  转写失败（文件为空），跳过")
            for f in [tmp_mp4, tmp_mp3]:
                if os.path.exists(f): os.remove(f)
            return False

        # 清理临时文件
        for f in [tmp_mp4, tmp_mp3, tmp_txt]:
            if os.path.exists(f): os.remove(f)
    else:
        print(f"  [缓存] 转写已存在，跳过下载&转写")

    # 步骤2：从缓存推送飞书（每次运行都尝试，直到成功）
    with open(cache_txt) as f:
        content = f.read().strip().replace('\n', ' ')

    print(f"  推送飞书...")
    ok, resp = write_feishu(aweme_id, title, content, f"https://www.douyin.com/video/{aweme_id}", duration, digg)
    if ok:
        print(f"  成功，删除缓存")
        os.remove(cache_txt)
        return True
    else:
        print(f"  失败(resp={resp[:100]})，保留缓存下次重试")
        return False

def main():
    print(f"=== 创哥的AI实验室 v5 断点续传 ===")
    print(f"缓存目录: {CACHE_DIR}")

    # 扫描缓存中待重试的任务
    pending = []
    cached_ids = set()
    for fn in os.listdir(CACHE_DIR):
        if fn.endswith(".txt"):
            aweme_id = fn[:-4]
            cached_ids.add(aweme_id)
            v = next((x for x in VIDEOS if x["aweme_id"] == aweme_id), None)
            if v:
                pending.append(v)

    # 收集所有待处理（缓存优先）
    to_process = []
    for v in VIDEOS:
        v["index"] = 0  # 待填充
        v["total"] = len(VIDEOS)
        if v["aweme_id"] not in cached_ids:
            to_process.append(v)

    all_tasks = pending + to_process
    for i, v in enumerate(all_tasks, 1):
        v["index"] = i

    total = len(all_tasks)
    done_count = len(pending)
    success_count = 0

    for v in all_tasks:
        ok = process_video(v)
        if ok:
            success_count += 1
        time.sleep(1)

    print(f"\n=== 完成 (本次成功: {success_count}, 缓存待重试: {len(pending)}) ===")

if __name__ == "__main__":
    main()

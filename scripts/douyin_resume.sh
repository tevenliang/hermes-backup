#!/bin/bash
# 抖音博主断点续爬脚本
# 用法: bash douyin_resume.sh

TMP="/tmp/douyin_resume"
TODAY_TS=$(date +%Y-%m-%d)
TODAY_MS=$(($(date +%s) * 1000))
mkdir -p "$TMP"

# 博主列表 (sec_uid | 博主名)
BLOGGERS=(
  "MS4wLjABAAAAcBGY4RqDTLberZGiFTk-nG_L0hVwrFC7Bii_20YdBgBDGu-9JoA2L6jtkpdnpBpr|数字游牧人Samuel"
  "MS4wLjABAAAAzaye_V0qtP4d7m77UywUBRq7xB9CRiLaeGPfg79hLtQ|宋鸿兵观天下"
  "MS4wLjABAAAAX1iRjBCVyMg-xzgVp1_sm758gj_zTJA9FJJojwcWw0fr-WLAv13_rIkv7jhwIF33|可喜"
  "MS4wLjABAAAAFR2-YXEXvVAcCX8_MiMRl3qsacsdXJiSdWm6AvCCU0k|创哥的AI实验室"
)

# 飞书配置
BASE_TOKEN="NeDBbyQvTa0xdysDCbRcQZ8cnMf"
TABLE_ID="tbllE5S5vOhj5W9x"

echo "=== 步骤1: 获取表格中已有的 aweme_id 列表 ==="
EXISTING_IDS=$(lark-cli base +record-list \
  --base-token "$BASE_TOKEN" \
  --table-id "$TABLE_ID" \
  --as user 2>/dev/null | jq -r '.data.data[] | .[10] // empty' | \
  while read url; do
    echo "$url" | sed 's|https://www.douyin.com/video/||' | tr -d '\n' | echo
    echo
  done | sort -u)
echo "已有记录数: $(echo "$EXISTING_IDS" | grep -c .)"

echo ""
echo "=== 开始遍历博主 ==="

for entry in "${BLOGGERS[@]}"; do
  IFS='|' read -r SEC_UID BLOGGER_NAME <<< "$entry"
  echo ""
  echo "=========================================="
  echo "开始处理博主: $BLOGGER_NAME (sec_uid: $SEC_UID)"
  echo "=========================================="

  # 获取视频列表
  echo "获取视频列表..."
  opencli douyin user-videos "$SEC_UID" --limit 10 --format json > "$TMP/videos_${BLOGGER_NAME}.json" 2>/dev/null

  VIDEO_COUNT=$(jq 'length' "$TMP/videos_${BLOGGER_NAME}.json" 2>/dev/null)
  echo "获取到 ${VIDEO_COUNT} 个视频"

  if [ "$VIDEO_COUNT" -lt 5 ]; then
    echo "警告：视频数异常，sec_uid 可能已失效，跳过"
    continue
  fi

  # 遍历每个视频
  jq -r '.[] | @json' "$TMP/videos_${BLOGGER_NAME}.json" | while read -r video_json; do
    AWEME_ID=$(echo "$video_json" | jq -r '.aweme_id')
    TITLE=$(echo "$video_json" | jq -r '.title')
    DURATION=$(echo "$video_json" | jq -r '.duration')
    DIGG_COUNT=$(echo "$video_json" | jq -r '.digg_count')
    PLAY_URL=$(echo "$video_json" | jq -r '.play_url')

    # 检查是否已存在
    if echo "$EXISTING_IDS" | grep -q "^${AWEME_ID}$"; then
      echo "[SKIP] $AWEME_ID 已存在，跳过"
      return
    fi

    MP4="$TMP/${AWEME_ID}.mp4"
    MP3="$TMP/${AWEME_ID}.mp3"
    TXT="$TMP/${AWEME_ID}.txt"

    echo "[NEW] 开始处理: $TITLE (时长=${DURATION}s, 点赞=${DIGG_COUNT})"

    # 下载
    echo "  下载中..."
    curl -L -o "$MP4" "$PLAY_URL" \
      -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36" \
      -H "Referer: https://www.douyin.com/" \
      -H "Accept-Language: zh-CN,zh;q=0.9" \
      --max-time 120 -s

    if [ ! -s "$MP4" ]; then
      echo "  下载失败，跳过"
      return
    fi

    # 提取音频
    echo "  提取音频..."
    ffmpeg -i "$MP4" -vn -acodec libmp3lame -q:a 2 "$MP3" -y -loglevel error

    # Whisper 转写
    echo "  转写中..."
    whisper "$MP3" --model small --language Chinese --output_dir "$TMP" --output_format txt 2>/dev/null

    # 读取转写文本
    if [ -f "$TXT" ] && [ -s "$TXT" ]; then
      CONTENT=$(cat "$TXT" | sed 's/"/\\"/g' | tr '\n' ' ')
    else
      CONTENT=""
    fi

    # 写入飞书
    echo "  写入飞书..."
    lark-cli base +record-create \
      --base-token "$BASE_TOKEN" \
      --table-id "$TABLE_ID" \
      --as user \
      --json "{\"fields\": [\"文章标题\", \"原文内容\", \"原文链接\", \"时长\", \"点赞数\", \"来源种类\", \"博主名称\", \"发布日期\"], \"rows\": [[\"$(echo "$TITLE" | sed 's/"/\\"/g')\", \"$CONTENT\", \"https://www.douyin.com/video/${AWEME_ID}\", ${DURATION}, ${DIGG_COUNT}, \"抖音\", \"${BLOGGER_NAME}\", ${TODAY_MS}]]}" 2>/dev/null

    echo "  完成: $AWEME_ID"

    # 清理临时文件
    rm -f "$MP4" "$MP3" "$TXT"
  done

  echo "博主 $BLOGGER_NAME 完成"
done

echo ""
echo "=== 全部完成 ==="
echo "临时文件位置: $TMP"

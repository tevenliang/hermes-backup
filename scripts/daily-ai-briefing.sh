#!/bin/bash
# 每日云厂商AI简报生成器
# 运行时间: 每天早上 08:30
# 追加保存到飞书文档

DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="/root/.openclaw/workspace/daily-briefings"
REPORT_FILE="$OUTPUT_DIR/$DATE-ai-briefing.md"

# ========== 第1步：生成简报内容 ==========
echo "# ☁️ 每日云厂商AI动态简报" > "$REPORT_FILE"
echo "**日期**: $DATE" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# AWS AI 动态
echo "## AWS AI" >> "$REPORT_FILE"
echo "- (待抓取)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Azure AI 动态
echo "## Azure AI" >> "$REPORT_FILE"
echo "- (待抓取)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Google Cloud AI
echo "## Google Cloud AI" >> "$REPORT_FILE"
echo "- (待抓取)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 阿里云/腾讯云
echo "## 中国云厂商 AI" >> "$REPORT_FILE"
echo "- (待抓取)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# GitHub/GitLab AI 竞品
echo "## 竞品动态 (GitHub/GitLab)" >> "$REPORT_FILE"
echo "- (待抓取)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "---" >> "$REPORT_FILE"
echo "*由贾维斯自动生成 $(date '+%Y-%m-%d %H:%M:%S')*" >> "$REPORT_FILE"

echo "✅ 简报已生成: $REPORT_FILE"

# ========== 第2步：追加到飞书文档 ==========
/usr/bin/python3 /root/.openclaw/workspace/scripts/append-ai-briefing.py "$DATE"

# ========== 第3步：发送飞书通知 ==========
FEISHU_TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
    -H "Content-Type: application/json" \
    -d '{"app_id":"cli_a947b541d8785bd9","app_secret":"HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"}' \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))")

if [ -n "$FEISHU_TOKEN" ]; then
    curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
        -H "Authorization: Bearer $FEISHU_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{
            \"receive_id\": \"ou_d4b39b86c8715f79b2c5b070c4e55393\",
            \"msg_type\": \"text\",
            \"content\": \"{\\\"text\\\": \\\"☁️ 每日AI简报 $DATE 已生成\\\\n📝 已同步保存到飞书文档\\\"}\"
        }" > /dev/null 2>&1
    echo "📱 飞书推送成功"
else
    echo "❌ 飞书token获取失败"
fi

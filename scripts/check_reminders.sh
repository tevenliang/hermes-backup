#!/bin/bash
# 检查提醒错误日志，如有错误则发飞书告警
ERROR_LOG="/tmp/reminder_errors.log"
ALERT_MARKER="/tmp/reminder_alerted_marker"  # 已告警过的日期标记

if [ ! -f "$ERROR_LOG" ] || [ ! -s "$ERROR_LOG" ]; then
    exit 0
fi

TODAY=$(date +%Y-%m-%d)
# 检查今天是否有新错误
if grep -q "^\\[$(date +%Y-%m-%d)" "$ERROR_LOG" 2>/dev/null; then
    LAST_ALERT=$(cat "$ALERT_MARKER" 2>/dev/null || echo "")
    if [ "$LAST_ALERT" != "$TODAY" ]; then
        # 有新错误，发飞书告警
        MSG="🤖 贾维斯自动检测：提醒推送出现错误，请检查！"
        TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
            -H "Content-Type: application/json" \
            -d '{"app_id":"cli_a947b541d8785bd9","app_secret":"HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"}' \
            | python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))")
        if [ -n "$TOKEN" ]; then
            curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d '{"receive_id": "ou_d4b39b86c8715f79b2c5b070c4e55393", "msg_type": "text", "content": "{\"text\": \"'"$MSG"\\n\\n错误日志：\\n$(tail -5 $ERROR_LOG)"'\"}"}' \
                > /dev/null 2>&1
            echo "$TODAY" > "$ALERT_MARKER"
        fi
    fi
fi

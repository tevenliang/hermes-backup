#!/bin/bash
# Minimax Coding Plan 用量查询（官方文档正确端点）
# 端点: www.minimaxi.com/v1/token_plan/remains
# 字段: week_usage_count / week_total_count

source /Users/twliang/.hermes/.env
API_KEY="${MINIMAX_CODING_API_KEY}"

if [ -z "$API_KEY" ]; then
    echo "⚠️ 未配置 MINIMAX_CODING_API_KEY"
    exit 1
fi

RESPONSE=$(curl -s --max-time 10 -X GET "https://www.minimaxi.com/v1/token_plan/remains" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json")

echo "$RESPONSE" | python3 -c "
import sys, json

raw = sys.stdin.read()
if not raw.strip():
    print('⚠️ API返回空响应')
    sys.exit(1)

data = json.loads(raw)

# Check error
if data.get('base_resp', {}).get('status_code') != 0:
    msg = data.get('base_resp', {}).get('status_msg', '未知')
    print(f'⚠️ API返回错误: {msg}')
    sys.exit(1)

for m in data.get('model_remains', []):
    model = m.get('model_name', '')

    # 5h window
    total_5h = m.get('current_interval_total_count', 0)
    used_5h = m.get('current_interval_usage_count', 0)
    remain_5h = total_5h - used_5h
    pct_5h = used_5h * 100 // total_5h if total_5h > 0 else 0

    # Week — 官方字段: current_weekly_total_count / current_weekly_usage_count
    week_total = m.get('current_weekly_total_count', 0)
    week_used = m.get('current_weekly_usage_count', 0)
    week_remain = week_total - week_used
    week_pct = week_used * 100 // week_total if week_total > 0 else 0

    print(f'📊 当前5h窗口: {used_5h} / {total_5h} prompts ({pct_5h}%)')
    print(f'🔄 剩余: {remain_5h} prompts')
    print(f'📅 本周配额: {week_used} / {week_total} ({week_pct}%)')
    print(f'📅 本周剩余: {week_remain} prompts')

    if pct_5h >= 90:
        print(f'状态: 🔴 紧急 — 当前周期用量{pct_5h}%，即将耗尽！')
    elif pct_5h >= 80:
        print(f'状态: 🔴 紧张 — 当前周期超过80%')
    elif pct_5h >= 50:
        print(f'状态: 🟡 正常 — 当前周期超过50%')
    else:
        print(f'状态: 💚 充足 — 当前周期低于50%')
    break
" 2>/dev/null || echo "⚠️ 解析失败，请检查API响应"

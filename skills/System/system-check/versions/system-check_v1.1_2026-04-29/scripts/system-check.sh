#!/bin/bash
# 系统检测脚本 — 整合 OpenClaw 状态 + Minimax用量 + 硬件健康检查

DISK_THRESHOLD=80
CPU_LOAD_THRESHOLD=3.0
MEMORY_THRESHOLD=90

echo "=========================================="
echo "🔍 系统检测"
echo "=========================================="
echo ""

# ── 模块一：OpenClaw 状态 ──
# 注：OpenClaw 状态由 AI 助手直接调用 session_status 工具读取，不在此脚本中执行
# 此脚本仅输出硬件健康状态

echo "📦 OpenClaw 运行状态"
echo "-------------------------------------------"
echo "  （由 AI 助手直接读取，见上方 session_status 输出）"
echo ""

# ── 模块二：硬件健康检查 ──
echo "🖥️ 硬件健康状态"
echo "-------------------------------------------"

# Disk
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
echo "  💾 磁盘: ${DISK_USAGE}% / 468G"
if (( DISK_USAGE > DISK_THRESHOLD )); then
    echo "     ❌ 告警 — 超过 ${DISK_THRESHOLD}%"
else
    echo "     ✅ 正常"
fi

# CPU Load
CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | awk '{printf "%.2f\n", $1}')
echo "  ⚙️ CPU负载(1m): ${CPU_LOAD}"
if (( $(echo "${CPU_LOAD} > ${CPU_LOAD_THRESHOLD}" | bc -l) )); then
    echo "     ❌ 告警 — 超过 ${CPU_LOAD_THRESHOLD}"
else
    echo "     ✅ 正常"
fi

# Memory
MEM_USED_PERCENT=$(free -h | awk '/^Mem:/ {printf "%.0f\n", $3/$2 * 100}')
echo "  🧠 内存: ${MEM_USED_PERCENT}%"
if (( MEM_USED_PERCENT > MEMORY_THRESHOLD )); then
    echo "     ❌ 告警 — 超过 ${MEMORY_THRESHOLD}%"
else
    echo "     ✅ 正常"
fi

echo ""
echo "=========================================="
echo "✅ 检测完成 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

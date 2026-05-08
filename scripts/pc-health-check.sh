#!/bin/bash
# PC 健康检查：CPU + 内存阈值告警
# macOS 内存计算参考：https://www.macworld.com/article/222277/how-to-check-memory-use-on-your-mac.html
#
# 内存计算方式（与 Activity Monitor 一致）：
#   已用 = active + wired + compressed
#   空闲 = free + purgeable + inactive（后三者均为可复用缓存）
#   占用率 = 已用 / (已用 + 空闲)

CPU_THRESHOLD=80
MEM_THRESHOLD=85

NOW=$(date "+%Y-%m-%d %H:%M")

# ---- CPU ----
# macOS top: "CPU usage: X% user, Y% sys, Z% idle"
CPU_LINE=$(top -l 1 | grep "CPU usage")
CPU_USER=$(echo "$CPU_LINE" | sed -E 's/.*([0-9]+\.[0-9]+)% user.*/\1/')
CPU_SYS=$(echo "$CPU_LINE" | sed -E 's/.*([0-9]+\.[0-9]+)% sys.*/\1/')
if [ -z "$CPU_USER" ] || [ "$CPU_USER" = "$CPU_LINE" ]; then
    CPU_USER=$(echo "$CPU_LINE" | awk '{print $3}' | sed 's/%//')
    CPU_SYS="0"
fi
CPU_USED=$(echo "scale=1; ${CPU_USER:-0} + ${CPU_SYS:-0}" | bc)
CPU_INT=$(printf "%.0f" "$CPU_USED" 2>/dev/null || echo "0")

# ---- 内存 ----
# vm_stat 中 inactive/purgeable/speculative 均为可复用缓存，不算占用
# 真正占用 = active + wired + compressed
FREE=$(vm_stat | grep "Pages free" | awk '{gsub(/[^0-9]/,""); print}')
PURGE=$(vm_stat | grep "Pages purgeable" | awk '{gsub(/[^0-9]/,""); print}')
INACT=$(vm_stat | grep "Pages inactive" | awk '{gsub(/[^0-9]/,""); print}')
SPEC=$(vm_stat | grep "Pages speculative" | awk '{gsub(/[^0-9]/,""); print}')
ACTIVE=$(vm_stat | grep "Pages active" | awk '{gsub(/[^0-9]/,""); print}')
WIRED=$(vm_stat | grep "Pages wired down" | awk '{gsub(/[^0-9]/,""); print}')
COMPR=$(vm_stat | grep "Pages compressed" | awk '{gsub(/[^0-9]/,""); print}')

# 空页 = free + purgeable + inactive + speculative（均为可复用）
FREE_PAGES=$((FREE + PURGE + INACT + SPEC))
# 已用页 = active + wired + compressed
USED_PAGES=$((ACTIVE + WIRED + COMPR))
TOTAL_PAGES=$((FREE_PAGES + USED_PAGES))

if [ "$TOTAL_PAGES" -gt 0 ]; then
    MEM_USAGE=$(echo "scale=1; $USED_PAGES * 100 / $TOTAL_PAGES" | bc)
else
    MEM_USAGE="0"
fi
MEM_INT=$(printf "%.0f" "$MEM_USAGE" 2>/dev/null || echo "0")

# ---- 告警判断 ----
ALERTS=""
[ "${CPU_INT:-0}" -ge "$CPU_THRESHOLD" ] && ALERTS="CPU: ${CPU_USED}% (阈值${CPU_THRESHOLD}%)"
[ "${MEM_INT:-0}" -ge "$MEM_THRESHOLD" ] && ALERTS="${ALERTS} ${ALERTS:+, }内存: ${MEM_USAGE}% (阈值${MEM_THRESHOLD}%)"

if [ -n "$ALERTS" ]; then
    echo "[$NOW] 高占用告警: $ALERTS"
    exit 1
else
    echo "[$NOW] ✓ CPU: ${CPU_USED}% | 内存: ${MEM_USAGE}% | 无异常"
    exit 0
fi

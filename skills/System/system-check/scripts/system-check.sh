#!/bin/bash
# 系统检测脚本 — 整合 Minimax 用量 + 硬件健康检查（macOS/Linux 通用）
# 使用方式：
#   bash ~/.hermes/skills/system/system-check/scripts/system-check.sh
#
# 注意：OpenClaw 状态由 AI 助手直接读取，本脚本仅负责硬件 + Minimax 用量

DISK_THRESHOLD=80
CPU_LOAD_THRESHOLD=3.0
MEMORY_THRESHOLD=85   # macOS Activity Monitor 口径（active+wired+compressed）

DETECT_OS() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)  echo "linux" ;;
    *)      echo "unknown" ;;
  esac
}

echo "=========================================="
echo "  系统检测 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# ── 模块一：Hermes 运行状态 ────────────────────────────────
echo "📦 Hermes 运行状态"
echo "------------------------------------------"
HERMES_STATUS=$(hermes status 2>&1)
MODEL=$(echo "$HERMES_STATUS" | grep "Model:" | awk '{print $2}')
PROVIDER=$(echo "$HERMES_STATUS" | grep "Provider:" | awk '{{$1=""; print $0}}' | sed 's/^ //')
GATEWAY=$(echo "$HERMES_STATUS" | grep "Status:" | head -1 | awk '{print $2}')
ACTIVE_JOBS=$(echo "$HERMES_STATUS" | grep "Jobs:" | awk '{print $2}')
ACTIVE_SESSIONS=$(echo "$HERMES_STATUS" | grep "Active:" | awk '{print $2}')
echo "  🤖 模型: ${MODEL} /${PROVIDER}"
echo "  🚀 Gateway: ${GATEWAY}"
echo "  📅 活跃Job: ${ACTIVE_JOBS}"
echo "  💬 活跃Session: ${ACTIVE_SESSIONS}"

# Token 使用量（历史累计）
HERMES_INSIGHTS=$(hermes insights 2>&1)
TOKEN_LINE=$(echo "$HERMES_INSIGHTS" | grep "^  Input tokens:")
INPUT_TOKENS=$(echo "$TOKEN_LINE" | sed 's/.*Input tokens: *\([0-9,]*\) *Output tokens: *\([0-9,]*\).*/\1/')
OUTPUT_TOKENS=$(echo "$TOKEN_LINE" | sed 's/.*Input tokens: *\([0-9,]*\) *Output tokens: *\([0-9,]*\).*/\2/')
TOTAL_TOKENS=$(echo "$HERMES_INSIGHTS" | grep "^  Total tokens:" | awk '{print $3}')
TOTAL_SESSIONS=$(echo "$HERMES_INSIGHTS" | grep "^  Sessions:" | awk '{print $2}')
TOTAL_MESSAGES=$(echo "$HERMES_INSIGHTS" | grep "^  Sessions:" | awk '{print $4}')
echo "  📊 累计Session: ${TOTAL_SESSIONS} | Message: ${TOTAL_MESSAGES}"
echo "  🔢 Token用量: 输入 ${INPUT_TOKENS} | 输出 ${OUTPUT_TOKENS} | 合计 ${TOTAL_TOKENS}"
echo ""

# ── 模块二：Minimax Coding Plan ──────────────────────────
echo "📊 Minimax Coding Plan 用量"
echo "------------------------------------------"
MINIMAX_SCRIPT="$HOME/.hermes/skills/system/system-check/scripts/minimax-check.sh"
if [ -f "$MINIMAX_SCRIPT" ]; then
  # 捕获 stderr，API 错误不混在主输出里
  MINIMAX_OUT=$(bash "$MINIMAX_SCRIPT" 2>&1)
  if [ $? -eq 0 ]; then
    echo "$MINIMAX_OUT"
  else
    echo "  ⚠️ 调用失败: ${MINIMAX_OUT}"
  fi
else
  echo "  ⚠️ 脚本未找到: $MINIMAX_SCRIPT"
fi
echo ""

# ── 模块三：硬件健康 ─────────────────────────────────────
OS=$(DETECT_OS)
echo "🖥️  硬件健康状态 (${OS})"
echo "------------------------------------------"

# — 磁盘（Linux/macOS 均兼容）—
DISK_USAGE=$(df -h / 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
if [ -n "$DISK_USAGE" ] && [ "$DISK_USAGE" -eq "$DISK_USAGE" ] 2>/dev/null; then
  echo "  💾 磁盘: ${DISK_USAGE}% / 468G"
  if (( DISK_USAGE > DISK_THRESHOLD )); then
    echo "     ❌ 告警 — 超过 ${DISK_THRESHOLD}%"
  else
    echo "     ✅ 正常"
  fi
else
  echo "  💾 磁盘: 无法获取"
fi

# — CPU —
if [ "$OS" = "macos" ]; then
  # macOS: top -l 1
  CPU_LINE=$(top -l 1 2>/dev/null | grep "CPU usage")
  CPU_USER=$(echo "$CPU_LINE" | sed -E 's/.*([0-9]+\.[0-9]+)% user.*/\1/' | tr -d ' ')
  CPU_SYS=$(echo "$CPU_LINE" | sed -E 's/.*([0-9]+\.[0-9]+)% sys.*/\1/' | tr -d ' ')
  if [ -z "$CPU_USER" ] || ! echo "$CPU_USER" | grep -qE '^[0-9]+\.[0-9]+$'; then
    CPU_USER=$(echo "$CPU_LINE" | awk '{print $3}' | sed 's/%//')
    CPU_SYS="0"
  fi
  if [ -n "$CPU_USER" ] && [ -n "$CPU_SYS" ]; then
    CPU_USED=$(awk "BEGIN {printf \"%.1f\", ${CPU_USER:-0} + ${CPU_SYS:-0}}")
  else
    CPU_USED="N/A"
  fi
  echo "  ⚙️  CPU: ${CPU_USED}% (user+sys)"
  # 阈值判断：CPU 使用率 > 80% 为高
  if [ "$CPU_USED" != "N/A" ]; then
    CPU_INT=$(awk "BEGIN {printf \"%.0f\", $CPU_USED}")
    if [ "$CPU_INT" -ge "$CPU_LOAD_THRESHOLD" ] 2>/dev/null; then
      echo "     ❌ 告警 — CPU 超过 ${CPU_LOAD_THRESHOLD}%"
    else
      echo "     ✅ 正常"
    fi
  fi
else
  # Linux: uptime
  CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d, -f1 | awk '{printf "%.2f\n", $1}')
  echo "  ⚙️  CPU负载(1m): ${CPU_LOAD}"
  # 用 awk 替代 bc 做浮点比较
  IS_HIGH=$(awk "BEGIN {print ($CPU_LOAD > $CPU_LOAD_THRESHOLD) ? 1 : 0}")
  if [ "$IS_HIGH" -eq 1 ]; then
    echo "     ❌ 告警 — 超过 ${CPU_LOAD_THRESHOLD}"
  else
    echo "     ✅ 正常"
  fi
fi

# — 内存 —
if [ "$OS" = "macos" ]; then
  # macOS: vm_stat 法（与 Activity Monitor 一致）
  FREE=$(vm_stat | grep "Pages free" | awk '{gsub(/[^0-9]/,""); print}')
  PURGE=$(vm_stat | grep "Pages purgeable" | awk '{gsub(/[^0-9]/,""); print}')
  INACT=$(vm_stat | grep "Pages inactive" | awk '{gsub(/[^0-9]/,""); print}')
  SPEC=$(vm_stat | grep "Pages speculative" | awk '{gsub(/[^0-9]/,""); print}')
  ACTIVE=$(vm_stat | grep "Pages active" | awk '{gsub(/[^0-9]/,""); print}')
  WIRED=$(vm_stat | grep "Pages wired down" | awk '{gsub(/[^0-9]/,""); print}')
  COMPR=$(vm_stat | grep "Pages compressed" | awk '{gsub(/[^0-9]/,""); print}')

  FREE_PAGES=$((FREE + PURGE + INACT + SPEC))
  USED_PAGES=$((ACTIVE + WIRED + COMPR))
  TOTAL_PAGES=$((FREE_PAGES + USED_PAGES))

  if [ "$TOTAL_PAGES" -gt 0 ]; then
    MEM_USAGE=$(awk "BEGIN {printf \"%.1f\", $USED_PAGES * 100 / $TOTAL_PAGES}")
  else
    MEM_USAGE="N/A"
  fi

  echo "  🧠 内存: ${MEM_USAGE}% (active+wired+compressed)"
  if [ "$MEM_USAGE" != "N/A" ]; then
    MEM_INT=$(awk "BEGIN {printf \"%.0f\", $MEM_USAGE}")
    if [ "$MEM_INT" -ge "$MEMORY_THRESHOLD" ] 2>/dev/null; then
      echo "     ❌ 告警 — 超过 ${MEMORY_THRESHOLD}%"
    else
      echo "     ✅ 正常"
    fi
  fi
else
  # Linux: free
  if command -v free &>/dev/null; then
    MEM_USED_PERCENT=$(free | awk '/^Mem:/ {printf "%.0f\n", $3/$2 * 100}')
    echo "  🧠 内存: ${MEM_USED_PERCENT}%"
    if (( MEM_USED_PERCENT > MEMORY_THRESHOLD )); then
      echo "     ❌ 告警 — 超过 ${MEMORY_THRESHOLD}%"
    else
      echo "     ✅ 正常"
    fi
  else
    echo "  🧠 内存: 无法获取（free 命令不可用）"
  fi
fi

echo ""
echo "=========================================="
echo "  ✅ 检测完成 — $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

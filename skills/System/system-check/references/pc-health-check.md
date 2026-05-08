# macOS 内存检查正确方式

## 错误计算（旧脚本）

```bash
# 错误：把 inactive/speculative/purgeable 算进"已用"
TOTAL=$((FREE + ACTIVE + WIRED + COMPR))
MEM_USAGE=$(echo "scale=1; $TOTAL * 100 / $TOTAL_PAGES" | bc)  # 虚高到 98%
```

macOS 的内存管理中：
- `inactive` = 已分配但最近未使用的页面，可随时回收
- `speculative` = 预读的页面，可回收
- `purgeable` = 可 purge 的页面
- 这些都**不算占用**

## 正确计算

```bash
# 真正占用 = active + wired + compressed
FREE=$(vm_stat | grep "Pages free" | awk '{gsub(/[^0-9]/,""); print}')
ACTIVE=$(vm_stat | grep "Pages active" | awk '{gsub(/[^0-9]/,""); print}')
WIRED=$(vm_stat | grep "Pages wired down" | awk '{gsub(/[^0-9]/,""); print}')
COMPR=$(vm_stat | grep "Pages compressed" | awk '{gsub(/[^0-9]/,""); print}')

FREE_PAGES=$((FREE + INACT + SPEC + PURGE))   # 可回收 = 空闲
USED_PAGES=$((ACTIVE + WIRED + COMPR))        # 真正占用
TOTAL_PAGES=$((FREE_PAGES + USED_PAGES))

MEM_USAGE=$(echo "scale=1; $USED_PAGES * 100 / $TOTAL_PAGES" | bc)
```

结果与 Activity Monitor 一致（约 60% 而不是 98%）。

## vm_stat 数字格式

macOS vm_stat 输出带尾缀点：`"4670."`、`"220800."`
清理方式：`awk '{gsub(/[^0-9]/,""); print}'`

## 脚本位置

- 正确版本：`~/.hermes/scripts/pc-health-check.sh`（已修复）
- 旧版本：`~/.hermes/scripts/system-check.sh`（未更新，如有）

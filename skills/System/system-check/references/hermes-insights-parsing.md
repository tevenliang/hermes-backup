# hermes insights 输出解析注意

## 数据来源

`hermes insights` 的 token 数据来自 `~/.hermes/state.db`（本地 SQLite），**不是** MiniMax API 返回值。统计周期是"最近 30 天"，不是从安装开始的累计。

## 字段解析陷阱

`Input tokens` 和 `Output tokens` 在**同一行**：

```
  Input tokens:      7,898,071     Output tokens:   468,751
  Total tokens:      99,760,383
```

不能用简单的 `awk '{print $3}'` 提取 Input——会拿到 `7,898,071` 但 Output 会错位。正确方式是用 sed 同一行解析：

```bash
TOKEN_LINE=$(hermes insights 2>&1 | grep "^  Input tokens:")
INPUT_TOKENS=$(echo "$TOKEN_LINE" | sed 's/.*Input tokens: *\([0-9,]*\) *Output tokens: *\([0-9,]*\).*/\1/')
OUTPUT_TOKENS=$(echo "$TOKEN_LINE" | sed 's/.*Input tokens: *\([0-9,]*\) *Output tokens: *\([0-9,]*\).*/\2/')
TOTAL_TOKENS=$(hermes insights 2>&1 | grep "^  Total tokens:" | awk '{print $3}')
```

Sessions 和 Messages 也在同一行：

```
  Sessions:          61            Messages:        3,578
```

```bash
TOTAL_SESSIONS=$(echo "$INSIGHTS" | grep "^  Sessions:" | awk '{print $2}')
TOTAL_MESSAGES=$(echo "$INSIGHTS" | grep "^  Sessions:" | awk '{print $4}')
```

## 其他可用命令

- `hermes status` — 模型、Gateway、活跃 Job/Session（实时）
- `hermes doctor` — 详细健康检查，含 Tool 可用性
- `hermes sessions list` — 最近 session 列表
- `hermes sessions stats` — 总 Session 数、Message 数、DB 大小

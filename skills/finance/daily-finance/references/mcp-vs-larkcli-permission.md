# MCP vs lark-cli 权限模型

## 核心区别

| 调用方式 | 身份 | bitable 权限 |
|---------|------|-------------|
| MCP 工具（agent 级别） | 用户身份 | ✅ 有（继承用户权限） |
| lark-cli 子进程 | Bot 身份 | ❌ 无（Bot 应用未开通 bitable 权限） |

## 为什么会失败

Python 脚本通过 `subprocess.run("lark-cli api GET ...")` 调用 lark-cli 时：
- lark-cli 运行在脚本外部，独立进程
- 它使用 Bot app 的身份（`cli_a97cf4a2bef8dcce`）
- Bot 应用没有在飞书后台开通 bitable 权限
- 即使加 `--as user` 也无效，因为 Bot 本身的权限域不包含 bitable

MCP 工具则不同：
- 是 agent 进程内的工具调用
- 使用用户的 OAuth token
- 用户能访问的多维表格，MCP 就能访问

## 解决方案：JSON 中介模式

```
Cron Job（Agent，有 MCP 工具）
  └── Step 1: MCP 读 bitable → 写本地 JSON
  └── Step 2: python3 daily_finance_new.py
        └── 读 JSON（无权限问题）
```

**为什么不让 Python 直接调 MCP？**
- Python 子进程无法直接调用 agent 的 MCP 工具
- MCP 是 agent 级别的，不是进程级别的
- JSON 文件是进程间数据传递的最简方式

## 相关错误信息

```json
{
  "code": 99991668,
  "msg": "permission_violations",
  "error": {
    "permission_violations": [{
      "subject": "bitable:app:readonly",
      "type": "action_privilege_required"
    }]
  }
}
```

## 适用场景

此模式适用于：
- cron job 调用 Python 脚本
- 脚本需要访问用户有权限但 Bot 无权限的资源
- 解决方案：cron agent 用 MCP 预取数据写 JSON，脚本只做计算/生成

不适用于：
- 纯 Python 环境（无 agent 上下文）需要访问 bitable → 仍需解决 Bot 权限问题

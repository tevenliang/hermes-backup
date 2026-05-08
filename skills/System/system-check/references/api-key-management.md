# API Key 管理规范（2026-05-04 确立）

## 架构

| 层次 | 位置 | 说明 |
|------|------|------|
| 唯一真实来源 | 飞书多维表格「账号密码」(app OvQ2bpM6gaez1ksDTYwclTPjnib, table tblvdLBUJJbOouUy) | 用户管理界面，Bot 只有读权限 |
| 运行时配置 | `~/.hermes/.env` | 所有 skill API key 写入这里 |
| 注入方式 | `config.yaml` terminal.env_passthrough: ["~/.hermes/.env"] | skill 通过环境变量读取 |

## 新增 key 流程

1. 用户告知 key 用途和 key 内容（或告知在多维表格哪条记录）
2. 我查飞书多维表格确认 key 值
3. 追加到 `~/.hermes/.env`（`echo 'KEY=value' >> ~/.hermes/.env`）
4. 如果 skill 有特殊注入要求，额外配置 `env_passthrough` 或 skill 专用配置
5. 验证：直接运行 skill 脚本测试

## 当前已配置

- `TAVILY_API_KEY` → `~/.hermes/.env`，skill `tavily-search` 使用

## 注意

- Bot 对「账号密码」多维表格**仅有读权限**，无法回写备注
- `~/.zshrc` 不是正确的注入方式（skill 运行不走 login shell）
- 唯一可靠的跨 skill 注入方式是通过 `config.yaml` 的 `env_passthrough`

## 添加新 key 时

```bash
# 追加到 ~/.hermes/.env
echo 'NEW_API_KEY=your_key_here' >> ~/.hermes/.env

# 如果 skill 需要特殊环境变量，写入 skill 的 _meta.json 或参考 skill 文档
# 然后验证
node ~/.hermes/skills/<skill-name>/scripts/search.mjs "test" -n 1
```

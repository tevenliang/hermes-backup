# 部署指南（腾讯云 OpenClaw）

本 Skill 需要以下环境准备，请在首次部署时完成配置。

---

## 一、lark-cli 安装与授权（必须）

OpenClaw 所在机器需要安装飞书 CLI 并完成 OAuth 授权：

```bash
# 1. 安装
npm install -g @larksuite/cli

# 2. 验证
lark-cli --version

# 3. 授权（交互式，需在有浏览器的环境操作一次）
lark-cli config init
# 按提示：用飞书账号扫码授权，授权后配置保存在 ~/.lark-cli/config.json
```

> 授权完成后配置持久化，后续执行无需再次授权。
> 若腾讯云无浏览器环境，需在本机完成授权后把 `~/.lark-cli/config.json` 上传到目标机器对应路径。

---

## 二、Tavily API Key（可选，无则用 curl 兜底）

Tavily 用于无腾讯新闻链接时的兜底搜索。
申请地址：https://app.tavily.com（免费额度 1000 次/月）

```bash
export TAVILY_API_KEY=tvly-xxxxxxxxxxxx
```

或者直接在 `config/config.json` 中填入（不推荐在共享环境）。

---

## 三、验证脚本

```bash
python3 ~/.workbuddy/skills/客户新闻追踪/scripts/fetch_and_sync.py --dry-run
```

无报错即为环境就绪。

---

## 四、腾讯云 OpenClaw 使用方式

在 OpenClaw 对话框中发送触发词即可：

```
客户新闻、每日客户新闻、客户情报
```

---

## 五、如需修改参数

编辑 `config/config.json`：
- `bitable.app_token` / `bitable.table_id`：知识库表地址
- `lark.folder_token`：文档存放的飞书云盘文件夹
- `tavily.api_key`：新闻搜索 API Key

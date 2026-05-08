# WeChat 渠道配置清理（2026-05-07）

## 触发

用户要求删除本地 Hermes 中的微信（WeChat/Weixin）渠道配置。

## 清理范围

WeChat 渠道配置分散在 5 处，需要全部清除才能彻底移除：

### 1. `.env` — WEIXIN_* 环境变量

路径：`~/.hermes/.env`

删除所有以 `WEIXIN_` 开头的行，典型变量包括：
```
WEIXIN_ACCOUNT_ID=c090968d80a2@im.bot
WEIXIN_TOKEN=c090968d80a2@im.bot:0600001362df61d644fb652cd54de1933df266
WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
WEIXIN_CDN_BASE_URL=https://novac2c.cdn.weixin.qq.com/c2c
WEIXIN_DM_POLICY=pairing
WEIXIN_ALLOW_ALL_USERS=false
WEIXIN_ALLOWED_USERS=
WEIXIN_GROUP_POLICY=open
WEIXIN_GROUP_ALLOWED_USERS=
```

删除方式：
```python
with open(env_file) as f:
    lines = f.readlines()
other_lines = [l for l in lines if not l.startswith('WEIXIN_')]
with open(env_file, 'w') as f:
    f.writelines(other_lines)
```

### 2. `weixin/` 目录

路径：`~/.hermes/weixin/`

包含账号 token 和 context-tokens 数据。直接删除整个目录：
```python
import shutil
shutil.rmtree(f'{hermes}/weixin/')
```

### 3. `channel_directory.json` — 渠道记录

路径：`~/.hermes/channel_directory.json`

结构为 `{ "updated_at": "...", "platforms": { "weixin": [...], ... } }`。

删除 `platforms.weixin` key：
```python
with open(ch_file) as f:
    ch_data = json.load(f)
del ch_data['platforms']['weixin']
with open(ch_file, 'w') as f:
    json.dump(ch_data, f, indent=2)
```

### 4. `gateway_state.json` — 网关状态

路径：`~/.hermes/gateway_state.json`

结构与 `channel_directory.json` 类似，`platforms.weixin` 包含连接状态（connected/disconnected）。

删除方式同上。

### 5. `state.db` — 会话记录

路径：`~/.hermes/state.db`

`sessions` 表中 `source='weixin'` 的记录为 WeChat 会话。

```python
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("DELETE FROM sessions WHERE source='weixin'")
conn.commit()
```

**注意**：messages 表中 content 字段的历史消息（含 weixin 提及）属于用户数据，不是配置。如用户未明确要求，不应删除。

## 清理顺序

按上述顺序执行即可，无强依赖关系。使用 `execute_code` python 脚本处理，避免 terminal shell 会话损坏。

## 验证

清理完成后确认：
- `.env` 中无 `WEIXIN_` 行
- `weixin/` 目录不存在
- `channel_directory.json` 中无 `weixin` key
- `gateway_state.json` 中无 `weixin` key
- `state.db` 中无 `source='weixin'` 的 sessions

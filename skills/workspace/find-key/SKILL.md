---
name: find-key
description: 账号密码查询与管理，全部数据存在飞书多维表格，搜索字段包括账号描述、账号、备注
version: 1.1.0
category: workspace
---

# 账号密码 Skill

## 数据源

**飞书多维表格**（唯一数据源）：
- Token: `OvQ2bpM6gaez1ksDTYwclTPjnib`
- Table ID: `tblvdLBUJJbOouUy`
- 链接: https://my.feishu.cn/base/OvQ2bpM6gaez1ksDTYwclTPjnib?table=tblvdLBUJJbOouUy&view=vewbnBSOLU

**字段：**
| 字段名 | 类型 | 说明 |
|--------|------|------|
| 账号描述 | Text（主字段） | 搜索关键词，如"东方财富-API" |
| 类型 | SingleSelect | 自动AI判断分类 |
| 账号 | Text | 账号 |
| 密码 | Text | 密码原文 |
| 备注或APIKEY | Text | API Key 或备注 |
| 创建日期 | DateTime | 自动默认值 |

---

## 查询账号

**触发词：** "查账号"、"查询账号"、"看看xxx的账号"、"账号密码"

**步骤：**
1. 用 `lark-cli base +record-list` 读取全表记录
2. 在返回结果中按关键词匹配 `账号描述` / `账号` / `备注或APIKEY` 字段
3. 返回匹配结果（完整密码直接显示）

**命令：**
```bash
lark-cli base +record-list --base-token OvQ2bpM6gaez1ksDTYwclTPjnib --table-id tblvdLBUJJbOouUy --as user
```

**返回格式：**
```
🔍 查询结果：「{账号描述}」

📋 账号详情：
  • 账号描述：{账号描述}
  • 类型：{类型}
  • 账号：{账号}
  • 密码：{密码原文}
  • 备注：{备注}
```

**未找到时：**
```
❌ 未找到「{关键词}」的记录。
是否需要新建？
```

---

## 新建账号

**触发词：** "新建账号"、"添加账号"、"创建账号"

**步骤：**
1. 询问：账号描述 / 类型 / 账号 / 密码 / 备注
2. 用 `lark-cli base +record-batch-create` 写入表格
3. 类型字段由飞书表格自动AI判断

---

## 更新账号

**触发词：** "更新密码"、"修改账号"、"更新账号"

1. 通过账号描述找到记录
2. 用 `lark-cli base +record-update` 更新字段

---

## 删除账号

**触发词：** "删除账号"

1. 确认账号描述
2. 手动在飞书多维表格中删除（lark-cli 暂不支持 delete_record）

---

## 注意

- 搜索为模糊匹配（大小写不敏感）
- 密码直接显示完整原文
- Ontology 不再存储账号密码数据
- **必须使用 lark-cli 执行所有操作，禁止使用 lark-mcp**（MCP token 频繁过期，错误多）

## 已知陷阱

### lark-cli 与 lark-mcp 是两套独立认证系统
**问题**: lark-mcp 的 token 容易过期且恢复复杂（需要 OAuth 浏览器回调 localhost:3000）
**解决**: 所有飞书操作统一用 lark-cli，其 token 通过 device code 自动续期，更稳定

### lark-cli base +record-list 不支持服务端过滤
**问题**: lark-cli base 命令不支持 --filter 参数，无法在服务端过滤
**解决**: 读回全表记录后，在客户端按关键词过滤字段

### contains 操作符只接受单个值（旧版 MCP 已废弃）
**症状**: `InvalidFilter` 错误
**原因**: lark-mcp 的 `contains` 操作符只接受单个字符串
**状态**: 已废弃，切换到 lark-cli 后无此限制

---

## 回复风格

直接给出查询结果，不用冗长的铺垫或确认语句。
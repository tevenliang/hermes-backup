category: productivity
---
name: 飞书任务
version: 1.3
description: 提醒事项与任务管理：设置提醒、查看任务、标记完成、删除任务、自动分类到工作/学习/生活列表。当用户提到"提醒我"、"设置提醒"、"创建任务"、"查看任务"、"完成任务"、"删除任务"时触发。
---

# 提醒事项管理

管理闻哥的飞书任务，支持飞书推送提醒、AI自动分类。

## 核心功能

- **设置提醒**：写入飞书任务 + 飞书推送通知
- **查看任务**：列出三个列表（工作/学习/生活）的所有任务
- **完成任务**：标记任务为已完成 + 备注
- **删除任务**：删除过期/测试任务
- **自动分类**：AI智能判断任务属于工作/学习/生活

## 飞书任务列表配置

| 列表名 | List ID |
|--------|---------|
| 工作 | BSLIST01wzmwLjIBXcAAAAAAA |
| 学习 | BSLIST01wzmwLjIBXcAAAAAAAB |
| 生活 | BSLIST01wzmwLjIBXcAAAAAAAC |

## 脚本使用

### 设置提醒（推荐用 AI 自动分类）

```bash
python3 skills/todo-management/scripts/todo_manager.py add "<任务描述>" "<截止时间>"
```

- AI 自动判断分类到工作/学习/生活
- 示例：`python3 skills/todo-management/scripts/todo_manager.py add "回复客户邮件" "2026-04-25T20:00:00+08:00"`

### 查看任务

```bash
python3 skills/todo-management/scripts/todo_manager.py list
```

### 完成任务

```bash
python3 skills/todo-management/scripts/todo_manager.py done "<任务标题关键词>"
python3 skills/todo-management/scripts/todo_manager.py done "<任务标题关键词>" --note "<备注内容>"
```

### 删除任务

```bash
python3 skills/todo-management/scripts/todo_manager.py delete "<任务标题关键词>"
```

## AI 自动分类规则

| 分类 | 关键词 |
|------|--------|
| 工作 | GitLab、客户、会议、汇报、销售、BOSS、LinkedIn、openclaw、邮件、电话、拜访、跟进、方案、PPT、周报、KPI |
| 学习 | 学习、研究、GTD、skills、优化、课程、培训、AI、编程、代码、market-news、安装、配置、搭建、复盘 |
| 生活 | 购物、旅行、休息、娱乐、美食、运动、家人、朋友、宠物、电影、聚会 |

## 输出格式规范（v1.1）

list 输出时：
- 按列表（工作/学习/生活）平铺输出，不分组显示
- 每个任务前加强序号（1、2、3...），序号在列表内连续
- 显示任务标题 + 截止日期（截止日期为 04-29 这样只显示月-日）
- 示例：
  ```
  1. [工作] Notebooklm最佳实践（无截止）
  2. [学习] 无头浏览器（04-29）
  3. [学习] 尝试修改get笔记加入自定义标签（无截止）
  ...
  ```

## 已知问题

**Python 3.9.6 语法错误（SyntaxError: f-string）**

`scripts/todo_manager.py` 第 393 行使用了 Python 3.12+ 的 f-string 嵌套引号语法：
```python
print(f"   🔄 {" / ".join(parts)}")   # SyntaxError on Python 3.9.6
```

修复：改为
```python
print("   🔄 " + " / ".join(parts))
```

MacBook 上 Python 版本为 3.9.6，执行前必须确认此行已修复。

## 注意事项

- 只写入飞书任务，不写 Outlook To-Do
- 所有任务必须通过 AI 自动分类，不允许手动指定分类
- 新增任务时默认负责人设为闻哥本人（Steven Liang，open_id: ou_d4b39b86c8715f79b2c5b070c4e55393）
- 删除任务前先查询确认精确 ID，避免误删
- 定期清理过期/测试任务，保持列表干净

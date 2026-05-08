#!/usr/bin/env python3
"""
提醒事项管理 - 飞书任务 API，支持AI自动分类到工作/学习/生活
不再使用 Outlook To-Do（Maton API），全部迁移到飞书任务
"""
import sys, json, subprocess, re
from datetime import datetime, timezone, timedelta

SH_TZ = timezone(timedelta(hours=8))

# 飞书任务列表 GUID（从 lark-cli task tasklists list 获取）
LIST_MAP = {
    "工作": "be555084-43da-4f29-a28f-eecb561eebc4",
    "学习": "1e3027d6-d0e0-442e-b1f9-fd6c39e03317",
    "生活": "18a601d2-9829-411c-ac98-7280e84adbe6",
}

FEISHU_USER_ID = "ou_d4b39b86c8715f79b2c5b070c4e55393"

# 智能分类规则
CATEGORY_KEYWORDS = {
    "工作": {
        "strong": ["GitLab", "客户", "会议", "汇报", "销售", "BOSS直聘", "LinkedIn", "openclaw", "提醒", "工作", "经理", "总监", "面试", "招聘", "绩效", "合同", "谈判", "渠道", "合作伙伴", "市场", "推广", "方案", "提案", "PPT", "周报", "月报", "工资", "晋升", "CRM", "KPI"],
        "medium": ["邮件", "电话", "拜访", "沟通", "跟进", "任务", "待办", "报告"]
    },
    "学习": {
        "strong": ["学习", "研究", "GTD", "skills", "优化", "课程", "培训", "AI", "编程", "代码", "market-news", "skill", "安装", "配置", "搭建", "复盘", "总结", "考试", "证书", "教程", "实践", "知识", "理解"],
        "medium": ["读", "写", "练", "研究"]
    },
    "生活": {
        "strong": ["购物", "旅行", "旅游", "休息", "娱乐", "美食", "运动", "健身", "跑步", "家人", "朋友", "生日", "聚会", "约会", "宠物", "家务", "去医院", "挂号", "体检", "保险", "度假"],
        "medium": ["电影", "电视", "游戏", "吃饭", "餐厅"]
    }
}

ERROR_LOG = "/tmp/reminder_errors.log"

def log_error(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def smart_categorize(message):
    """基于关键词权重智能分类"""
    msg = message.lower()
    scores = {"工作": 0, "学习": 0, "生活": 0}
    for cat, rules in CATEGORY_KEYWORDS.items():
        for kw in rules["strong"]:
            if kw.lower() in msg:
                scores[cat] += 3
        for kw in rules["medium"]:
            if kw.lower() in msg:
                scores[cat] += 1
    for kw in ["邮件", "电话", "客户", "会议", "汇报", "工作"]:
        if kw in message:
            scores["工作"] += 2
    max_score = max(scores.values())
    if max_score == 0:
        return "生活"
    for cat in ["工作", "学习", "生活"]:
        if scores[cat] == max_score:
            return cat
    return "生活"

def lark_run(args, timeout=15):
    """封装 lark-cli 调用"""
    cmd = ["lark-cli"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        log_error(f"lark-cli failed: {' '.join(args)} -> {r.stderr}")
        return None
    try:
        return json.loads(r.stdout)
    except:
        return None

def get_feishu_token():
    data = json.dumps({
        "app_id": "cli_a947b541d8785bd9",
        "app_secret": "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
    }).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())["tenant_access_token"]

import urllib.request

def send_feishu(message, retry=True):
    try:
        token = get_feishu_token()
        payload = json.dumps({
            "receive_id": FEISHU_USER_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message})
        }).encode()
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            data=payload, method="POST"
        )
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        if result.get("code") == 0:
            return True
        else:
            log_error(f"飞书发送失败: code={result.get('code')} msg={result.get('msg')}")
            if retry:
                return send_feishu(message, retry=False)
            return False
    except Exception as e:
        log_error(f"飞书异常: {e}")
        if retry:
            return send_feishu(message, retry=False)
        return False

# ========== 飞书任务 API ==========

# 分组 GUID（已知的不支持写入，仅保留作参考）
SECTION_MAP = {
    "工作": "54bf5343-4df5-454c-fdf4-a6e820021db0",
    "学习": "37bed3b9-2433-d572-98db-c770bd4e985f",
    "生活": "c469b880-7d14-32c2-3006-a9e1960dad5a",
}

def add_feishu_task(title, due_str, list_name):
    """创建飞书任务，reminders=[]取消默认提醒时间"""
    list_id = LIST_MAP.get(list_name, LIST_MAP["生活"])
    payload = {"summary": title, "reminders": []}
    if due_str:
        payload["due"] = {
            "timestamp": _parse_ts(due_str),
            "is_all_day": " " not in due_str
        }
    data_json = json.dumps(payload)
    args = ["task", "+create", "--tasklist-id", list_id, "--data", data_json, "--format", "json"]
    return lark_run(args)

def _parse_ts(due_str):
    """把 "2026-05-02" 或 "2026-05-02 16:00" 转成毫秒时间戳"""
    if " " in due_str:
        dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
    else:
        dt = datetime.strptime(due_str, "%Y-%m-%d")
    dt = dt.replace(tzinfo=SH_TZ)
    return str(int(dt.timestamp() * 1000))


def update_feishu_task_note(task_guid, note):
    """更新任务评论（写入评论而非description）"""
    args = ["task", "+comment", "--task-id", task_guid, "--content", note, "--as", "user", "--format", "json"]
    return lark_run(args)

def update_feishu_task(task_guid, title=None, due_str=None):
    """更新任务标题或截止时间"""
    task_body = {}
    update_fields = []
    if title:
        task_body["summary"] = title
        update_fields.append("summary")
    if due_str:
        # due_str 格式: "2026-05-02 16:00" 或 "2026-05-02"
        import time
        try:
            if " " in due_str:
                dt = datetime.strptime(due_str, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(due_str, "%Y-%m-%d")
            dt = dt.replace(tzinfo=SH_TZ)
            ts = str(int(dt.timestamp() * 1000))
            is_all_day = " " not in due_str
            task_body["due"] = {"timestamp": ts, "is_all_day": is_all_day}
            update_fields.append("due")
        except Exception as e:
            log_error(f"日期解析失败: {due_str} -> {e}")
            return None
    if not task_body:
        return None
    data = json.dumps({"task": task_body, "update_fields": update_fields})
    args = ["task", "tasks", "patch", "--task-id", task_guid, "--data", data, "--as", "user", "--format", "json"]
    return lark_run(args)

def complete_feishu_task(task_guid):
    """完成任务"""
    args = ["task", "+complete", "--task-id", task_guid, "--format", "json"]
    return lark_run(args)

def update_feishu_task_note(task_guid, note):
    """更新任务评论（写入评论而非description）"""
    args = ["task", "+comment", "--task-id", task_guid, "--content", note, "--as", "user", "--format", "json"]
    return lark_run(args)


def delete_feishu_task(task_guid):
    """删除任务"""
    args = ["task", "tasks", "delete", "--task-id", task_guid, "--format", "json"]
    return lark_run(args)

def search_feishu_tasks(keyword):
    """搜索任务"""
    args = ["task", "+search", "--query", keyword, "--format", "json"]
    result = lark_run(args)
    if not result:
        return []
    return result.get("data", {}).get("items", [])

def list_feishu_tasks(list_name=None):
    """列出任务列表中的任务"""
    if list_name:
        list_ids = [LIST_MAP.get(list_name)]
    else:
        list_ids = list(LIST_MAP.values())
    
    all_tasks = []
    for lid in list_ids:
        # 使用通用 API，因为 lark-cli task tasklists tasks 不支持 --tasklist-guid 传参
        args = ["api", "GET", f"/open-apis/task/v2/tasklists/{lid}/tasks", "--as", "user", "--format", "json"]
        r = subprocess.run(["lark-cli"] + args, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            try:
                result = json.loads(r.stdout)
                items = result.get("data", {}).get("items", [])
                all_tasks.extend(items)
            except:
                pass
    return all_tasks

def get_task_detail(task_guid):
    """获取任务详情"""
    args = ["task", "tasks", "get", "--task-id", task_guid, "--format", "json"]
    return lark_run(args)

# ========== 命令实现 ==========

def cmd_add(message, due_str, title=None, category=None):
    cat = category or smart_categorize(message)
    title = title or message[:50]
    print(f"🏷️  自动分类: {cat}")
    print(f"📱 发飞书: {message[:40]}...")

    feishu_ok = send_feishu(message)
    print(f"{'✅' if feishu_ok else '❌'} 飞书: {'成功' if feishu_ok else '失败'}")

    print(f"📋 写飞书任务: {title[:40]} (截止 {due_str}) -> [{cat}]...")
    result = add_feishu_task(title, due_str, cat)
    task_ok = result and result.get("ok", False)
    if task_ok:
        task_guid = result.get("data", {}).get("guid", "")
        task_url = result.get("data", {}).get("url", "")
        print(f"✅ 飞书任务: 成功 -> {task_url}")
    else:
        print(f"❌ 飞书任务: 失败")
        log_error(f"add_feishu_task failed: {result}")

    if feishu_ok and task_ok:
        print("🎉 任务创建完成！")
    else:
        print("⚠️ 部分失败")

def parse_due(task):
    """解析任务截止日期"""
    due = task.get("due", {})
    ts_str = due.get("timestamp", "") if due else ""
    is_all_day = due.get("is_all_day", False) if due else False
    if not ts_str:
        return ("(未设截止)", False, None)
    try:
        if len(ts_str) >= 13:
            dt = datetime.fromtimestamp(int(ts_str) / 1000, tz=SH_TZ)
        else:
            dt = datetime.fromtimestamp(int(ts_str), tz=SH_TZ)
    except:
        return ("(解析失败)", False, None)
    
    now_sh = datetime.now(SH_TZ)
    today_start = now_sh.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now_sh.replace(hour=23, minute=59, second=59)
    if is_all_day:
        due_str = dt.strftime("%m-%d")
    else:
        due_str = dt.strftime("%m-%d %H:%M")
    is_today = today_start <= dt <= today_end
    return (due_str, is_today, dt)

def cmd_list(today_only=False):
    list_names = {"be555084-43da-4f29-a28f-eecb561eebc4": "工作",
                   "1e3027d6-d0e0-442e-b1f9-fd6c39e03317": "学习",
                   "18a601d2-9829-411c-ac98-7280e84adbe6": "生活"}

    now_sh = datetime.now(SH_TZ)

    all_pending = []
    for lid, name in list_names.items():
        tasks = list_feishu_tasks(name)
        pending = [t for t in tasks if not t.get("completed_at") or t.get("completed_at") in ("0", 0)]
        
        if today_only:
            today_tasks = []
            for t in pending:
                due = t.get("due", {})
                ts_str = due.get("timestamp", "") if due else ""
                if ts_str:
                    try:
                        if len(ts_str) >= 13:
                            dt = datetime.fromtimestamp(int(ts_str) / 1000, tz=SH_TZ)
                        else:
                            dt = datetime.fromtimestamp(int(ts_str), tz=SH_TZ)
                        if dt.date() == now_sh.date():
                            today_tasks.append(t)
                    except:
                        pass
            pending = today_tasks

        for t in pending:
            all_pending.append((name, t))

    if not all_pending:
        print("📋 闻哥的提醒事项")
        print("（暂无任务）")
        return

    print("📋 闻哥的提醒事项\n")
    for i, (cat, t) in enumerate(all_pending, 1):
        title = t.get("summary", t.get("title", ""))
        due_str, is_today, _ = parse_due(t)
        date_str = due_str.strip("()")
        print(f"{i}. [{cat}] {title}（{date_str}）")

def cmd_done(keyword, note=None):
    """完成任务"""
    results = search_feishu_tasks(keyword)
    if not results:
        print(f"❌ 未找到包含「{keyword}」的任务")
        return
    for r in results:
        guid = r.get("guid")
        title = r.get("summary", "")
        completed = r.get("completed_at")
        if completed:
            print(f"ℹ️  已完成跳过: {title}")
            continue
        if note:
            # 先写备注，再完成
            update_feishu_task_note(guid, note)
        result = complete_feishu_task(guid)
        if result and result.get("ok"):
            print(f"✅ 已完成: {title}")
            if note:
                print(f"   📝 备注: {note}")
        else:
            print(f"❌ 完成失败: {title}")

def cmd_delete(keyword):
    """删除任务"""
    results = search_feishu_tasks(keyword)
    if not results:
        print(f"❌ 未找到包含「{keyword}」的任务")
        return
    for r in results:
        guid = r.get("guid")
        title = r.get("summary", "")
        result = delete_feishu_task(guid)
        if result and result.get("ok"):
            print(f"✅ 已删除: {title}")
        else:
            print(f"❌ 删除失败: {title}")

def cmd_update(keyword, new_title=None, new_due=None):
    """更新任务标题或截止时间"""
    results = search_feishu_tasks(keyword)
    if not results:
        print(f"❌ 未找到包含「{keyword}」的任务")
        return
    for r in results:
        guid = r.get("guid")
        title = r.get("summary", "")
        result = update_feishu_task(guid, new_title, new_due)
        if result is None:
            print(f"⚠️  无更新内容: {title}")
            continue
        if result.get("ok"):
            parts = []
            if new_title:
                parts.append(f"标题 -> {new_title}")
            if new_due:
                parts.append(f"截止 -> {new_due}")
            print(f"✅ 已更新: {title}")
            if parts:
                print(f"   🔄 {" / ".join(parts)}")
        else:
            print(f"❌ 更新失败: {title}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""用法:
  python3 todo_manager.py add "<任务描述>" "<截止时间>" [标题]
  python3 todo_manager.py list [--today]
  python3 todo_manager.py done "<任务关键词>" [--note <备注>]
  python3 todo_manager.py delete "<任务关键词>"
  python3 todo_manager.py update "<任务关键词>" [--title <新标题>] [--due <新截止时间>]
        """)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 4:
            print("❌ add 需要 <任务描述> 和 <截止时间>")
            sys.exit(1)
        message = sys.argv[2]
        due_str = sys.argv[3]
        title = None
        category = None
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--title" and i + 1 < len(sys.argv):
                title = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--category" and i + 1 < len(sys.argv):
                category = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        cmd_add(message, due_str, title, category)
    elif cmd == "list":
        today_only = "--today" in sys.argv
        cmd_list(today_only=today_only)
    elif cmd == "done":
        if len(sys.argv) < 3:
            print("❌ done 需要 <任务关键词>")
            sys.exit(1)
        keyword = sys.argv[2]
        note = None
        for i, arg in enumerate(sys.argv):
            if arg == "--note" and i + 1 < len(sys.argv):
                note = sys.argv[i + 1]
                break
        cmd_done(keyword, note)
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("❌ delete 需要 <任务关键词>")
            sys.exit(1)
        keyword = sys.argv[2]
        cmd_delete(keyword)
    elif cmd == "update":
        if len(sys.argv) < 3:
            print("❌ update 需要 <任务关键词>")
            sys.exit(1)
        keyword = sys.argv[2]
        new_title = None
        new_due = None
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--title" and i + 1 < len(sys.argv):
                new_title = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--due" and i + 1 < len(sys.argv):
                new_due = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        if not new_title and not new_due:
            print("❌ update 至少需要 --title 或 --due 其中之一")
            sys.exit(1)
        cmd_update(keyword, new_title, new_due)
    else:
        print(f"❌ 未知命令: {cmd}")
        sys.exit(1)

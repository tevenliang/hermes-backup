#!/usr/bin/env python3
"""提醒事项管理 - 飞书推送 + Outlook To-Do 同步，支持AI自动分类到工作/学习/生活"""
import sys, json, urllib.request, time, re
from datetime import datetime, timezone, timedelta

FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FEISHU_USER_ID = "ou_d4b39b86c8715f79b2c5b070c4e55393"
MATON_KEY = "GQWYNUq1TbTaisz_a26wKJDLEQn70PgsH3um2Kqv87a0M4qIGVynDdUwehh1U897HtIc1B9aDR07F3iLckDVKWI3hFKn4ukipSo"
SH_TZ = timezone(timedelta(hours=8))

# 列表ID映射
LIST_MAP = {
    "工作": "AQMkADAwATNiZmYAZS1iMDAAZC1jN2UyLTAwAi0wMAoALgAAA4tjk6PQscFKo9qqy51WnSsBAL3l3JnfYFhMgwOqGr9A1EMAAAJayAAAAA==",
    "学习": "AQMkADAwATNiZmYAZS1iMDAAZC1jN2UyLTAwAi0wMAoALgAAA4tjk6PQscFKo9qqy51WnSsBAL3l3JnfYFhMgwOqGr9A1EMAAAJayQAAAA==",
    "生活": "AQMkADAwATNiZmYAZS1iMDAAZC1jN2UyLTAwAi0wMAoALgAAA4tjk6PQscFKo9qqy51WnSsBAL3l3JnfYFhMgwOqGr9A1EMAAAJaygAAAA==",
}

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
    work_indicators = ["邮件", "电话", "客户", "会议", "汇报", "工作"]
    for kw in work_indicators:
        if kw in message:
            scores["工作"] += 2
    max_score = max(scores.values())
    if max_score == 0:
        return "生活"
    for cat in ["工作", "学习", "生活"]:
        if scores[cat] == max_score:
            return cat
    return "生活"

def get_feishu_token():
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())["tenant_access_token"]

ERROR_LOG = "/tmp/reminder_errors.log"

def log_error(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")

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

def add_outlook_task(title, due_str, list_name):
    list_id = LIST_MAP.get(list_name, LIST_MAP["生活"])
    payload = json.dumps({
        "title": title,
        "dueDateTime": {"dateTime": due_str, "timeZone": "China Standard Time"}
    }).encode()
    task_url = f"https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{list_id}/tasks"
    req = urllib.request.Request(task_url, data=payload, method='POST')
    req.add_header('Authorization', f'Bearer {MATON_KEY}')
    req.add_header('Content-Type', 'application/json')
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

def complete_task(list_id, task_id, note=None):
    payload = {"status": "completed"}
    if note:
        payload["body"] = {"contentType": "text", "content": note}
    data = json.dumps(payload).encode()
    url = f'https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{list_id}/tasks/{task_id}'
    req = urllib.request.Request(url, data=data, method='PATCH')
    req.add_header('Authorization', f'Bearer {MATON_KEY}')
    req.add_header('Content-Type', 'application/json')
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

def delete_task(list_id, task_id):
    url = f'https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{list_id}/tasks/{task_id}'
    req = urllib.request.Request(url, method='DELETE')
    req.add_header('Authorization', f'Bearer {MATON_KEY}')
    urllib.request.urlopen(req, timeout=15)
    return True

def find_task(keyword):
    """在所有列表中查找匹配的任务"""
    results = []
    for name, list_id in LIST_MAP.items():
        url = f'https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{list_id}/tasks'
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {MATON_KEY}')
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            tasks = json.loads(resp.read()).get('value', [])
            for t in tasks:
                if keyword in t.get('title', ''):
                    results.append({
                        'list_name': name,
                        'list_id': list_id,
                        'id': t['id'],
                        'title': t['title'],
                        'status': t.get('status')
                    })
        except Exception as e:
            pass
    return results

def cmd_add(message, due_str, title=None):
    category = smart_categorize(message)
    title = title or message[:50]
    print(f"🏷️  自动分类: {category}")
    print(f"📱 发飞书: {message[:40]}...")
    feishu_ok = send_feishu(message)
    print(f"{'✅' if feishu_ok else '❌'} 飞书: {'成功' if feishu_ok else '失败'}")
    print(f"📋 写Outlook: {title[:40]} (截止 {due_str}) -> [{category}]...")
    try:
        result = add_outlook_task(title, due_str, category)
        outlook_ok = result.get('title') is not None
        print(f"{'✅' if outlook_ok else '❌'} Outlook: {'成功' if outlook_ok else '失败'} -> {category}列表")
    except Exception as e:
        print(f"❌ Outlook: {e}")
        outlook_ok = False
    if feishu_ok and outlook_ok:
        print("🎉 两边同步完成！")
    else:
        print("⚠️ 部分失败")

def parse_due(task):
    """解析任务截止日期，返回(due_str, is_today, is_default_zero, dt_obj)"""
    due = task.get('dueDateTime', {})
    dt_str = due.get('dateTime', '')
    time_zone = due.get('timeZone', '')
    if not dt_str:
        return ('(未设截止)', False, False, None)
    try:
        # 去掉末尾的Z或+00:00，统一按UTC时间解析
        clean = dt_str.replace('Z', '').replace('+00:00', '').strip()
        # 去除微秒部分（API返回7位）
        if '.' in clean:
            clean = clean.split('.')[0]
        has_explicit_tz = (dt_str.endswith('Z') or '+' in dt_str)
        # 关键逻辑：API 返回 timeZone='UTC' 的全天任务（hour=0）时，
        # macOS 把"全天"存为 UTC 0点，这不代表 UTC 时间，而是"当天"的约定俗成
        # 所以：timeZone='UTC' + hour=0 → 当作深圳时区直接解释，不走 UTC 转换
        if time_zone == 'UTC' and not has_explicit_tz:
            dt_check = datetime.fromisoformat(clean).replace(tzinfo=SH_TZ)
            if dt_check.hour == 0 and dt_check.minute == 0:
                # 全天任务，直接按深圳日期解释，不做 UTC 偏移
                dt_sh = dt_check.replace(hour=0, minute=0, second=0)
            else:
                dt_sh = dt_check
        else:
            dt_utc = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
            dt_sh = dt_utc.astimezone(SH_TZ)
    except Exception as e:
        return ('(解析失败)', False, False, None)
    now_sh = datetime.now(SH_TZ)
    today_start = now_sh.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now_sh.replace(hour=23, minute=59, second=59)
    # 检查是否是默认零点（未设具体时间，API默认返回当天00:00 UTC）
    if dt_sh.hour == 0 and dt_sh.minute == 0 and dt_sh.second == 0:
        due_str = dt_sh.strftime('%m-%d')
        is_today = today_start <= dt_sh <= today_end
        return (due_str, is_today, True, dt_sh)
    # 正常截止日期
    due_str = dt_sh.strftime('%m-%d %H:%M')
    is_today = today_start <= dt_sh <= today_end
    return (due_str, is_today, False, dt_sh)

def cmd_list(today_only=False):
    print("📋 闻哥的提醒事项\n")
    for name, list_id in LIST_MAP.items():
        url = f'https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{list_id}/tasks'
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {MATON_KEY}')
        resp = urllib.request.urlopen(req, timeout=15)
        tasks = json.loads(resp.read()).get('value', [])

        # 分离已完成和未完成
        completed = [t for t in tasks if t.get('status') == 'completed']
        pending = [t for t in tasks if t.get('status') != 'completed']

        if today_only:
            # 今日待办：截止日期在今天或昨天的任务
            now_sh = datetime.now(SH_TZ)
            today_start = datetime.now(SH_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            def is_today_due(t):
                dt = parse_due(t)[3]
                if dt is None:
                    return False
                # 严格匹配今天（不过滤昨天的逾期任务）
                return dt.date() == now_sh.date()
            pending = [t for t in pending if is_today_due(t)]

        if pending or completed:
            print(f"【{name}】")
            idx = 1
            for t in pending:
                due_str, is_today, is_default, _ = parse_due(t)
                marker = '📅' if is_today else '  '
                default_tag = ' ⏰' if is_default else ''
                note = t.get('body', {}).get('content', '')
                print(f"  {idx}. 📌 {t.get('title')}{default_tag}")
                print(f"     {marker} 截止: {due_str}")
                if note:
                    print(f"     📝 {note}")
                idx += 1
            for t in completed:
                due_str, _, _, _ = parse_due(t)
                note = t.get('body', {}).get('content', '')
                print(f"  {idx}. ✅ {t.get('title')}")
                if note:
                    print(f"     📝 {note}")
                idx += 1
            print()
        else:
            if today_only:
                print(f"【{name}】 无今日待办\n")
            else:
                print(f"【{name}】 无任务\n")

def cmd_done(keyword, note=None):
    results = find_task(keyword)
    if not results:
        print(f"❌ 未找到包含「{keyword}」的任务")
        return
    for r in results:
        if r['status'] != 'completed':
            try:
                complete_task(r['list_id'], r['id'], note)
                print(f"✅ 已完成 [{r['list_name']}]: {r['title']}")
                if note:
                    print(f"   📝 备注: {note}")
            except Exception as e:
                print(f"❌ 完成失败 [{r['list_name']}]: {e}")
        else:
            print(f"ℹ️  已完成跳过: {r['title']}")

def update_task(list_id, task_id, title=None, due_str=None):
    payload = {}
    if title:
        payload["title"] = title
    if due_str:
        payload["dueDateTime"] = {"dateTime": due_str, "timeZone": "China Standard Time"}
    if not payload:
        return None
    data = json.dumps(payload).encode()
    url = f'https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{list_id}/tasks/{task_id}'
    req = urllib.request.Request(url, data=data, method='PATCH')
    req.add_header('Authorization', f'Bearer {MATON_KEY}')
    req.add_header('Content-Type', 'application/json')
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

def cmd_update(keyword, new_title=None, new_due=None):
    results = find_task(keyword)
    if not results:
        print(f"❌ 未找到包含「{keyword}」的任务")
        return
    for r in results:
        try:
            result = update_task(r['list_id'], r['id'], new_title, new_due)
            if result is None:
                print(f"⚠️  无更新内容 [{r['list_name']}]: {r['title']}")
                continue
            parts = []
            if new_title:
                parts.append(f"标题 -> {new_title}")
            if new_due:
                parts.append(f"截止 -> {new_due}")
            print(f"✅ 已更新 [{r['list_name']}]: {r['title']}")
            print(f"   🔄 {" / ".join(parts)}")
        except Exception as e:
            print(f"❌ 更新失败 [{r['list_name']}]: {e}")

def cmd_delete(keyword):
    results = find_task(keyword)
    if not results:
        print(f"❌ 未找到包含「{keyword}」的任务")
        return
    for r in results:
        try:
            delete_task(r['list_id'], r['id'])
            print(f"✅ 已删除 [{r['list_name']}]: {r['title']}")
        except Exception as e:
            print(f"❌ 删除失败 [{r['list_name']}]: {e}")

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
        title = sys.argv[4] if len(sys.argv) > 4 else None
        cmd_add(message, due_str, title)
    elif cmd == "list":
        today_only = '--today' in sys.argv
        cmd_list(today_only=today_only)
    elif cmd == "done":
        if len(sys.argv) < 3:
            print("❌ done 需要 <任务关键词>")
            sys.exit(1)
        keyword = sys.argv[2]
        note = None
        for i, arg in enumerate(sys.argv):
            if arg == "--note" and i+1 < len(sys.argv):
                note = sys.argv[i+1]
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
            if sys.argv[i] == "--title" and i+1 < len(sys.argv):
                new_title = sys.argv[i+1]
                i += 2
            elif sys.argv[i] == "--due" and i+1 < len(sys.argv):
                new_due = sys.argv[i+1]
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

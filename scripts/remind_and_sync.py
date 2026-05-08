#!/usr/bin/env python3
"""发飞书提醒 + 写Outlook To Do，一次调用两件事搞定"""
import sys, json, urllib.request, time

FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FEISHU_USER_ID = "ou_d4b39b86c8715f79b2c5b070c4e55393"
MATON_KEY = "GQWYNUq1TbTaisz_a26wKJDLEQn70PgsH3um2Kqv87a0M4qIGVynDdUwehh1U897HtIc1B9aDR07F3iLckDVKWI3hFKn4ukipSo"

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
            log_error(f"飞书发送失败: code={result.get('code')} msg={result.get('msg')} 内容: {message[:50]}")
            if retry:
                return send_feishu(message, retry=False)  # token过期就重试一次
            return False
    except Exception as e:
        log_error(f"飞书异常: {e} 内容: {message[:50]}")
        if retry:
            return send_feishu(message, retry=False)
        return False

def get_life_list():
    url = "https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {MATON_KEY}')
    resp = urllib.request.urlopen(req, timeout=15)
    lists = json.loads(resp.read()).get('value', [])
    return next((l for l in lists if l['displayName'] == 'Life'), lists[0])

def add_outlook_task(title, due_str):
    life = get_life_list()
    payload = json.dumps({
        "title": title,
        "dueDateTime": {"dateTime": due_str, "timeZone": "China Standard Time"}
    }).encode()
    task_url = f"https://gateway.maton.ai/microsoft-to-do/v1.0/me/todo/lists/{life['id']}/tasks"
    req = urllib.request.Request(task_url, data=payload, method='POST')
    req.add_header('Authorization', f'Bearer {MATON_KEY}')
    req.add_header('Content-Type', 'application/json')
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

if __name__ == "__main__":
    # Usage: remind_and_sync.py <message> <due_datetime_YYYY-MM-DDTHH:MM:SS+08:00> [title_override]
    if len(sys.argv) < 3:
        print("Usage: remind_and_sync.py <feishu_message> <due_datetime> [title]")
        sys.exit(1)

    message = sys.argv[1]
    due_str = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else message[:50]

    print(f"📱 发飞书: {message[:40]}...")
    feishu_ok = send_feishu(message)
    print(f"{'✅' if feishu_ok else '❌'} 飞书: {'成功' if feishu_ok else '失败'}")

    print(f"📋 写Outlook: {title[:40]} (截止 {due_str})...")
    try:
        result = add_outlook_task(title, due_str)
        outlook_ok = result.get('title') is not None
        print(f"{'✅' if outlook_ok else '❌'} Outlook: {'成功' if outlook_ok else '失败'}")
    except Exception as e:
        print(f"❌ Outlook: {e}")
        outlook_ok = False

    if feishu_ok and outlook_ok:
        print("🎉 两边同步完成！")
    else:
        print("⚠️ 部分失败")

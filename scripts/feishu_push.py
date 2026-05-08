#!/usr/bin/env python3
"""直接发飞书消息，不走OpenClaw cron agent session"""
import sys, json, urllib.request, time

FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FEISHU_USER_ID = "ou_d4b39b86c8715f79b2c5b070c4e55393"

def get_token():
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())["tenant_access_token"]

def send_message(token, message):
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
    return json.loads(resp.read())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: feishu_push.py <message>")
        sys.exit(1)
    
    message = sys.argv[1]
    token = get_token()
    result = send_message(token, message)
    
    if result.get("code") == 0:
        print(f"✅ 消息发送成功: {message[:30]}...")
    else:
        print(f"❌ 发送失败: {result.get('msg')}")
        sys.exit(1)

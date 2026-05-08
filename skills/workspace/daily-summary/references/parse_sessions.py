#!/usr/bin/env python3
"""
daily-summary session 解析参考脚本
用法: python3 references/parse_sessions.py [YYYYMMDD]
不传参数默认今天
"""
import json
import os
import sys
from datetime import datetime

SESSIONS_DIR = os.path.expanduser("~/.hermes/sessions")

def parse_sessions(date_prefix):
    """解析指定日期的所有 session 文件，返回按时间排序的用户消息"""
    all_files = sorted(os.listdir(SESSIONS_DIR))
    
    # 过滤当天文件，排除 cron session
    session_files = [
        f for f in all_files 
        if f.startswith(date_prefix) 
        and not f.startswith("session_cron")
        and f.endswith(".jsonl")
    ]
    
    # 也包括 weixin/飞书的 session JSON 文件（来自 session_search 里的那种）
    session_jsons = [
        f for f in all_files 
        if f.startswith(f"session_{date_prefix}")
        and not f.startswith("session_cron")
        and f.endswith(".json")
    ]
    
    all_messages = []
    
    for fname in session_files:
        fpath = os.path.join(SESSIONS_DIR, fname)
        with open(fpath, 'r', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    if d.get('role') == 'user':
                        content = str(d.get('content', ''))
                        if len(content) < 5:  # 跳过心跳等极短消息
                            continue
                        ts = d.get('timestamp', '')[:16]
                        all_messages.append((ts, content))
                except Exception:
                    pass
    
    # 按时间排序
    all_messages.sort(key=lambda x: x[0])
    return all_messages


if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_str = sys.argv[1].replace("-", "")  # 支持 2026-05-05 或 20260505
    else:
        date_str = datetime.now().strftime("%Y%m%d")
    
    msgs = parse_sessions(date_str)
    print(f"共 {len(msgs)} 条用户消息 ({date_str}):\n")
    for ts, content in msgs:
        print(f"[{ts}] {content[:100]}")
        print()

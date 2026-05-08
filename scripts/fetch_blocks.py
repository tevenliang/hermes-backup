#!/usr/bin/env python3
"""获取关注板块涨幅数据，独立脚本，5秒超时"""
import thsdk, sys, signal

def handler(signum, frame):
    print("TIMEOUT", file=sys.stderr)
    sys.exit(1)

signal.signal(signal.SIGALRM, handler)
signal.alarm(5)

try:
    codes = ["URFI885530","URFI886033","URFI885311","URFI886108"]
    with thsdk.THS() as ths:
        r = ths.market_data_block(codes, "扩展")
        if r.success:
            for item in r.data:
                c = item.get("代码","")
                chg = item.get("涨幅")
                chg5 = item.get("5日涨幅", 0)
                chg10 = item.get("10日涨幅", 0)
                print(c + "|" + str(chg) + "|" + str(chg5) + "|" + str(chg10))
        else:
            print("ERROR:" + r.error, file=sys.stderr)
except Exception as e:
    print(f"ERROR:{e}", file=sys.stderr)

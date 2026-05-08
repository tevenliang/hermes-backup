# 腾讯行情 API 参考

## 接口地址
```
https://qt.gtimg.cn/q={codes}
```
- A股指数：`sh000001`（上证）、`sz399001`（深证）、`sz399006`（创业板）、`sh000688`（科创50）
- 港股指数：`hkHSI`（恒生）、`hkHSTECH`（恒生科技）
- 纳指：`usNDX`（纳斯达克100）
- 美股个股：`usAAPL` 等

## 返回格式
```
v_sh000001="1~上证指数~4164.42~4112.16~4135.45~451194372~0~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~~20260506120400~52.26~1.27~4165.06~4129.91~4164.42/451194372/941721094624"
```

## 解析方法（Python）
```python
def _qq_quote(codes):
    url = f"https://qt.gtimg.cn/q={codes}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://gu.qq.com/"
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read().decode("gbk")
    results = {}
    for line in raw.strip().split("\n"):
        parts = line.split("~")
        if len(parts) > 35:
            raw_key = parts[0]           # v_sh000001="1
            inner = raw_key.split("=")[0] # v_sh000001
            code = inner.lstrip("v_")     # sh000001
            # 腾讯对A股指数的编码后缀（_1, _51, _100, _200）需去掉
            if code[-2:] in ("_1", "_51", "_100", "_200"):
                code = code[:-2]
            results[code] = {
                "name":    parts[1],
                "price":   parts[3],
                "preclose":parts[4],
                "open":    parts[5],
                "pct":     parts[32],    # 涨跌幅%
            }
    return results
```

## 关键字段索引
| 索引 | 字段 | 说明 |
|------|------|------|
| [1] | name | 名称 |
| [3] | price | 最新价 |
| [4] | preclose | 昨收价 |
| [5] | open | 今开 |
| [32] | pct | 涨跌幅% |

## 常见错误
- **key 含引号**：`v_sh000001="1` 不能直接 `strip('"')`，因为中间还有 `"`。正确做法：`split('=')[0]` 取 `v_sh000001`，再 `lstrip('v_')`。
- **A股指数后缀**：`sh000001_1` 是腾讯内部编码，需要去掉尾部 `_1` 才能得到标准代码 `sh000001`。
- **编码**：返回是 GBK 编码，必须 decode("gbk") 不能用 utf-8。

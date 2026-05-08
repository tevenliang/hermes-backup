# CHANGELOG - daily-finance

## v1.5 (2026-04-28)
- 新增：市场本地缓存机制（cache/market_cache_YYYY-MM-DD.json），当日运行结束后将7个指数的收盘价和涨跌幅写入缓存，明日运行时自动作为"昨日数据"回填，解决 HKHSI/HKHSTECH/IXIC 历史数据无法从 API 获取的问题
- 缓存文件按日期存储在 skills/daily-finance/cache/ 目录

## v1.4 (2026-04-28)
- 修改：大盘指数字段调整为：指数名称、代码、昨收价、昨涨跌幅、最新价、最新涨跌幅
- 新增：A股指数（上证/深证/创业板/科创50）接入东方财富历史K线接口（push2his.eastmoney.com），获取真实昨日涨跌幅
- 港股（恒生/恒生科技）和纳斯达克：历史数据暂无法从免费 API 获取，今日数据作为明日缓存

## v1.3 (2026-04-28)
- 修改：基金净数字段调整为：基金代码、基金名称、昨收净值、昨涨跌幅、最新净值、最新涨跌幅
- 新增：基金净值查询接入东方财富历史NAV接口（api.fund.eastmoney.com/f10/lsjz），获取真实昨日确认净值和涨跌幅，替代原来天天基金API的估算值
- 修复：timedelta 未 import 导致 `_get_last_nav` 函数抛异常被 except 吞没，昨日数据始终显示 "-" 的 bug

## v1.2 (2026-04-28)
- 新增：finflow 数据自动校验层 `sanitize_finfow_data()`，changePercent 与 (price-preclose)/preclose 偏差 >1% 时自动修正，从源头防止港股数据错误
- 修改：大盘指数和基金持仓行情统一走 sanitize 校验

## v1.1 (2026-04-28)
- 修改：大盘指数涨跌幅计算改为基于 price/preclose 推导，避免 finflow 返回错误数据（如 HKHSTECH 返回 -228 而非 -2.28，HKHSI 返回 -95 而非 -0.95）
- 修改：基金持仓股票行情同样改为 price/preclose 推导，避免港股股票（德昌电机控股、中芯国际等）涨跌幅出现 -100 倍错误

## v1.0 (2026-04-10)
- 初始版本

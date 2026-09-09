# 聚宽量化交易平台 API 知识库

## 文档概述

本文档是聚宽（JoinQuant）量化交易平台 API 的完整使用指南，旨在为 AI 助手和量化交易开发者提供全面的技术参考。聚宽是中国领先的量化交易平台，采用 Python 语言，为投资者提供丰富的金融数据 API 和完整的策略开发环境。

---

## 第一部分：平台基础与核心概念

### 1.1 平台简介

聚宽量化交易平台是中国专业的量化交易研究平台，提供完整的 Python 编程环境用于量化策略开发。平台支持股票、基金、ETF、期货等多种金融产品的策略回测和模拟交易。

**核心特色功能：**

- 提供丰富的历史数据和实时市场数据
- 具备完整的 Python 量化开发环境
- 内置专业的回测引擎和风险分析工具
- 支持多种金融产品交易
- 提供因子库和技术分析工具

### 1.2 核心概念解释

在开始学习 API 之前，需要理解以下核心概念：

| 概念 | 说明 |
|------|------|
| context | 策略上下文对象，包含策略运行状态、账户信息、持仓等 |
| security | 证券代码，如 '000001.XSHE' 表示平安银行 |
| g | 全局变量对象，用于存储策略参数和状态 |
| data | 当前时点的市场数据对象 |
| order | 订单对象，包含下单相关信息 |

### 1.3 证券代码规范

聚宽平台使用标准化的证券代码格式，投资者在进行量化策略开发时必须正确使用各种证券代码：

**A股股票代码格式：**

```python
# 深交所股票
'000001.XSHE'  # 平安银行

# 上交所股票
'600000.XSHG'  # 浦发银行
```

**指数代码格式：**

```python
'000300.XSHG'  # 沪深300指数
'000905.XSHG'  # 中证500指数
'399006.XSHE'  # 创业板指数
```

**ETF基金代码格式：**

```python
'510300.XSHG'  # 沪深300ETF
'159915.XSHE'  # 创业板ETF
```

**期货代码格式（主力合约）：**

```python
'RB9999.XSGE'  # 螺纹钢主力合约
```

### 1.4 策略生命周期框架

每个聚宽策略都遵循标准的生命周期模式，包含四个核心函数：

```python
from jqdata import *

def initialize(context):
    """
    策略初始化函数，只在策略开始时运行一次
    用于设置基准、手续费、运行时间等
    """
    pass

def before_trading_start(context):
    """每日开盘前运行（可选）"""
    pass

def handle_data(context, data):
    """主要交易逻辑，按设定频率运行（可选）"""
    pass

def after_trading_end(context):
    """每日收盘后运行（可选）"""
    pass
```

**函数执行顺序：**

1. `initialize(context)` - 策略启动时仅执行一次
2. `before_trading_start(context)` - 每日开盘前执行
3. `handle_data(context, data)` - 每个数据周期执行
4. `after_trading_end(context)` - 每日收盘后执行

---

## 第二部分：核心配置 API

### 2.1 基准设置

**API 函数：** `set_benchmark(security)`

设置策略基准指数，用于性能比较和收益评估。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 证券代码，支持股票、指数等 | '000300.XSHG' |

```python
# 设置沪深300为基准
set_benchmark('000300.XSHG')

# 其他常用基准指数
set_benchmark('000905.XSHG')  # 中证500指数
set_benchmark('399006.XSHE')  # 创业板指数
set_benchmark('000001.XSHG')  # 上证综指
set_benchmark('399101.XSHE')  # 深证成指
```

### 2.2 系统选项配置

**API 函数：** `set_option(option_name, value)`

配置策略运行的系统参数，用于优化回测精度。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值 | 默认值 |
|--------|------|------|------|--------|--------|
| option_name | str | 是 | 配置项名称 | 见下方列表 | - |
| value | - | 是 | 配置值 | 根据option_name而定 | - |

**可用配置项列表：**

| 配置项名称 | 值类型 | 说明 | 推荐值 |
|------------|--------|------|--------|
| use_real_price | bool | 是否使用真实价格交易，避免回测偏差 | True |
| avoid_future_data | bool | 是否避免未来数据泄露 | True |
| order_volume_ratio | float | 单笔订单不超过5分钟成交量的比例 | 0.25 |
| match_with_order_book | bool | 是否开启盘口撮合，提高回测精度 | True |
| float_percentage_precision | int | 持仓权重计算精度 | 8 |
| disable_cache | bool | 是否禁用数据缓存 | False |

```python
# 重要配置（强烈推荐设置）
set_option('use_real_price', True)        # 使用真实价格交易，避免回测偏差
set_option('avoid_future_data', True)     # 避免未来数据泄露

# 可选配置
set_option('order_volume_ratio', 0.25)    # 成交量比例限制
set_option('match_with_order_book', True) # 开启盘口撮合
```

### 2.3 交易成本设置

**API 函数：** `set_order_cost(OrderCost(**kwargs), type)`

设置不同类型证券的交易成本，包括印花税、佣金等费用。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 取值范围 |
|--------|------|------|------|----------|
| OrderCost对象 | object | 是 | 交易成本配置对象 | - |
| type | str | 是 | 证券类型 | 'stock', 'fund', 'futures', 'index', 'bond' |

**OrderCost 对象参数：**

| 参数名 | 类型 | 必填 | 说明 | 取值示例 |
|--------|------|------|------|----------|
| open_tax | float | 是 | 买入印花税（比例） | 0（买入通常为0） |
| close_tax | float | 是 | 卖出印花税（比例） | 0.001（千分之1） |
| open_commission | float | 是 | 买入佣金（比例） | 0.0003（万分之3） |
| close_commission | float | 是 | 卖出佣金（比例） | 0.0003（万分之3） |
| close_today_commission | float | 否 | 平今仓佣金（期货专用） | 0.0002 |
| min_commission | float | 否 | 最低佣金（元） | 5 |

```python
# 股票交易成本设置
set_order_cost(OrderCost(
    open_tax=0,                    # 买入印花税（通常为0）
    close_tax=0.001,              # 卖出印花税（千分之1）
    open_commission=0.0003,       # 买入佣金（万分之3）
    close_commission=0.0003,      # 卖出佣金（万分之3）
    close_today_commission=0,     # 平今仓佣金
    min_commission=5              # 最低佣金5元
), type='stock')

# ETF/基金交易成本设置（无印花税）
set_order_cost(OrderCost(
    open_tax=0,
    close_tax=0,                  # ETF无印花税
    open_commission=0.0003,
    close_commission=0.0003,
    min_commission=5
), type='fund')

# 期货交易成本设置
set_order_cost(OrderCost(
    open_tax=0,
    close_tax=0,
    open_commission=0.0002,       # 期货佣金相对较低
    close_commission=0.0002,
    close_today_commission=0.0002,
    min_commission=5
), type='futures')
```

### 2.4 滑点设置

**API 函数：** `set_slippage(slippage_type)`

设置交易滑点，模拟实际交易中的价格冲击成本。

**滑点类型详解：**

| 滑点类型 | 说明 | 参数说明 |
|----------|------|----------|
| FixedSlippage | 固定滑点，按照固定比例滑点 | slippage: float类型，如0.002表示0.2% |
| PriceRelatedSlippage | 价格相关滑点，按照成交价的比例滑点 | slippage: float类型，如0.002表示0.2% |
| StepRelatedSlippage | 步长相关滑点，按照价格最小变动单位的整数倍滑点 | slippage: int类型，如2表示2个最小变动单位 |

```python
# 固定滑点（推荐）
set_slippage(FixedSlippage(0.002))        # 固定0.2%滑点

# 价格相关滑点
set_slippage(PriceRelatedSlippage(0.002)) # 价格相关0.2%滑点

# 零滑点（理想情况，不建议在实际策略中使用）
set_slippage(FixedSlippage(0))

# 步长相关滑点（主要用于期货）
set_slippage(StepRelatedSlippage(2))      # 2个最小变动单位
```

### 2.5 完整初始化示例

```python
def initialize(context):
    """完整的策略初始化示例"""
    # 设置基准
    set_benchmark('000300.XSHG')

    # 系统配置
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_option('order_volume_ratio', 0.25)

    # 交易成本
    set_order_cost(OrderCost(
        open_tax=0,
        close_tax=0.001,
        open_commission=0.0003,
        close_commission=0.0003,
        min_commission=5
    ), type='stock')

    # 滑点设置
    set_slippage(FixedSlippage(0.002))

    # 策略参数
    g.stock_num = 10              # 持仓股票数量
    g.rebalance_period = 20       # 调仓周期（天）
    g.benchmark = '000300.XSHG'   # 基准指数

    # 初始化变量
    g.current_positions = []      # 当前持仓
    g.target_stocks = []          # 目标股票池
    g.trade_count = 0             # 交易次数统计

    # 设置定时运行
    run_daily(before_market_open, time='9:00')
    run_daily(trade_stocks, time='9:30')
    run_daily(after_market_close, time='15:30')
```

---

## 第三部分：数据获取 API 详解

### 3.1 价格数据获取

#### 3.1.1 get_price() - 核心价格数据 API

**API 函数：** `get_price(security, start_date, end_date, frequency, fields, skip_paused, fq, count, panel, fill_paused)`

获取历史价格数据的主要函数，支持日线、分钟线等多种数据频率。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| security | str/list | 是 | 股票代码或代码列表 | '000001.XSHE' 或 ['000001.XSHE', '000002.XSHE'] |
| start_date | str/datetime | 否 | 开始日期 | '2023-01-01' 或 datetime(2023,1,1) |
| end_date | str/datetime | 否 | 结束日期 | '2023-12-31' |
| frequency | str | 否 | 数据频率 | 'daily'/'1d', '1m', '5m', '15m', '30m', '60m' |
| fields | list | 否 | 数据字段列表 | ['open', 'close', 'high', 'low', 'volume', 'money'] |
| skip_paused | bool | 否 | 是否跳过停牌日 | True/False，默认False |
| fq | str | 否 | 复权类型 | 'pre'（前复权，推荐）, 'post'（后复权）, None（不复权） |
| count | int | 否 | 获取最近N个数据 | 与start_date/end_date二选一 |
| panel | bool | 否 | 返回格式 | False（返回DataFrame，推荐）, True（返回Panel） |
| fill_paused | bool | 否 | 是否填充停牌日数据 | True/False |

**可用字段列表：**

| 字段名 | 说明 | 数据类型 |
|--------|------|----------|
| open | 开盘价 | float |
| close | 收盘价 | float |
| high | 最高价 | float |
| low | 最低价 | float |
| volume | 成交量 | float |
| money | 成交额 | float |
| pre_close | 前收盘价 | float |
| paused | 是否停牌 | bool |

```python
# 基础用法 - 获取单只股票数据
df = get_price(
    security='000001.XSHE',
    start_date='2023-01-01',
    end_date='2023-12-31',
    frequency='daily',
    fields=['open', 'close', 'high', 'low', 'volume', 'money'],
    skip_paused=True,
    fq='pre'
)

# 使用count参数获取最近N天数据
df = get_price('000001.XSHE', count=30, fields=['close', 'volume'])

# 获取多只股票数据
stock_list = ['000001.XSHE', '000002.XSHE', '600000.XSHG']
df = get_price(stock_list, count=20, frequency='daily', panel=False)

# 获取分钟级数据
df = get_price('000001.XSHE', count=240, frequency='1m', fields=['close'])

# 获取不同频率数据
df_5m = get_price('000001.XSHE', count=100, frequency='5m')
df_15m = get_price('000001.XSHE', count=50, frequency='15m')
df_1h = get_price('000001.XSHE', count=30, frequency='60m')
```

#### 3.1.2 attribute_history() - 简化历史数据获取

**API 函数：** `attribute_history(security, count, unit, fields, skip_paused, df, fq)`

获取单只股票历史数据的便捷函数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| security | str | 是 | 股票代码 | '000001.XSHE' |
| count | int | 是 | 获取数据的个数 | 20（获取20个数据） |
| unit | str | 是 | 时间单位 | '1d'（日）, '1m'（1分钟）, '5m', '15m', '30m', '60m' |
| fields | list | 否 | 数据字段列表 | ['open', 'close', 'high', 'low', 'volume'] |
| skip_paused | bool | 否 | 是否跳过停牌日 | True/False |
| df | bool | 否 | 是否返回DataFrame格式 | True（返回DataFrame）, False（返回dict） |
| fq | str | 否 | 复权类型 | 'pre', 'post', None |

```python
# 获取最近20天的收盘价
closes = attribute_history('000001.XSHE', 20, '1d', ['close'])

# 获取完整OHLCV数据
data = attribute_history(
    security='000001.XSHE',
    count=30,
    unit='1d',
    fields=['open', 'close', 'high', 'low', 'volume'],
    skip_paused=True,
    df=True,
    fq='pre'
)

# 计算技术指标
ma5 = closes['close'].rolling(5).mean()    # 5日均线
ma20 = closes['close'].rolling(20).mean()  # 20日均线
```

#### 3.1.3 history() - 多股票历史数据

**API 函数：** `history(count, unit, field, security_list, df, skip_paused)`

获取多只股票指定字段的历史数据。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| count | int | 是 | 获取数据的个数 | 10 |
| unit | str | 是 | 时间单位 | '1d', '1m', '5m', '15m', '30m', '60m' |
| field | str | 是 | 数据字段名 | 'close', 'open', 'volume'等 |
| security_list | list | 是 | 股票代码列表 | ['000001.XSHE', '000002.XSHE'] |
| df | bool | 否 | 是否返回DataFrame格式 | True（默认） |
| skip_paused | bool | 否 | 是否跳过停牌日 | True/False |

```python
# 获取多只股票的收盘价
stock_list = ['000001.XSHE', '000002.XSHE', '600000.XSHG']
prices = history(
    count=10,
    unit='1d',
    field='close',
    security_list=stock_list,
    df=True
)

# 获取实时数据（在handle_data中使用）
def handle_data(context, data):
    current_prices = history(1, '1m', 'close', g.stock_pool, df=False)
    for stock in g.stock_pool:
        print(f"{stock}: {current_prices[stock][-1]}")
```

### 3.2 实时数据获取

#### 3.2.1 get_current_data() - 当前市场数据

**API 函数：** `get_current_data()`

获取所有股票的实时市场数据，返回一个字典，key为股票代码。

**返回对象属性详解：**

| 属性名 | 类型 | 说明 |
|--------|------|------|
| last_price | float | 最新价格 |
| day_open | float | 开盘价 |
| high_limit | float | 涨停价 |
| low_limit | float | 跌停价 |
| paused | bool | 是否停牌 |
| is_st | bool | 是否ST股票 |
| name | str | 股票名称 |
| pre_close | float | 前收盘价 |
| bid_price | list | 买一价到买五价 |
| ask_price | list | 卖一价到卖五价 |
| bid_vol | list | 买一量到买五量 |
| ask_vol | list | 卖一量到卖五量 |

```python
def check_market_status(context):
    """检查市场状态示例"""
    current_data = get_current_data()

    for stock in g.stock_pool:
        stock_data = current_data[stock]

        # 基础价格信息
        last_price = stock_data.last_price    # 最新价格
        day_open = stock_data.day_open        # 开盘价
        high_limit = stock_data.high_limit    # 涨停价
        low_limit = stock_data.low_limit      # 跌停价

        # 状态信息
        is_paused = stock_data.paused         # 是否停牌
        is_st = stock_data.is_st              # 是否ST股票
        name = stock_data.name                # 股票名称

        # 交易决策
        if not is_paused and not is_st:
            if last_price < high_limit and last_price > low_limit:
                log.info(f"{name}({stock}): 价格 {last_price}, 可交易")
            else:
                log.warning(f"{name}({stock}): 触及涨跌停，无法交易")
```

### 3.3 基本面数据获取

#### 3.3.1 get_fundamentals() - 财务数据查询

**API 函数：** `get_fundamentals(query_object, date, statDate)`

获取上市公司基本面数据的核心函数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| query_object | query对象 | 是 | 查询对象，由query()函数构建 | query(valuation.code, ...) |
| date | str/datetime | 否 | 查询日期 | '2023-12-31' |
| statDate | str | 否 | 财报统计期 | '2023q3', '2023' |

**常用基本面数据表：**

| 表名 | 说明 | 常用字段 |
|------|------|----------|
| valuation | 估值相关 | code, market_cap, pe_ratio, pb_ratio, ps_ratio, pcf_ratio |
| indicator | 财务指标 | code, roe, roa, eps, gross_profit_margin, net_profit_margin |
| income | 利润表 | code, total_operating_revenue, net_profit, operating_profit |
| balance | 资产负债表 | code, total_assets, total_liability, current_assets |
| cash_flow | 现金流量表 | code, net_operate_cash_flow, net_invest_cash_flow |

**valution表完整字段：**

| 字段名 | 说明 | 数据类型 |
|--------|------|----------|
| code | 股票代码 | str |
| pe_ratio | 市盈率 | float |
| pb_ratio | 市净率 | float |
| ps_ratio | 市销率 | float |
| pcf_ratio | 市现率 | float |
| market_cap | 总市值（亿元） | float |
| circulating_market_cap | 流通市值（亿元） | float |
| capitalization | 总股本（万股） | float |
| circulating_cap | 流通股本（万股） | float |

**indicator表完整字段：**

| 字段名 | 说明 | 数据类型 |
|--------|------|----------|
| code | 股票代码 | str |
| roe | 净资产收益率 | float |
| roa | 总资产收益率 | float |
| eps | 每股收益（元） | float |
| gross_profit_margin | 毛利率 | float |
| net_profit_margin | 净利率 | float |
| operating_profit_margin | 营业利润率 | float |
| debt_to_assets | 资产负债率 | float |
| current_ratio | 流动比率 | float |
| quick_ratio | 速动比率 | float |
| total_asset_turnover | 资产周转率 | float |

```python
# 基础财务数据查询
def get_fundamental_data(context):
    """获取基本面数据示例"""
    q = query(
        # 基础信息
        valuation.code,
        valuation.market_cap,
        valuation.circulating_market_cap,

        # 估值指标
        valuation.pe_ratio,
        valuation.pb_ratio,
        valuation.ps_ratio,
        valuation.pcf_ratio,

        # 盈利指标
        indicator.roe,
        indicator.roa,
        indicator.eps,
        indicator.operating_profit,

        # 财务数据
        income.total_operating_revenue,
        income.net_profit,
        balance.total_assets,
        balance.total_liability,
        cash_flow.net_operate_cash_flow
    ).filter(
        valuation.market_cap.between(50, 2000),
        valuation.pe_ratio > 0,
        valuation.pe_ratio < 50,
        indicator.roe > 0.1,
        income.net_profit > 0
    ).order_by(
        valuation.market_cap.asc()
    ).limit(100)

    df = get_fundamentals(q, date=context.previous_date)
    return df
```

#### 3.3.2 get_valuation() - 估值数据

**API 函数：** `get_valuation(security, start_date, end_date, fields)`

获取股票估值数据的时间序列。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| security | str/list | 是 | 股票代码或列表 | '000001.XSHE' 或列表 |
| start_date | str | 否 | 开始日期 | '2023-01-01' |
| end_date | str | 否 | 结束日期 | '2023-12-31' |
| fields | list | 否 | 返回字段列表 | ['market_cap', 'pe_ratio', 'pb_ratio'] |

```python
# 获取单只股票估值历史
valuation_data = get_valuation(
    security='000001.XSHE',
    start_date='2023-01-01',
    end_date='2023-12-31',
    fields=['market_cap', 'pe_ratio', 'pb_ratio', 'turnover_ratio']
)

# 获取多只股票当前估值
stocks = ['000001.XSHE', '000002.XSHE']
current_valuation = get_valuation(
    security=stocks,
    start_date=context.previous_date,
    end_date=context.previous_date
)
```

### 3.4 股票基础信息

#### 3.4.1 get_all_securities() - 获取证券列表

**API 函数：** `get_all_securities(types, date)`

获取所有或指定类型的证券信息。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| types | list | 是 | 证券类型列表 | ['stock'], ['etf'], ['fund'], ['bond'] |
| date | str | 否 | 查询日期，返回该日期已上市的证券 | '2023-12-31' |

**证券类型说明：**

| 类型值 | 说明 |
|--------|------|
| stock | 股票 |
| etf | 交易所交易基金 |
| fund | 普通基金 |
| bond | 债券 |
| index | 指数 |

```python
# 获取所有股票
all_stocks = get_all_securities(types=['stock'])
stock_codes = list(all_stocks.index)

# 获取不同类型证券
etfs = get_all_securities(types=['etf'])
funds = get_all_securities(types=['fund'])
bonds = get_all_securities(types=['bond'])

# 获取指定日期的证券列表
stocks_2023 = get_all_securities(types=['stock'], date='2023-12-31')
```

#### 3.4.2 get_index_stocks() - 指数成分股

**API 函数：** `get_index_stocks(index_symbol, date)`

获取指数的成分股列表。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| index_symbol | str | 是 | 指数代码 | '000300.XSHG' |
| date | str | 否 | 查询日期，获取该日期的成分股 | '2023-01-01' |

```python
# 主要指数成分股
hs300_stocks = get_index_stocks('000300.XSHG')        # 沪深300
csi500_stocks = get_index_stocks('000905.XSHG')       # 中证500
sz50_stocks = get_index_stocks('000016.XSHG')         # 上证50
gem_stocks = get_index_stocks('399006.XSHE')          # 创业板指

# 获取历史成分股
hs300_2023 = get_index_stocks('000300.XSHG', date='2023-01-01')
```

#### 3.4.3 get_security_info() - 证券详细信息

**API 函数：** `get_security_info(security, date)`

获取单只证券的详细信息。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 证券代码 | '000001.XSHE' |
| date | str | 否 | 查询日期 | '2023-12-31' |

**返回对象属性：**

| 属性名 | 类型 | 说明 |
|--------|------|------|
| display_name | str | 证券名称 |
| name | str | 证券简称 |
| start_date | datetime | 上市/成立日期 |
| end_date | datetime | 退市/到期日期（未退市为None） |
| type | str | 证券类型 |
| code | str | 证券代码 |
| underlying_symbol | str | 标的代码（期权/期货用） |

```python
# 获取股票基本信息
stock_info = get_security_info('000001.XSHE')

print(f"股票名称: {stock_info.display_name}")
print(f"上市日期: {stock_info.start_date}")
print(f"退市日期: {stock_info.end_date}")
print(f"证券类型: {stock_info.type}")
```

### 3.5 其他重要数据 API

#### 3.5.1 get_trade_days() - 交易日历

**API 函数：** `get_trade_days(start_date, end_date, count)`

获取交易日历信息。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| start_date | str | 否 | 开始日期，与count二选一 | '2023-01-01' |
| end_date | str | 否 | 结束日期 | '2023-12-31' |
| count | int | 否 | 获取最近N个交易日 | 252（一年交易日） |

```python
# 获取指定期间的交易日
trade_days = get_trade_days(start_date='2023-01-01', end_date='2023-12-31')

# 获取最近N个交易日
recent_days = get_trade_days(end_date='2023-12-31', count=252)

# 实用函数
def is_trading_day(date):
    """判断是否为交易日"""
    trade_days = get_trade_days(start_date=date, end_date=date)
    return len(trade_days) > 0

def get_previous_trading_day(date, n=1):
    """获取前N个交易日"""
    trade_days = get_trade_days(end_date=date, count=n+1)
    return trade_days[-1] if len(trade_days) > n else None
```

#### 3.5.2 get_extras() - 特殊数据

**API 函数：** `get_extras(info, security_list, start_date, end_date, df, count)`

获取股票的特殊属性数据。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| info | str/list | 是 | 获取的信息类型 | 'is_st', 'paused', 'high_limit', 'low_limit' |
| security_list | list | 是 | 股票代码列表 | ['000001.XSHE'] |
| start_date | str | 否 | 开始日期 | '2023-01-01' |
| end_date | str | 否 | 结束日期 | '2023-12-31' |
| df | bool | 否 | 是否返回DataFrame | True/False |
| count | int | 否 | 获取最近N个数据 | 1 |

**可用info值：**

| info值 | 说明 | 返回类型 |
|--------|------|----------|
| is_st | 是否ST股票 | bool |
| paused | 是否停牌 | bool |
| high_limit | 涨停价 | float |
| low_limit | 跌停价 | float |
| pre_close | 前收盘价 | float |
| factor | 复权因子 | float |
| st_flags | ST标志详情 | str |

```python
# 获取ST股票信息
st_data = get_extras('is_st', stock_list, count=1, end_date=context.previous_date)

# 获取停牌信息
paused_data = get_extras('paused', stock_list, count=1, end_date=context.previous_date)

# 获取涨跌停价格
limit_data = get_extras(['high_limit', 'low_limit'], stock_list, count=1, end_date=context.previous_date)
```

---

## 第四部分：交易执行 API 指南

### 4.1 基础下单函数

#### 4.1.1 order() - 基础下单

**API 函数：** `order(security, amount, style, side)`

最基础的下单函数，按股数下单。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 股票代码 | '000001.XSHE' |
| amount | int | 是 | 买入股数（正数买入，负数卖出） | 1000（买入1000股）, -500（卖出500股） |
| style | OrderStyle | 否 | 订单类型 | MarketOrderStyle(), LimitOrderStyle(12.50) |
| side | str | 否 | 交易方向 | 'long'（买入）, 'short'（卖出） |

**OrderStyle类型：**

| 类型 | 说明 | 参数 |
|------|------|------|
| MarketOrderStyle | 市价单 | 无参数 |
| LimitOrderStyle | 限价单 | price: 限价价格 |

```python
# 基础用法
order('000001.XSHE', 1000)                    # 买入1000股
order('000001.XSHE', -500)                    # 卖出500股

# 使用不同订单类型
order('000001.XSHE', 1000, MarketOrderStyle())      # 市价单
order('000001.XSHE', 1000, LimitOrderStyle(12.50))  # 限价单
```

#### 4.1.2 order_value() - 按金额下单

**API 函数：** `order_value(security, value, style)`

按金额下单，系统自动计算股数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 股票代码 | '000001.XSHE' |
| value | float | 是 | 交易金额（元），正数买入，负数卖出 | 10000（买入1万元）, -5000（卖出5000元） |
| style | OrderStyle | 否 | 订单类型 | MarketOrderStyle() |

```python
# 按金额买入
order_value('000001.XSHE', 10000)   # 买入1万元的股票
order_value('000001.XSHE', -5000)   # 卖出5000元的股票

# 动态资金分配
def allocate_funds(context, stock_list):
    if not stock_list:
        return

    available_cash = context.portfolio.available_cash
    cash_per_stock = available_cash * 0.8 / len(stock_list)

    for stock in stock_list:
        order_value(stock, cash_per_stock)
```

#### 4.1.3 order_target() - 目标持仓下单

**API 函数：** `order_target(security, amount, style)`

调整持仓到目标数量。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 股票代码 | '000001.XSHE' |
| amount | int | 是 | 目标持仓股数，0表示清仓 | 1000（持仓到1000股）, 0（清仓） |
| style | OrderStyle | 否 | 订单类型 | MarketOrderStyle() |

```python
# 调整到目标股数
order_target('000001.XSHE', 1000)   # 持仓调整到1000股
order_target('000001.XSHE', 0)      # 清仓
```

#### 4.1.4 order_target_value() - 目标市值下单

**API 函数：** `order_target_value(security, value, style)`

调整持仓到目标市值，推荐使用。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 股票代码 | '000001.XSHE' |
| value | float | 是 | 目标持仓市值（元），0表示清仓 | 20000（持仓到2万元）, 0（清仓） |
| style | OrderStyle | 否 | 订单类型 | MarketOrderStyle() |

```python
# 调整到目标市值
order_target_value('000001.XSHE', 20000)   # 持仓调整到2万元
order_target_value('000001.XSHE', 0)        # 清仓

# 等权重投资组合
def equal_weight_portfolio(context, stock_list):
    if not stock_list:
        return

    total_value = context.portfolio.total_value
    target_value_per_stock = total_value * 0.9 / len(stock_list)

    for stock in context.portfolio.positions:
        if stock not in stock_list:
            order_target_value(stock, 0)

    for stock in stock_list:
        order_target_value(stock, target_value_per_stock)
```

#### 4.1.5 order_target_percent() - 按比例下单

**API 函数：** `order_target_percent(security, percent, style)`

按总资产比例调整持仓。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| security | str | 是 | 股票代码 | '000001.XSHE' |
| percent | float | 是 | 目标持仓比例（0-1之间） | 0.1（持仓到10%）, 0（清仓） |
| style | OrderStyle | 否 | 订单类型 | MarketOrderStyle() |

```python
# 按比例调整持仓
order_target_percent('000001.XSHE', 0.1)   # 调整到总资产的10%
order_target_percent('000001.XSHE', 0.05)   # 调整到总资产的5%
```

### 4.2 高级下单功能

#### 4.2.1 安全下单函数

```python
def safe_order_target_value(security, value, max_retry=3):
    """安全的目标市值下单函数"""
    current_data = get_current_data()

    # 基础检查
    if current_data[security].paused:
        log.warning(f"{security} 停牌，无法交易")
        return None

    if current_data[security].is_st:
        log.warning(f"{security} ST股票，建议谨慎交易")

    # 涨跌停检查
    last_price = current_data[security].last_price
    high_limit = current_data[security].high_limit
    low_limit = current_data[security].low_limit

    if value > 0:
        if last_price >= high_limit:
            log.warning(f"{security} 涨停，无法买入")
            return None
    else:
        if last_price <= low_limit:
            log.warning(f"{security} 跌停，可能无法卖出")

    # 执行下单
    for attempt in range(max_retry):
        try:
            order_obj = order_target_value(security, value)
            if order_obj:
                return order_obj
        except Exception as e:
            log.error(f"下单异常 {security}: {str(e)}")

    return None
```

### 4.3 订单管理

#### 4.3.1 订单查询

**API 函数：** `get_orders()`, `get_open_orders()`, `get_trades()`

**参数详解：**

| API函数 | 说明 | 返回类型 |
|---------|------|----------|
| get_orders() | 获取所有历史订单 | dict |
| get_open_orders() | 获取未完成订单 | dict |
| get_trades() | 获取所有成交记录 | dict |

**Order对象属性：**

| 属性名 | 类型 | 说明 |
|--------|------|------|
| id | str | 订单ID |
| security | str | 股票代码 |
| side | str | 交易方向 |
| price | float | 委托价格 |
| amount | int | 委托数量 |
| filled | int | 成交数量 |
| status | OrderStatus | 订单状态 |
| add_time | datetime | 委托时间 |
| avg_price | float | 成交均价 |

**订单状态说明：**

| 状态值 | 说明 |
|--------|------|
| OrderStatus.open | 订单已提交，等待成交 |
| OrderStatus.filled | 订单已完全成交 |
| OrderStatus.canceled | 订单已取消 |
| OrderStatus.rejected | 订单被拒绝 |
| OrderStatus.held | 订单部分成交 |

```python
def manage_orders(context):
    """订单管理示例"""
    # 获取所有订单
    all_orders = get_orders()

    # 获取未完成订单
    open_orders = get_open_orders()

    # 检查订单状态
    for order_id, order_obj in open_orders.items():
        log.info(f"订单 {order_id}:")
        log.info(f"  股票: {order_obj.security}")
        log.info(f"  委托数量: {order_obj.amount}")
        log.info(f"  成交数量: {order_obj.filled}")
        log.info(f"  订单状态: {order_obj.status}")
```

### 4.4 仓位管理

#### 4.4.1 仓位信息查询

**Portfolio对象属性：**

| 属性名 | 类型 | 说明 |
|--------|------|------|
| total_value | float | 总资产 |
| available_cash | float | 可用现金 |
| positions_value | float | 持仓市值 |
| starting_cash | float | 初始资金 |
| returns | float | 当日收益率 |
| daily_returns | float | 当日收益率（别名） |

**Position对象属性：**

| 属性名 | 类型 | 说明 |
|--------|------|------|
| security | str | 股票代码 |
| total_amount | int | 总持仓数量 |
| closeable_amount | int | 可卖出数量 |
| avg_cost | float | 平均成本 |
| price | float | 当前价格 |
| value | float | 持仓市值 |
| init_time | datetime | 建仓时间 |

```python
def analyze_portfolio(context):
    """投资组合分析"""
    portfolio = context.portfolio

    # 基础信息
    log.info(f"总资产: {portfolio.total_value:.2f}")
    log.info(f"可用现金: {portfolio.available_cash:.2f}")
    log.info(f"持仓市值: {portfolio.positions_value:.2f}")
    log.info(f"当日收益: {portfolio.daily_returns:.4f}")
    log.info(f"累计收益率: {(portfolio.total_value / portfolio.starting_cash - 1):.4f}")

    # 持仓详情
    for stock, position in portfolio.positions.items():
        profit = position.value - position.avg_cost * position.total_amount
        profit_rate = (position.price / position.avg_cost - 1) * 100
        weight = position.value / portfolio.total_value

        log.info(f"{stock}: 持仓{position.total_amount}股, "
                f"成本{position.avg_cost:.2f}, "
                f"现价{position.price:.2f}, "
                f"盈亏{profit_rate:.2f}%")
```

---

## 第五部分：时间调度管理

### 5.1 定时执行 API

#### 5.1.1 run_daily() - 每日执行

**API 函数：** `run_daily(func, time, reference_security)`

设置每日定时执行的函数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| func | function | 是 | 要执行的函数名 | before_market_open |
| time | str | 是 | 执行时间 | 见下方说明 |
| reference_security | str | 否 | 参考证券（用于确定交易日） | '000300.XSHG' |

**time参数可选值：**

| 值 | 说明 |
|----|------|
| 'before_open' | 开盘前（9:00） |
| 'open' | 开盘时（9:30） |
| 'after_close' | 收盘后（15:30） |
| 'HH:MM' | 具体时间，如'09:30', '14:50' |
| 'every_bar' | 按K线周期执行（分钟K线专用） |

```python
def initialize(context):
    """定时任务设置示例"""
    # 开盘前准备工作
    run_daily(before_market_open, time='09:00')
    run_daily(prepare_data, time='before_open')

    # 开盘后交易执行
    run_daily(trade_stocks, time='09:30')
    run_daily(monitor_positions, time='10:30')

    # 分钟K线策略触发
    run_daily(trade_strategy, time='every_bar')

    # 收盘前最后检查
    run_daily(final_check, time='14:50')

    # 收盘后分析
    run_daily(after_market_close, time='after_close')
```

#### 5.1.2 run_weekly() - 每周执行

**API 函数：** `run_weekly(func, weekday, time, reference_security)`

设置每周定时执行的函数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| func | function | 是 | 要执行的函数名 | weekly_rebalance |
| weekday | int | 是 | 星期几执行 | 1-5（周一至周五） |
| time | str | 是 | 执行时间 | 'HH:MM'或预定义值 |
| reference_security | str | 否 | 参考证券 | '000300.XSHG' |

```python
def initialize(context):
    """每周执行示例"""
    # 每周一开盘时重新选股和调仓
    run_weekly(weekly_rebalance, weekday=1, time='09:30')

    # 每周三进行风险检查
    run_weekly(risk_assessment, weekday=3, time='14:00')

    # 每周五生成周报
    run_weekly(weekly_report, weekday=5, time='after_close')

    # weekday参数：1=周一, 2=周二, 3=周三, 4=周四, 5=周五
```

#### 5.1.3 run_monthly() - 每月执行

**API 函数：** `run_monthly(func, monthday, time, reference_security)`

设置每月定时执行的函数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值 |
|--------|------|------|------|--------|
| func | function | 是 | 要执行的函数名 | monthly_rebalance |
| monthday | int | 是 | 每月第几日执行 | 1-31或-1（最后一日） |
| time | str | 是 | 执行时间 | 'HH:MM'或预定义值 |
| reference_security | str | 否 | 参考证券 | '000300.XSHG' |

```python
def initialize(context):
    """每月执行示例"""
    # 每月第一个交易日进行大调仓
    run_monthly(monthly_major_rebalance, monthday=1, time='09:30')

    # 每月15日进行策略回顾
    run_monthly(strategy_review, monthday=15, time='after_close')

    # 每月最后一个交易日生成月报
    run_monthly(monthly_report, monthday=-1, time='15:30')

    # monthday参数：1-31表示每月第几日，-1表示最后一日
```

### 5.2 时间管理工具

#### 5.2.1 context时间属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| current_dt | datetime | 当前时间（回测/模拟时间） |
| previous_date | date | 前一个交易日 |
| current_date | date | 当前日期 |
| current_time | time | 当前时间（不含日期） |

```python
def time_management_example(context):
    """时间管理示例"""
    # 获取当前时间信息
    current_time = context.current_dt
    previous_date = context.previous_date

    # 时间格式转换
    current_date = current_time.date()
    current_time_only = current_time.time()

    # 判断交易时段
    if current_time_only < pd.Timestamp('09:30').time():
        log.info("开盘前")
    elif current_time_only < pd.Timestamp('11:30').time():
        log.info("上午交易时段")
    elif current_time_only < pd.Timestamp('13:00').time():
        log.info("午间休息")
    elif current_time_only < pd.Timestamp('15:00').time():
        log.info("下午交易时段")
    else:
        log.info("收盘后")

def is_month_end(context):
    """判断是否为月末"""
    current_date = context.current_dt.date()
    next_trade_days = get_trade_days(start_date=current_date, count=2)

    if len(next_trade_days) < 2:
        return True

    next_day = next_trade_days[-1]
    return current_date.month != next_day.month
```

---

## 第六部分：因子分析与技术指标

### 6.1 JQFactor 因子库

#### 6.1.1 get_factor_values() - 因子数据获取

**API 函数：** `get_factor_values(securities, factors, start_date, end_date, count)`

聚宽内置因子库的核心函数。

**参数详解：**

| 参数名 | 类型 | 必填 | 说明 | 可选值/示例 |
|--------|------|------|------|-------------|
| securities | list | 是 | 股票代码列表 | ['000001.XSHE'] |
| factors | list | 是 | 因子名称列表 | ['ROE', 'PE'] |
| start_date | str | 否 | 开始日期 | '2023-01-01' |
| end_date | str | 否 | 结束日期 | '2023-12-31' |
| count | int | 否 | 获取最近N期数据 | 20（与日期参数二选一） |

**常用因子分类：**

| 分类 | 因子名称 | 说明 |
|------|----------|------|
| 估值因子 | PE, PB, PS, PCF, PEG, EV_EBITDA | 市盈率、市净率等 |
| 盈利因子 | ROE, ROA, gross_profit_margin, net_profit_margin, operating_profit_margin, EBITDA_margin | 净资产收益率等 |
| 成长因子 | sales_growth, net_profit_growth_rate, total_asset_growth_rate, operating_revenue_growth_rate, eps_growth | 营收增长率等 |
| 质量因子 | current_ratio, quick_ratio, debt_to_equity, asset_turnover, inventory_turnover | 流动比率等 |
| 技术因子 | RSI, MACD, BIAS, momentum_1m, momentum_3m, volatility_1m | 技术指标 |
| 规模因子 | market_cap, circulating_market_cap, total_market_value | 市值因子 |

```python
from jqfactor import get_factor_values

# 基础用法
def get_factor_data_example(context, stock_list):
    """因子数据获取示例"""

    # 获取单个因子
    factor_data = get_factor_values(
        securities=stock_list,
        factors=['ROE'],
        start_date='2023-01-01',
        end_date='2023-12-31'
    )

    # 获取多个因子
    multi_factor_data = get_factor_values(
        securities=stock_list,
        factors=['ROE', 'ROA', 'PE', 'PB', 'market_cap'],
        end_date=context.previous_date,
        count=1
    )

    return multi_factor_data
```

### 6.2 技术指标计算

#### 6.2.1 使用 talib 库

**主要函数说明：**

| 函数 | 说明 | 关键参数 |
|------|------|----------|
| SMA(data, timeperiod) | 简单移动平均 | timeperiod: 周期 |
| EMA(data, timeperiod) | 指数移动平均 | timeperiod: 周期 |
| RSI(data, timeperiod) | 相对强弱指数 | timeperiod: 周期，默认14 |
| MACD(data, fastperiod, slowperiod, signalperiod) | MACD指标 | fastperiod: 快线周期, slowperiod: 慢线周期, signalperiod: 信号线周期 |
| BBANDS(data, timeperiod, nbdevup, nbdevdn) | 布林带 | timeperiod: 周期, nbdevup: 上轨标准差倍数 |
| ATR(high, low, close, timeperiod) | 平均真实波幅 | timeperiod: 周期 |
| STOCH(high, low, close, fastk_period, slowk_period, slowd_period) | 随机指标KDJ | fastk_period: K周期, slowk_period: D周期 |
| OBV(close, volume) | 能量潮 | 无特殊参数 |
| AD(high, low, close, volume) | 累计派踪线 | 无特殊参数 |

```python
import talib

def technical_indicators_talib(context, security):
    """使用talib计算技术指标"""

    # 获取价格数据
    price_data = attribute_history(security, 60, '1d',
                                 ['open', 'high', 'low', 'close', 'volume'])

    open_prices = price_data['open'].values
    high_prices = price_data['high'].values
    low_prices = price_data['low'].values
    close_prices = price_data['close'].values
    volume = price_data['volume'].values

    indicators = {}

    # 移动平均线
    indicators['MA5'] = talib.SMA(close_prices, timeperiod=5)[-1]
    indicators['MA20'] = talib.SMA(close_prices, timeperiod=20)[-1]
    indicators['MA60'] = talib.SMA(close_prices, timeperiod=60)[-1]

    # RSI指标
    indicators['RSI'] = talib.RSI(close_prices, timeperiod=14)[-1]

    # MACD指标
    macd, macd_signal, macd_hist = talib.MACD(close_prices)
    indicators['MACD'] = macd[-1]
    indicators['MACD_SIGNAL'] = macd_signal[-1]
    indicators['MACD_HIST'] = macd_hist[-1]

    # 布林带
    bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices)
    indicators['BB_UPPER'] = bb_upper[-1]
    indicators['BB_MIDDLE'] = bb_middle[-1]
    indicators['BB_LOWER'] = bb_lower[-1]

    # ATR指标
    indicators['ATR'] = talib.ATR(high_prices, low_prices, close_prices, timeperiod=14)[-1]

    return indicators
```

#### 6.2.2 使用 jqlib 技术分析

**主要函数说明：**

| 函数 | 说明 | 关键参数 |
|------|------|----------|
| MA(security, check_date, timeperiod, unit) | 移动平均线 | timeperiod: 周期, unit: 时间单位 |
| MACD(security, check_date, SHORT, LONG, MID, unit) | MACD指标 | SHORT/LONG/MID: 快慢线周期 |
| RSI(security, check_date, N1, unit) | RSI指标 | N1: 周期 |
| KDJ(security, check_date, N, M1, M2, unit) | KDJ指标 | N: RSV周期, M1/M2: K/D周期 |
| Bollinger_Bands(security, check_date, timeperiod, nbdevup, nbdevdn, unit) | 布林带 | timeperiod: 周期 |
| VR(security, check_date, N, unit) | 成交量变异率 | N: 周期 |

```python
from jqlib.technical_analysis import *

def technical_indicators_jqlib(context, stock_list):
    """使用jqlib计算技术指标"""

    check_date = context.previous_date
    indicators_data = {}

    for security in stock_list:
        try:
            indicators = {}

            # 移动平均线
            ma_result = MA(security, check_date=check_date, timeperiod=20, unit='1d')
            indicators['MA20'] = ma_result.get(security, 0)

            # MACD
            macd_result = MACD(security, check_date=check_date, SHORT=12, LONG=26, MID=9, unit='1d')
            indicators['MACD'] = macd_result[0].get(security, 0)

            # RSI
            rsi_result = RSI(security, check_date=check_date, N1=14, unit='1d')
            indicators['RSI'] = rsi_result.get(security, 50)

            # KDJ
            kdj_result = KDJ(security, check_date=check_date, N=9, M1=3, M2=3, unit='1d')
            indicators['KDJ_K'] = kdj_result[0].get(security, 50)
            indicators['KDJ_D'] = kdj_result[1].get(security, 50)

            indicators_data[security] = indicators

        except Exception as e:
            continue

    return indicators_data
```

---

## 第七部分：数据过滤与风险管理

### 7.1 股票过滤函数

#### 7.1.1 基础过滤器

```python
def comprehensive_stock_filter(context, stock_list):
    """综合股票过滤函数"""
    current_data = get_current_data()
    filtered_stocks = []

    for stock in stock_list:
        stock_data = current_data[stock]

        # 基础过滤条件
        if (not stock_data.paused and
            not stock_data.is_st and
            'ST' not in stock_data.name and
            '*' not in stock_data.name and
            '退' not in stock_data.name):

            # 涨跌停过滤
            if (stock_data.low_limit < stock_data.last_price < stock_data.high_limit):
                # 成交量过滤
                volume_data = attribute_history(stock, 5, '1d', ['volume'])
                if len(volume_data) >= 5:
                    avg_volume = volume_data['volume'].mean()
                    if avg_volume > 1000000:
                        filtered_stocks.append(stock)

    return filtered_stocks
```

#### 7.1.2 财务健康度过滤

```python
def filter_by_financial_health(context, stock_list):
    """基于财务健康度过滤"""
    q = query(
        valuation.code,
        valuation.pe_ratio,
        valuation.pb_ratio,
        indicator.roe,
        indicator.current_ratio,
        indicator.quick_ratio,
        balance.total_liability,
        balance.total_assets
    ).filter(
        valuation.code.in_(stock_list)
    )

    df = get_fundamentals(q, date=context.previous_date)

    healthy_stocks = df[
        (df['pe_ratio'] > 0) & (df['pe_ratio'] < 50) &
        (df['pb_ratio'] > 0) & (df['pb_ratio'] < 8) &
        (df['roe'] > 0.05) &
        (df['current_ratio'] > 1.2) &
        (df['quick_ratio'] > 0.8) &
        (df['total_liability'] / df['total_assets'] < 0.7)
    ]

    return list(healthy_stocks['code'])
```

### 7.2 行业和板块分析

```python
def get_industry_distribution(stock_list):
    """获取股票的行业分布"""
    industry_dict = {}

    for stock in stock_list:
        try:
            info = get_security_info(stock)
            industry = getattr(info, 'industry', '未知')

            if industry not in industry_dict:
                industry_dict[industry] = []
            industry_dict[industry].append(stock)
        except:
            continue

    return industry_dict

def limit_industry_concentration(stock_list, max_stocks_per_industry=3):
    """限制单个行业的股票数量"""
    industry_dist = get_industry_distribution(stock_list)

    balanced_stocks = []
    for industry, stocks in industry_dist.items():
        selected_stocks = stocks[:max_stocks_per_industry]
        balanced_stocks.extend(selected_stocks)

    return balanced_stocks
```

### 7.3 风险预警系统

```python
def risk_warning_system(context):
    """风险预警系统"""
    warnings = []

    # 1. 仓位集中度检查
    total_value = context.portfolio.total_value
    positions = context.portfolio.positions

    for stock, position in positions.items():
        weight = position.value / total_value
        if weight > 0.15:
            warnings.append(f"持仓集中度警告：{stock} 权重 {weight:.2%}")

    # 2. 回撤检查
    current_drawdown = calculate_current_drawdown(context)
    if current_drawdown > 0.1:
        warnings.append(f"回撤警告：当前回撤 {current_drawdown:.2%}")

    # 3. 波动率检查
    volatility = calculate_portfolio_volatility(context)
    if volatility > 0.3:
        warnings.append(f"波动率警告：当前年化波动率 {volatility:.2%}")

    for warning in warnings:
        log.warning(warning)

    return len(warnings) > 0

def calculate_current_drawdown(context):
    """计算当前回撤"""
    if not hasattr(g, 'max_value_history'):
        g.max_value_history = context.portfolio.total_value

    current_value = context.portfolio.total_value
    g.max_value_history = max(g.max_value_history, current_value)

    drawdown = (g.max_value_history - current_value) / g.max_value_history
    return drawdown

def calculate_portfolio_volatility(context, days=20):
    """计算组合波动率"""
    if not hasattr(g, 'return_history'):
        g.return_history = []

    daily_return = context.portfolio.returns
    g.return_history.append(daily_return)

    if len(g.return_history) > days:
        g.return_history.pop(0)

    if len(g.return_history) >= days:
        returns_array = np.array(g.return_history)
        volatility = np.std(returns_array) * np.sqrt(252)
        return volatility

    return 0
```

---

## 第八部分：实战策略开发

### 8.1 海龟交易策略

```python
def initialize(context):
    """海龟交易策略初始化"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)

    # 海龟策略参数
    g.turtle_params = {
        'entry_period': 20,      # 入场突破周期
        'exit_period': 10,       # 出场突破周期
        'atr_period': 20,        # ATR计算周期
        'risk_per_trade': 0.02   # 每笔交易风险比例
    }

    g.stock_pool = get_index_stocks('000300.XSHG')[:50]
    run_daily(turtle_strategy, time='9:30')

def turtle_strategy(context):
    """海龟策略主逻辑"""
    for stock in g.stock_pool:
        try:
            data = get_price(stock, count=g.turtle_params['entry_period']+1,
                           end_date=context.previous_date,
                           fields=['high', 'low', 'close'])

            if len(data) < g.turtle_params['entry_period']:
                continue

            entry_signal = check_entry_signal(stock, data)
            exit_signal = check_exit_signal(stock, data)

            execute_turtle_trade(context, stock, data, entry_signal, exit_signal)

        except Exception as e:
            continue

def check_entry_signal(stock, data):
    """检查入场信号"""
    current_price = data['high'].iloc[-1]
    highest_high = data['high'].iloc[:-1].max()
    return current_price > highest_high

def check_exit_signal(stock, data):
    """检查出场信号"""
    current_price = data['low'].iloc[-1]
    lowest_low = data['low'].iloc[-g.turtle_params['exit_period']:].min()
    return current_price < lowest_low

def execute_turtle_trade(context, stock, data, entry_signal, exit_signal):
    """执行海龟交易"""
    current_position = context.portfolio.positions.get(stock)

    if entry_signal and not current_position:
        atr = calculate_atr(data, g.turtle_params['atr_period'])
        if atr > 0:
            position_value = calculate_position_size(context, stock, data, atr)
            if position_value > 1000:
                order_target_value(stock, position_value)

    elif exit_signal and current_position:
        order_target_value(stock, 0)
```

### 8.2 布林带均值回归策略

```python
def initialize(context):
    """布林带均值回归策略"""
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)

    g.bollinger_params = {
        'period': 20,
        'std_multiplier': 2.0,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70
    }

    g.stock_pool = get_index_stocks('000300.XSHG')
    g.max_positions = 10

    run_daily(bollinger_strategy, time='9:30')

def calculate_bollinger_bands(prices, period, std_multiplier):
    """计算布林带"""
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + (std * std_multiplier)
    lower = middle - (std * std_multiplier)
    return upper.iloc[-1], middle.iloc[-1], lower.iloc[-1]

def calculate_rsi(prices, period):
    """计算RSI指标"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def generate_bollinger_signals(stock, current_price, bb_upper, bb_lower, rsi):
    """生成布林带交易信号"""
    signals = {'buy': False, 'sell': False}

    if current_price <= bb_lower and rsi <= g.bollinger_params['rsi_oversold']:
        signals['buy'] = True
    elif current_price >= bb_upper and rsi >= g.bollinger_params['rsi_overbought']:
        signals['sell'] = True

    return signals
```

---

## 第九部分：最佳实践与优化

### 9.1 策略评估与监控

```python
def performance_monitor(context):
    """策略表现监控"""
    record_strategy_metrics(context)
    risk_check_result = comprehensive_risk_check(context)

    if risk_check_result['high_risk']:
        emergency_risk_control(context, risk_check_result)

def record_strategy_metrics(context):
    """记录策略指标"""
    portfolio = context.portfolio

    total_value = portfolio.total_value
    daily_return = portfolio.returns
    positions_count = len(portfolio.positions)
    cash_ratio = portfolio.available_cash / total_value

    record(
        总资产=total_value,
        日收益率=daily_return,
        持仓数量=positions_count,
        现金比例=cash_ratio
    )

def calculate_max_drawdown(context):
    """计算最大回撤"""
    if not hasattr(g, 'net_value_history'):
        g.net_value_history = []

    current_net_value = context.portfolio.total_value / context.portfolio.starting_cash
    g.net_value_history.append(current_net_value)

    if len(g.net_value_history) > 252:
        g.net_value_history.pop(0)

    if len(g.net_value_history) < 2:
        return 0

    peak = g.net_value_history[0]
    max_drawdown = 0

    for value in g.net_value_history:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak
        max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown

def calculate_annual_metrics(context):
    """计算年化指标"""
    if not hasattr(g, 'daily_returns'):
        g.daily_returns = []

    g.daily_returns.append(context.portfolio.returns)

    if len(g.daily_returns) > 252:
        g.daily_returns.pop(0)

    if len(g.daily_returns) < 20:
        return 0, 0

    mean_return = np.mean(g.daily_returns)
    annual_return = (1 + mean_return) ** 252 - 1
    volatility = np.std(g.daily_returns) * np.sqrt(252)

    risk_free_rate = 0.03
    sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

    return annual_return, sharpe_ratio
```

### 9.2 应急风险控制

```python
def emergency_risk_control(context, risk_result):
    """应急风险控制"""
    log.warning("触发应急风险控制措施")
    log.warning(f"风险因素: {risk_result['risk_factors']}")

    if risk_result['risk_level'] == 'high':
        reduce_positions(context, 0.5)
        log.warning("执行50%减仓操作")
    elif risk_result['risk_level'] == 'medium':
        reduce_positions(context, 0.3)
        log.warning("执行30%减仓操作")

    record(风控触发=1)

def reduce_positions(context, reduce_ratio):
    """减仓操作"""
    for stock, position in context.portfolio.positions.items():
        current_value = position.value
        target_value = current_value * (1 - reduce_ratio)
        order_target_value(stock, target_value)
```

---

## 附录：API 完整参数速查表

### A.1 数据获取 API 完整参数

| API 函数 | 必填参数 | 可选参数 | 返回类型 |
|----------|----------|----------|----------|
| get_price() | security | start_date, end_date, frequency, fields, skip_paused, fq, count, panel, fill_paused | DataFrame |
| attribute_history() | security, count, unit | fields, skip_paused, df, fq | DataFrame/dict |
| history() | count, unit, field, security_list | df, skip_paused | DataFrame |
| get_current_data() | 无 | 无 | dict |
| get_fundamentals() | query_object | date, statDate | DataFrame |
| get_valuation() | security | start_date, end_date, fields | DataFrame |
| get_all_securities() | types | date | DataFrame |
| get_index_stocks() | index_symbol | date | list |
| get_security_info() | security | date | object |
| get_trade_days() | 无 | start_date, end_date, count | DatetimeIndex |
| get_extras() | info, security_list | start_date, end_date, df, count | DataFrame/dict |

### A.2 交易执行 API 完整参数

| API 函数 | 必填参数 | 可选参数 | 说明 |
|----------|----------|----------|------|
| order() | security, amount | style, side | 按股数下单 |
| order_value() | security, value | style | 按金额下单 |
| order_target() | security, amount | style | 目标持仓下单 |
| order_target_value() | security, value | style | 目标市值下单 |
| order_target_percent() | security, percent | style | 比例下单 |
| get_orders() | 无 | 无 | dict |
| get_open_orders() | 无 | 无 | dict |
| get_trades() | 无 | 无 | dict |

### A.3 定时任务 API 完整参数

| API 函数 | 必填参数 | 可选参数 |
|----------|----------|----------|
| run_daily() | func, time | reference_security |
| run_weekly() | func, weekday, time | reference_security |
| run_monthly() | func, monthday, time | reference_security |

### A.4 配置 API 完整参数

| API 函数 | 必填参数 | 可选参数 |
|----------|----------|----------|
| set_benchmark() | security | 无 |
| set_option() | option_name, value | 无 |
| set_order_cost() | OrderCost对象, type | 无 |
| set_slippage() | slippage对象 | 无 |

### A.5 OrderCost 对象完整参数

| 参数 | 类型 | 说明 | 股票示例 | 期货示例 |
|------|------|------|----------|----------|
| open_tax | float | 买入印花税 | 0 | 0 |
| close_tax | float | 卖出印花税 | 0.001 | 0 |
| open_commission | float | 买入佣金 | 0.0003 | 0.0002 |
| close_commission | float | 卖出佣金 | 0.0003 | 0.0002 |
| close_today_commission | float | 平今仓佣金 | 0 | 0.0002 |
| min_commission | float | 最低佣金 | 5 | 5 |

### A.6 get_current_data() 返回对象完整属性

| 属性 | 类型 | 说明 |
|------|------|------|
| last_price | float | 最新价格 |
| day_open | float | 开盘价 |
| high_limit | float | 涨停价 |
| low_limit | float | 跌停价 |
| paused | bool | 是否停牌 |
| is_st | bool | 是否ST股票 |
| name | str | 股票名称 |
| pre_close | float | 前收盘价 |
| bid_price | list | 买一价到买五价 |
| ask_price | list | 卖一价到卖五价 |
| bid_vol | list | 买一量到买五量 |
| ask_vol | list | 卖一量到卖五量 |

### A.7 context 对象关键属性

| 属性 | 类型 | 说明 |
|------|------|------|
| current_dt | datetime | 当前时间 |
| previous_date | date | 前一交易日 |
| portfolio | Portfolio | 投资组合信息 |
| current_date | date | 当前日期 |
| current_time | time | 当前时间 |

### A.8 Portfolio 对象属性

| 属性 | 类型 | 说明 |
|------|------|------|
| total_value | float | 总资产 |
| available_cash | float | 可用现金 |
| positions_value | float | 持仓市值 |
| starting_cash | float | 初始资金 |
| returns | float | 当日收益率 |
| positions | dict | 持仓字典 |

### A.9 Position 对象属性

| 属性 | 类型 | 说明 |
|------|------|------|
| security | str | 股票代码 |
| total_amount | int | 总持仓数量 |
| closeable_amount | int | 可卖出数量 |
| avg_cost | float | 平均成本 |
| price | float | 当前价格 |
| value | float | 持仓市值 |
| init_time | datetime | 建仓时间 |

---

## 附录：因子库完整字段说明

### B.1 valuation 表完整字段

| 字段名 | 说明 | 数据类型 | 单位 |
|--------|------|----------|------|
| code | 股票代码 | str | - |
| pe_ratio | 市盈率 | float | - |
| pb_ratio | 市净率 | float | - |
| ps_ratio | 市销率 | float | - |
| pcf_ratio | 市现率 | float | - |
| market_cap | 总市值 | float | 亿元 |
| circulating_market_cap | 流通市值 | float | 亿元 |
| capitalization | 总股本 | float | 万股 |
| circulating_cap | 流通股本 | float | 万股 |

### B.2 indicator 表完整字段

| 字段名 | 说明 | 数据类型 | 单位 |
|--------|------|----------|------|
| code | 股票代码 | str | - |
| roe | 净资产收益率 | float | - |
| roa | 总资产收益率 | float | - |
| eps | 每股收益 | float | 元 |
| gross_profit_margin | 毛利率 | float | - |
| net_profit_margin | 净利率 | float | - |
| operating_profit_margin | 营业利润率 | float | - |
| debt_to_assets | 资产负债率 | float | - |
| current_ratio | 流动比率 | float | - |
| quick_ratio | 速动比率 | float | - |
| total_asset_turnover | 资产周转率 | float | - |
| inventory_turnover | 存货周转率 | float | - |
| inc_revenue_year_on_year | 营收同比增长率 | float | - |
| inc_net_profit_year_on_year | 净利润同比增长率 | float | - |

### B.3 income 表完整字段

| 字段名 | 说明 | 数据类型 | 单位 |
|--------|------|----------|------|
| code | 股票代码 | str | - |
| total_operating_revenue | 营业总收入 | float | 元 |
| operating_revenue | 营业收入 | float | 元 |
| total_operating_cost | 营业总成本 | float | 元 |
| operating_profit | 营业利润 | float | 元 |
| net_profit | 净利润 | float | 元 |
| basic_eps | 基本每股收益 | float | 元 |
| diluted_eps | 稀释每股收益 | float | 元 |

### B.4 balance 表完整字段

| 字段名 | 说明 | 数据类型 | 单位 |
|--------|------|----------|------|
| code | 股票代码 | str | - |
| total_assets | 总资产 | float | 元 |
| total_liability | 总负债 | float | 元 |
| total_equity | 股东权益 | float | 元 |
| current_assets | 流动资产 | float | 元 |
| fixed_assets | 固定资产 | float | 元 |
| accounts_receivable | 应收账款 | float | 元 |
| accounts_payable | 应付账款 | float | 元 |

### B.5 cash_flow 表完整字段

| 字段名 | 说明 | 数据类型 | 单位 |
|--------|------|----------|------|
| code | 股票代码 | str | - |
| net_operate_cash_flow | 经营活动现金流净额 | float | 元 |
| net_invest_cash_flow | 投资活动现金流净额 | float | 元 |
| net_finance_cash_flow | 筹资活动现金流净额 | float | 元 |
| cash_equivalents | 货币资金 | float | 元 |
| free_cash_flow | 自由现金流 | float | 元 |

---

## 文档信息

**文档版本：** 2.0（完整参数版）
**创建日期：** 2024年
**适用平台：** 聚宽量化交易平台
**Python 版本：** Python 3.x

---

*本文档由 MiniMax Agent 整理编写，用于 AI 知识库存储和量化交易开发者参考使用。*

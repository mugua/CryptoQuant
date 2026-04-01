# 📈 CryptoQuant 策略文档

## 目录

- [策略基类](#策略基类)
- [内置策略](#内置策略)
  - [均线交叉策略](#均线交叉策略ma-cross)
  - [RSI 策略](#rsi-策略)
  - [布林带策略](#布林带策略)
  - [网格交易策略](#网格交易策略)
  - [DCA 定投策略](#dca-定投策略)
- [自定义策略开发](#自定义策略开发)
- [回测指南](#回测指南)

---

## 策略基类

所有策略都继承自 `StrategyBase` 抽象基类（`backend/engine/strategy_base.py`）。

### 核心属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | 策略名称 |
| `version` | str | 版本号（语义化版本） |
| `description` | str | 策略描述 |
| `parameters` | dict | 可调参数（初始化时传入） |
| `_capital` | float | 当前可用资金 |
| `_initial_capital` | float | 初始资金 |
| `_positions` | Dict[str, Position] | 持仓记录 |
| `_orders` | List[OrderRecord] | 交易记录 |
| `_signals` | List[Signal] | 信号记录 |

### 抽象方法（必须实现）

```python
def initialize(self) -> None:
    """策略初始化，创建指标缓冲区。在策略开始运行前调用一次。"""
    ...

def on_candle(self, candle: pd.Series) -> Optional[Signal]:
    """处理每根 K 线。
    
    参数:
        candle: 包含 open, high, low, close, volume 的 Series
    
    返回:
        Signal 对象（BUY/SELL/HOLD/CLOSE）或 None
    """
    ...

def on_tick(self, tick: Dict) -> Optional[Signal]:
    """处理实时 Tick 数据（可选实现）。"""
    ...
```

### 内置交易方法

```python
def buy(self, symbol: str, quantity: float, price: float, 
        commission_rate: float = 0.001) -> Signal:
    """生成买入信号并更新持仓。"""

def sell(self, symbol: str, quantity: float, price: float, 
         commission_rate: float = 0.001) -> Signal:
    """生成卖出信号并结算盈亏。"""
```

### 绩效查询

```python
def get_performance_metrics(self) -> dict:
    """返回策略绩效指标。"""
    # 返回: total_trades, winning_trades, losing_trades, win_rate,
    #       total_pnl, gross_profit, gross_loss, profit_factor,
    #       current_capital, total_return_pct
```

### 信号类型

| 信号 | 说明 |
|------|------|
| `BUY` | 买入开仓 |
| `SELL` | 卖出平仓 |
| `HOLD` | 持仓不动 |
| `CLOSE` | 平仓 |

---

## 内置策略

### 均线交叉策略（MA Cross）

**文件：** `backend/strategies/moving_average_cross.py`  
**类名：** `MovingAverageCross`

#### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `fast_period` | 9 | 快速均线周期 |
| `slow_period` | 21 | 慢速均线周期 |
| `signal_type` | `"ema"` | 均线类型：`"ema"` 或 `"sma"` |
| `atr_period` | 14 | ATR 周期（用于仓位计算） |
| `atr_multiplier` | 1.0 | ATR 乘数（止损距离） |
| `risk_per_trade_pct` | 0.01 | 每笔交易风险比例（占资金） |

#### 信号逻辑

```
买入信号（金叉）：
  条件: 快速均线上穿慢速均线 AND 当前无持仓
  仓位: 基于 ATR 的风险仓位计算
        quantity = (capital × risk_per_trade_pct) / (ATR × atr_multiplier)

卖出信号（死叉）：
  条件: 快速均线下穿慢速均线 AND 当前有持仓
  操作: 全部平仓
```

#### 工作原理

1. **初始化**：创建收盘价和高/低/收盘价缓冲区
2. **每根 K 线**：
   - 更新价格缓冲区
   - 计算快速和慢速均线（SMA 或 EMA）
   - 计算 ATR
   - 检测均线交叉
   - 金叉时根据 ATR 计算仓位并买入
   - 死叉时全仓卖出

---

### RSI 策略

**文件：** `backend/strategies/rsi_strategy.py`  
**类名：** `RSIStrategy`

#### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `rsi_period` | 14 | RSI 计算周期 |
| `oversold` | 30 | 超卖阈值（触发买入） |
| `overbought` | 70 | 超买阈值（触发卖出） |
| `exit_rsi_buy` | 50 | 多头退出 RSI 阈值（中线） |
| `exit_rsi_sell` | 50 | 空头退出 RSI 阈值（中线） |
| `risk_per_trade_pct` | 0.95 | 资金利用比例 |

#### 信号逻辑

```
买入信号（超卖反转）：
  条件: RSI < oversold AND 当前无持仓
  仓位: capital × risk_per_trade_pct / close_price

卖出信号：
  条件 1: RSI > overbought（超买）
  条件 2: RSI 从下方上穿 exit_rsi_buy（中线退出）
  操作: 全部平仓
```

#### 工作原理

1. **初始化**：创建收盘价缓冲区和前一根 RSI 值记录
2. **每根 K 线**：
   - 更新收盘价序列
   - 计算当前 RSI 值
   - RSI 进入超卖区域时买入
   - RSI 进入超买区域 或 RSI 上穿中线时卖出
   - 记录前一根 RSI 用于交叉检测

---

### 布林带策略

**文件：** `backend/strategies/bollinger_bands.py`  
**类名：** `BollingerBandsStrategy`

#### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `period` | 20 | 布林带 SMA 周期 |
| `std_dev` | 2.0 | 标准差倍数 |
| `squeeze_threshold` | 0.1 | 挤压检测阈值（带宽/中轨比值） |
| `risk_per_trade_pct` | 0.95 | 资金利用比例 |

#### 信号逻辑

```
挤压检测：
  band_width = (upper - lower) / middle
  is_squeeze = band_width < squeeze_threshold

买入信号（均值回归）：
  条件: 价格 ≤ 下轨 AND 处于挤压状态 AND 当前无持仓
  仓位: capital × risk_per_trade_pct / close_price
  止损: 中轨价格

卖出信号：
  条件 1: 价格 ≥ 上轨（目标到达）
  条件 2: 价格 < 中轨（止损）
  操作: 全部平仓
```

#### 工作原理

1. **初始化**：创建收盘价缓冲区
2. **每根 K 线**：
   - 更新收盘价序列
   - 计算布林带三轨（上轨、中轨、下轨）
   - 计算带宽，判断是否处于挤压状态
   - 挤压状态下价格触及下轨时买入（预期均值回归）
   - 价格触及上轨或跌破中轨时卖出

---

### 网格交易策略

**文件：** `backend/strategies/grid_trading.py`  
**类名：** `GridTradingStrategy`

#### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `grid_count` | 10 | 网格层数 |
| `upper_price` | 0 | 网格上界价格 |
| `lower_price` | 0 | 网格下界价格 |
| `investment_per_grid` | 100 | 每格投入金额（USDT） |

#### 网格机制

```
网格构建：
  grid_step = (upper_price - lower_price) / grid_count
  grid_levels = [lower_price + i × grid_step  for i in range(grid_count + 1)]

  示例（BTC 40000-50000，10 格）：
  [40000, 41000, 42000, ..., 49000, 50000]

买入逻辑：
  当价格 ≤ 某网格层级 AND 该层级未被填充：
    买入数量 = investment_per_grid / current_price
    标记该层级为"已买入"

卖出逻辑：
  当价格 ≥ 某网格层级的上一层级 AND 该层级已持仓：
    卖出该层级全部持仓
    累计网格利润
    标记该层级为"已卖出"
```

#### 工作原理

1. **初始化**：根据上下界和网格数计算所有网格价位，初始化网格状态追踪器
2. **每根 K 线**：
   - 从最低价位向上遍历网格
   - 价格低于网格价位时买入（如未持仓）
   - 价格高于卖出目标（上一层级）时卖出（如已持仓）
   - 每次完成买卖循环时累计利润
3. **特点**：震荡市中自动低买高卖，适合区间震荡行情

---

### DCA 定投策略

**文件：** `backend/strategies/dca_strategy.py`  
**类名：** `DCAStrategy`

#### 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `investment_amount` | 100 | 每次定投金额（USDT） |
| `interval_days` | 7 | 定投间隔天数 |
| `max_positions` | 10 | 最大累积仓位数 |
| `take_profit_pct` | 20 | 止盈比例（%） |
| `drop_trigger_pct` | -5 | 跌幅触发加仓比例（%） |

#### 定时机制

```
定时定投：
  每隔 interval_days 天，投入 investment_amount USDT
  买入数量 = investment_amount / current_price
  前提: 累积仓位数 < max_positions

跌幅加仓：
  当价格较上次买入下跌 drop_trigger_pct% 时，额外加仓一次
  前提: 累积仓位数 < max_positions

止盈退出：
  当总持仓收益达到 take_profit_pct% 时，卖出全部持仓
  收益计算: (current_value - total_invested) / total_invested × 100
```

#### 工作原理

1. **初始化**：记录上次买入时间和价格，初始化累计投入和持仓数量
2. **每根 K 线**：
   - 检查是否到达定投日期（间隔天数）
   - 到期则执行定额买入
   - 检查价格是否较上次买入下跌超过阈值
   - 满足跌幅条件则额外加仓
   - 计算当前总收益率
   - 收益率达到止盈线则全部卖出
3. **特点**：适合长期看涨标的，通过定期投入平滑成本

---

## 自定义策略开发

### 步骤 1：创建策略文件

在 `backend/strategies/` 目录下创建新文件，如 `my_strategy.py`：

```python
from typing import Dict, Optional
import pandas as pd

from engine.strategy_base import StrategyBase, Signal
from engine.indicators import SMA, RSI, ATR


class MyStrategy(StrategyBase):
    """自定义策略示例"""

    name = "my_strategy"
    version = "1.0.0"
    description = "我的自定义策略"

    def __init__(self, parameters: dict = None):
        super().__init__(parameters or {})
        # 自定义参数，提供默认值
        self.lookback = self.parameters.get("lookback", 20)
        self.threshold = self.parameters.get("threshold", 0.02)

    def initialize(self) -> None:
        """初始化指标缓冲区"""
        self.closes = pd.Series(dtype=float)
        self.highs = pd.Series(dtype=float)
        self.lows = pd.Series(dtype=float)

    def on_candle(self, candle: pd.Series) -> Optional[Signal]:
        """处理每根 K 线"""
        # 更新数据
        self.closes = pd.concat([
            self.closes, 
            pd.Series([candle["close"]])
        ]).reset_index(drop=True)
        
        # 等待足够数据
        if len(self.closes) < self.lookback:
            return None
        
        # 计算指标
        sma = SMA(self.closes, self.lookback)
        current_price = candle["close"]
        current_sma = sma.iloc[-1]
        
        # 生成信号
        position = self.get_position(candle.get("symbol", "BTC/USDT"))
        
        if current_price < current_sma * (1 - self.threshold):
            if position is None or position.quantity == 0:
                quantity = self._capital * 0.95 / current_price
                return self.buy(
                    symbol=candle.get("symbol", "BTC/USDT"),
                    quantity=quantity,
                    price=current_price
                )
        
        elif current_price > current_sma * (1 + self.threshold):
            if position and position.quantity > 0:
                return self.sell(
                    symbol=candle.get("symbol", "BTC/USDT"),
                    quantity=position.quantity,
                    price=current_price
                )
        
        return None

    def on_tick(self, tick: Dict) -> Optional[Signal]:
        """处理实时 Tick（可选）"""
        return None
```

### 步骤 2：注册策略

在 `backend/strategies/__init__.py` 中导入新策略：

```python
from .my_strategy import MyStrategy
```

### 步骤 3：回测验证

通过回测接口测试策略表现：

```bash
curl -X POST http://localhost:8000/api/v1/backtest/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "timeframe": "1h",
    "symbol": "BTC/USDT",
    "strategy_type": "MY_STRATEGY",
    "parameters": {
      "lookback": 20,
      "threshold": 0.02
    },
    "initial_capital": 10000,
    "commission_rate": 0.001
  }'
```

### 开发建议

1. **参数化设计**：所有可调参数通过 `parameters` 字典传入，方便回测优化
2. **数据缓冲**：使用 pandas Series 存储历史数据，利用 `engine/indicators.py` 计算指标
3. **仓位管理**：使用 `self._capital` 和 `self.get_position()` 管理资金和持仓
4. **风险控制**：合理设置仓位比例，避免单笔交易风险过大
5. **充分回测**：在多个时间段、多个标的上回测，避免过拟合

---

## 回测指南

### 回测流程

```
1. 配置回测参数
   ├── 时间范围（start_date, end_date）
   ├── K 线周期（timeframe: 1m/5m/15m/1h/4h/1d）
   ├── 交易对（symbol: BTC/USDT）
   ├── 初始资金（initial_capital）
   └── 手续费率（commission_rate）

2. 选择策略和参数
   ├── 策略类型（MA_CROSS/RSI/BOLLINGER/GRID/DCA）
   └── 策略参数（各策略参数不同）

3. 执行回测
   ├── 加载历史 OHLCV 数据
   ├── 策略初始化
   ├── 逐 K 线处理
   │   ├── 调用 strategy.on_candle()
   │   ├── 产生信号 → 模拟成交
   │   └── 计算手续费和滑点
   └── 生成结果

4. 分析结果
   ├── 交易列表（每笔交易详情）
   ├── 权益曲线（资金变化轨迹）
   └── 统计指标
```

### 关键统计指标

| 指标 | 说明 | 参考值 |
|------|------|--------|
| **胜率（Win Rate）** | 盈利交易数 / 总交易数 | > 50% 为佳 |
| **总收益率（Total Return）** | (最终资金 - 初始资金) / 初始资金 | 正值为盈利 |
| **年化收益率（Annualized Return）** | 按年折算的收益率 | 对比基准收益 |
| **最大回撤（Max Drawdown）** | 权益曲线的最大峰谷跌幅 | < 20% 为佳 |
| **夏普比率（Sharpe Ratio）** | 风险调整后收益 | > 1.0 为佳，> 2.0 优秀 |
| **索提诺比率（Sortino Ratio）** | 仅考虑下行风险的夏普变体 | > 1.5 为佳 |
| **卡尔马比率（Calmar Ratio）** | 年化收益 / 最大回撤 | > 1.0 为佳 |
| **盈亏比（Profit Factor）** | 总盈利 / 总亏损 | > 1.5 为佳 |
| **平均持仓时间** | 每笔交易的平均持续时间 | 因策略而异 |

### 回测注意事项

1. **避免前视偏差**：策略只能使用当前和历史数据，不能使用未来数据
2. **考虑手续费**：设置合理的 `commission_rate`（通常 0.1%）
3. **考虑滑点**：真实交易中成交价可能偏离信号价格
4. **多标的验证**：在不同交易对上测试，检验策略普适性
5. **多时段验证**：在牛市、熊市、震荡市中分别回测
6. **样本外测试**：将数据分为训练集和测试集，避免过拟合
7. **参数敏感性**：小幅调整参数后策略表现不应剧烈变化

# 📡 CryptoQuant API 接口文档

## 目录

- [概述](#概述)
- [认证](#认证)
- [认证接口](#认证接口)
- [用户接口](#用户接口)
- [策略接口](#策略接口)
- [回测接口](#回测接口)
- [交易接口](#交易接口)
- [行情数据接口](#行情数据接口)
- [组合接口](#组合接口)
- [告警接口](#告警接口)
- [WebSocket](#websocket)
- [健康检查](#健康检查)

---

## 概述

### Base URL

```
http://localhost:8000/api/v1
```

### 请求格式

- Content-Type: `application/json`
- 字符编码: `UTF-8`

### 响应格式

所有接口返回 JSON 格式数据。成功响应直接返回数据对象，错误响应格式：

```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 请求体验证失败 |
| 429 | 请求频率超限 |
| 500 | 服务器内部错误 |

---

## 认证

除注册和登录外，所有接口需要在请求头中携带 JWT Access Token：

```
Authorization: Bearer <access_token>
```

Token 有效期为 30 分钟。过期后使用 Refresh Token 获取新的 Access Token。

---

## 认证接口

### 注册

```
POST /auth/register
```

**请求体：**

```json
{
  "email": "user@example.com",
  "username": "trader",
  "password": "SecurePassword123"
}
```

**响应（200）：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 登录

```
POST /auth/login
```

**请求体：**

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "two_fa_code": "123456"
}
```

> `two_fa_code` 仅在用户启用 2FA 后必填。

**响应（200）：**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 刷新 Token

```
POST /auth/refresh
```

**请求体：**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**响应（200）：** 同登录响应格式，返回新的 Token 对。

### 登出

```
POST /auth/logout
```

**请求体：**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**响应（200）：**

```json
{
  "message": "Successfully logged out"
}
```

### 全部登出

```
POST /auth/logout-all
```

> 需要认证。注销当前用户的所有活跃会话。

**响应（200）：**

```json
{
  "message": "Successfully logged out from all sessions"
}
```

---

## 用户接口

### 获取当前用户

```
GET /users/me
```

**响应（200）：**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "trader",
  "is_active": true,
  "avatar_url": "/static/avatars/xxx.jpg",
  "phone": null,
  "timezone": "Asia/Shanghai",
  "theme_mode": "dark",
  "language": "zh-CN",
  "default_exchange": "binance",
  "two_fa_enabled": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 更新用户资料

```
PUT /users/me
```

**请求体：**

```json
{
  "username": "new_name",
  "phone": "+8613800138000",
  "timezone": "Asia/Shanghai"
}
```

### 修改密码

```
PUT /users/me/password
```

**请求体：**

```json
{
  "old_password": "OldPassword123",
  "new_password": "NewPassword456"
}
```

### 更新用户设置

```
PUT /users/me/settings
```

**请求体：**

```json
{
  "theme_mode": "dark",
  "language": "zh-CN",
  "default_exchange": "binance",
  "default_timeframe": "1h"
}
```

### 上传头像

```
POST /users/me/avatar
Content-Type: multipart/form-data
```

**参数：** `file` — 图片文件（JPEG/PNG/GIF/WebP）

### 2FA — 初始化设置

```
POST /users/me/2fa/setup
```

**响应（200）：**

```json
{
  "secret": "BASE32SECRET...",
  "qr_code": "otpauth://totp/CryptoQuant:user@example.com?secret=..."
}
```

### 2FA — 验证启用

```
POST /users/me/2fa/verify
```

**请求体：**

```json
{
  "code": "123456"
}
```

### 2FA — 关闭

```
DELETE /users/me/2fa
```

**请求体：**

```json
{
  "code": "123456"
}
```

### 2FA — 获取恢复码

```
GET /users/me/2fa/recovery-codes
```

### 会话管理 — 列出会话

```
GET /users/me/sessions
```

**响应（200）：**

```json
[
  {
    "id": "uuid",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "device_info": "Chrome on Windows",
    "last_active_at": "2024-01-01T12:00:00Z",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### 会话管理 — 注销会话

```
DELETE /users/me/sessions/{session_id}
```

### API 密钥 — 列表

```
GET /users/me/api-keys
```

**响应（200）：**

```json
[
  {
    "id": "uuid",
    "exchange": "binance",
    "label": "主账户",
    "api_key_masked": "abcd****wxyz",
    "permissions": ["read", "trade"],
    "is_active": true,
    "last_tested_at": "2024-01-01T00:00:00Z"
  }
]
```

### API 密钥 — 创建

```
POST /users/me/api-keys
```

**请求体：**

```json
{
  "exchange": "binance",
  "api_key": "your-api-key",
  "api_secret": "your-api-secret",
  "label": "主账户",
  "permissions": ["read", "trade"]
}
```

### API 密钥 — 更新

```
PUT /users/me/api-keys/{key_id}
```

### API 密钥 — 删除

```
DELETE /users/me/api-keys/{key_id}
```

### API 密钥 — 连通测试

```
POST /users/me/api-keys/{key_id}/test
```

### 通知 — 列表

```
GET /users/me/notifications?page=1&page_size=20
```

### 通知 — 未读数量

```
GET /users/me/notifications/unread-count
```

**响应（200）：**

```json
{
  "count": 5
}
```

### 通知 — 标记已读

```
PUT /users/me/notifications/{notification_id}/read
```

### 通知 — 全部已读

```
PUT /users/me/notifications/read-all
```

### 通知 — 删除

```
DELETE /users/me/notifications/{notification_id}
```

### 通知设置 — 获取

```
GET /users/me/notification-settings
```

### 通知设置 — 更新

```
PUT /users/me/notification-settings
```

### 操作日志

```
GET /users/me/operation-logs?page=1&page_size=20&action=login
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码（默认 1） |
| `page_size` | int | 每页条数（默认 20） |
| `action` | string | 按操作类型筛选（可选） |

---

## 策略接口

### 列出策略

```
GET /strategies?page=1&page_size=20
```

**响应（200）：**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "BTC均线交叉",
      "strategy_type": "MA_CROSS",
      "parameters": {
        "fast_period": 9,
        "slow_period": 21,
        "signal_type": "ema"
      },
      "is_active": true,
      "is_running": false,
      "exchange": "binance",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 创建策略

```
POST /strategies
```

**请求体：**

```json
{
  "name": "BTC均线交叉",
  "description": "BTC 快慢均线交叉策略",
  "strategy_type": "MA_CROSS",
  "parameters": {
    "fast_period": 9,
    "slow_period": 21,
    "signal_type": "ema",
    "atr_period": 14,
    "risk_per_trade_pct": 0.01
  },
  "exchange": "binance",
  "symbol": "BTC/USDT",
  "timeframe": "1h"
}
```

**支持的策略类型：** `MA_CROSS`、`RSI`、`BOLLINGER`、`GRID`、`DCA`、`MACD`

### 获取策略详情

```
GET /strategies/{strategy_id}
```

### 更新策略

```
PUT /strategies/{strategy_id}
```

### 删除策略

```
DELETE /strategies/{strategy_id}
```

### 启动策略

```
POST /strategies/{strategy_id}/start
```

**响应（200）：**

```json
{
  "message": "Strategy started",
  "strategy_id": "uuid",
  "is_running": true
}
```

### 停止策略

```
POST /strategies/{strategy_id}/stop
```

---

## 回测接口

### 执行回测

```
POST /backtest/run
```

**请求体：**

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-06-30",
  "timeframe": "1h",
  "symbol": "BTC/USDT",
  "strategy_type": "MA_CROSS",
  "parameters": {
    "fast_period": 9,
    "slow_period": 21
  },
  "initial_capital": 10000.0,
  "commission_rate": 0.001
}
```

**响应（200）：**

```json
{
  "trades": [
    {
      "entry_time": "2024-01-15T08:00:00Z",
      "exit_time": "2024-01-16T14:00:00Z",
      "symbol": "BTC/USDT",
      "side": "long",
      "quantity": 0.1,
      "entry_price": 42000.0,
      "exit_price": 43500.0,
      "commission": 8.55,
      "pnl": 141.45,
      "pnl_pct": 3.37,
      "duration_hours": 30.0
    }
  ],
  "equity_curve": [
    {"timestamp": "2024-01-01T00:00:00Z", "equity": 10000.0},
    {"timestamp": "2024-01-15T08:00:00Z", "equity": 10141.45}
  ],
  "stats": {
    "total_trades": 25,
    "winning_trades": 15,
    "losing_trades": 10,
    "win_rate": 0.6,
    "total_return_pct": 18.5,
    "annualized_return_pct": 37.0,
    "max_drawdown_pct": 8.2,
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.41,
    "calmar_ratio": 4.51,
    "profit_factor": 2.1,
    "avg_trade_duration_hours": 28.5,
    "total_commission": 125.0
  }
}
```

---

## 交易接口

### 下单

```
POST /trading/orders
```

**请求体：**

```json
{
  "exchange": "binance",
  "symbol": "BTC/USDT",
  "order_type": "limit",
  "side": "buy",
  "quantity": 0.01,
  "price": 42000.0
}
```

**`order_type` 取值：** `market`、`limit`

**`side` 取值：** `buy`、`sell`

### 查询订单列表

```
GET /trading/orders?page=1&page_size=20&status=open&symbol=BTC/USDT
```

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `page` | int | 页码 |
| `page_size` | int | 每页条数 |
| `status` | string | 订单状态：pending/open/filled/cancelled |
| `symbol` | string | 交易对筛选（可选） |

### 查询订单详情

```
GET /trading/orders/{order_id}
```

### 撤销订单

```
DELETE /trading/orders/{order_id}
```

### 交易记录

```
GET /trading/trades?page=1&page_size=20
```

**响应（200）：**

```json
{
  "items": [
    {
      "id": "uuid",
      "exchange": "binance",
      "symbol": "BTC/USDT",
      "side": "buy",
      "price": 42000.0,
      "quantity": 0.01,
      "fee": 0.042,
      "fee_currency": "USDT",
      "pnl": null,
      "created_at": "2024-01-15T08:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

## 行情数据接口

### K 线数据

```
GET /market-data/candles?exchange=binance&symbol=BTC/USDT&timeframe=1h&limit=100
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `exchange` | string | 是 | 交易所名称 |
| `symbol` | string | 是 | 交易对 |
| `timeframe` | string | 否 | K 线周期（默认 1h） |
| `limit` | int | 否 | 数据条数（默认 100） |

**响应（200）：**

```json
[
  {
    "timestamp": "2024-01-15T08:00:00Z",
    "open": 42000.0,
    "high": 42500.0,
    "low": 41800.0,
    "close": 42300.0,
    "volume": 1234.56
  }
]
```

### 当前行情

```
GET /market-data/ticker?exchange=binance&symbol=BTC/USDT
```

**响应（200）：**

```json
{
  "symbol": "BTC/USDT",
  "last": 42300.0,
  "bid": 42290.0,
  "ask": 42310.0,
  "volume": 15000.0,
  "change_24h": 2.5,
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 深度数据

```
GET /market-data/orderbook?exchange=binance&symbol=BTC/USDT&depth=20
```

**响应（200）：**

```json
{
  "symbol": "BTC/USDT",
  "bids": [[42290.0, 1.5], [42280.0, 2.0]],
  "asks": [[42310.0, 1.2], [42320.0, 0.8]],
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### 交易所列表

```
GET /market-data/exchanges
```

**响应（200）：**

```json
["binance", "coinbase", "kraken", "bybit", "okx", "huobi", "kucoin"]
```

### 交易对列表

```
GET /market-data/symbols?exchange=binance
```

**响应（200）：**

```json
["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
```

---

## 组合接口

### 组合汇总

```
GET /portfolio
```

**响应（200）：**

```json
{
  "total_value_usdt": 50000.0,
  "cash_usdt": 20000.0,
  "positions_value_usdt": 30000.0,
  "unrealized_pnl": 1500.0,
  "realized_pnl": 3000.0,
  "daily_pnl": 500.0,
  "total_return_pct": 12.5
}
```

### 盈亏历史

```
GET /portfolio/pnl-history?days=30
```

**响应（200）：**

```json
[
  {
    "date": "2024-01-01",
    "pnl": 150.0,
    "cumulative_pnl": 150.0,
    "total_value": 50150.0
  }
]
```

### 指定交易所组合

```
GET /portfolio/{exchange}
```

### 交易所持仓

```
GET /portfolio/{exchange}/positions
```

**响应（200）：**

```json
[
  {
    "symbol": "BTC/USDT",
    "quantity": 0.5,
    "avg_entry_price": 40000.0,
    "current_price": 42000.0,
    "value_usdt": 21000.0,
    "unrealized_pnl": 1000.0,
    "unrealized_pnl_pct": 5.0
  }
]
```

---

## 告警接口

### 列出告警

```
GET /alerts?page=1&page_size=20
```

### 创建告警

```
POST /alerts
```

**请求体：**

```json
{
  "name": "BTC 价格突破 50000",
  "alert_type": "price",
  "exchange": "binance",
  "symbol": "BTC/USDT",
  "condition": "gte",
  "threshold": 50000.0
}
```

**`condition` 取值：**

| 值 | 说明 |
|----|------|
| `gt` | 大于 |
| `gte` | 大于等于 |
| `lt` | 小于 |
| `lte` | 小于等于 |

### 获取告警详情

```
GET /alerts/{alert_id}
```

### 更新告警

```
PUT /alerts/{alert_id}
```

### 删除告警

```
DELETE /alerts/{alert_id}
```

### 测试告警

```
POST /alerts/{alert_id}/test
```

> 模拟触发告警，验证告警配置是否正确。

---

## WebSocket

### 实时连接

```
ws://localhost:8000/ws/{client_id}
```

**连接参数：**

| 参数 | 说明 |
|------|------|
| `client_id` | 客户端唯一标识符 |

**消息格式（JSON）：**

```json
{
  "type": "ticker",
  "data": {
    "symbol": "BTC/USDT",
    "price": 42300.0,
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

支持的消息类型：实时行情推送、交易通知、告警触发通知。

---

## 健康检查

```
GET /health
```

**响应（200）：**

```json
{
  "status": "healthy",
  "app": "CryptoQuant",
  "version": "1.0.0"
}
```

> 此接口无需认证，用于负载均衡和监控探针。

# 🏗 CryptoQuant 架构设计文档

## 目录

- [系统架构](#系统架构)
- [模块说明](#模块说明)
- [数据流](#数据流)
- [数据库设计](#数据库设计)
- [认证流程](#认证流程)
- [主题系统设计](#主题系统设计)

---

## 系统架构

```
                            ┌──────────────┐
                            │   Nginx      │
                            │  (反向代理)   │
                            │  :80 / :443  │
                            └──────┬───────┘
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                 │
                  ▼                ▼                 ▼
         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
         │   Frontend   │ │   Backend    │ │  WebSocket   │
         │   React 18   │ │   FastAPI    │ │   /ws/{id}   │
         │   :3000      │ │   :8000      │ │   :8000      │
         └──────────────┘ └──────┬───────┘ └──────────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  │              │               │
                  ▼              ▼               ▼
         ┌──────────────┐ ┌──────────┐ ┌──────────────────┐
         │  PostgreSQL  │ │  Redis   │ │  Celery Workers  │
         │  (数据存储)   │ │ (缓存/    │ │  (异步任务)       │
         │  :5432       │ │  消息队列) │ │                  │
         │              │ │  :6379   │ │  ┌────────────┐  │
         └──────────────┘ └──────────┘ │  │ celery_beat │  │
                                       │  │ (定时调度)   │  │
                                       │  └────────────┘  │
                                       └──────────────────┘
                                               │
                                               ▼
                                      ┌──────────────────┐
                                      │   交易所 API      │
                                      │  (CCXT 统一接口)   │
                                      │  Binance/OKX/...  │
                                      └──────────────────┘
```

### 架构概述

CryptoQuant 采用前后端分离的微服务架构：

- **Nginx** 作为统一入口，负责反向代理、限流、安全头和 WebSocket 升级
- **Frontend** 是 React 18 单页应用，通过 REST API 和 WebSocket 与后端通信
- **Backend** 是 FastAPI 异步应用，处理所有业务逻辑
- **PostgreSQL** 作为持久化存储
- **Redis** 同时承担缓存和 Celery 消息队列角色
- **Celery Worker + Beat** 处理异步任务（交易执行、数据采集、告警检查）
- **CCXT** 提供统一的多交易所 API 接口

---

## 模块说明

### 后端 API 层（`backend/app/api/v1/`）

| 模块 | 职责 |
|------|------|
| `auth.py` | 用户注册、登录、Token 刷新、登出（支持 2FA） |
| `users.py` | 用户资料、设置、2FA 管理、会话管理、API 密钥、通知、操作日志 |
| `strategies.py` | 策略 CRUD、启动/停止策略运行 |
| `backtest.py` | 执行策略回测，返回详细统计结果 |
| `trading.py` | 订单管理（下单、撤单、查询）、交易记录 |
| `market_data.py` | K 线数据、Ticker、深度图、交易所/交易对列表 |
| `portfolio.py` | 组合汇总、盈亏历史、交易所持仓 |
| `alerts.py` | 价格告警 CRUD、告警测试 |

### 量化引擎（`backend/engine/`）

| 模块 | 职责 |
|------|------|
| `strategy_base.py` | 策略抽象基类，定义 `on_candle`/`on_tick` 接口，提供 `buy`/`sell` 方法和绩效统计 |
| `indicators.py` | 技术指标库（15+ 指标），输入 pandas Series，输出计算结果 |
| `backtester.py` | 事件驱动回测器，模拟滑点和手续费，计算夏普比率等统计指标 |
| `risk_manager.py` | 风险管理器：仓位上限、每日止损、最大回撤限制、Kelly 公式 |
| `execution.py` | 交易执行引擎，封装 CCXT 下单接口，支持指数退避重试 |
| `portfolio_manager.py` | 组合管理器，追踪多交易所持仓、盈亏、再平衡计算 |
| `data_feed.py` | 数据源连接器，获取 OHLCV 数据、Ticker、深度，支持分页历史数据 |

### 内置策略（`backend/strategies/`）

| 策略 | 类名 | 说明 |
|------|------|------|
| 均线交叉 | `MovingAverageCross` | 快慢均线金叉死叉，ATR 动态仓位 |
| RSI | `RSIStrategy` | RSI 超买超卖 + 中线退出 |
| 布林带 | `BollingerBandsStrategy` | 挤压检测 + 均值回归 |
| 网格交易 | `GridTradingStrategy` | 等间距网格逐级交易 |
| DCA 定投 | `DCAStrategy` | 定时定额 + 跌幅加仓 + 止盈 |

### 任务系统（`backend/tasks/`）

| 模块 | 职责 |
|------|------|
| `celery_app.py` | Celery 应用配置 |
| `data_tasks.py` | 定时采集行情数据 |
| `trading_tasks.py` | 异步交易执行 |
| `alert_tasks.py` | 定时检查价格告警 |

### 前端应用（`frontend/src/`）

| 目录 | 职责 |
|------|------|
| `api/` | Axios HTTP 客户端，封装后端 API 调用 |
| `components/` | 可复用 UI 组件（图表、表格、表单等） |
| `hooks/` | 自定义 React Hooks（数据获取、状态逻辑） |
| `locales/` | 国际化翻译文件（中文/英文） |
| `pages/` | 页面级组件（Dashboard、Trading、Strategies 等） |
| `store/` | Zustand 全局状态管理 |
| `themes/` | 亮色/暗色主题配置 |
| `types/` | TypeScript 类型定义 |

---

## 数据流

### 实时行情数据流

```
交易所 API ──► DataFeed ──► WebSocket ──► Frontend 图表
                  │
                  ├──► Celery Task (定时采集) ──► PostgreSQL
                  │
                  └──► AlertTask (价格检查) ──► 通知系统
```

### 策略交易数据流

```
用户创建策略 ──► Strategy Service ──► PostgreSQL (保存配置)
                                         │
用户启动策略 ──► Celery Task ──► StrategyBase.on_candle()
                                         │
                                    Signal (BUY/SELL)
                                         │
                              RiskManager.check_order()
                                         │
                              ExecutionEngine.place_order()
                                         │
                                    交易所 API
                                         │
                              PortfolioManager.update()
                                         │
                                    PostgreSQL (记录)
```

### 回测数据流

```
用户提交回测请求 ──► BacktestConfig
                        │
                   Backtester.run()
                        │
              DataFeed.fetch_ohlcv_history()
                        │
              Strategy.initialize()
                        │
              逐 K 线处理: Strategy.on_candle()
                        │
                   Signal ──► 模拟成交
                        │
              BacktestResult (trades, equity_curve, stats)
                        │
                   返回前端展示
```

---

## 数据库设计

### 核心数据表

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│      User        │     │    Strategy      │     │      Order       │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id (UUID, PK)    │◄──┐ │ id (UUID, PK)    │◄──┐ │ id (UUID, PK)    │
│ email (unique)   │   │ │ user_id (FK)     │   │ │ user_id (FK)     │
│ username (unique)│   │ │ name             │   │ │ strategy_id (FK) │
│ hashed_password  │   │ │ strategy_type    │   │ │ exchange         │
│ is_active        │   │ │ parameters (JSON)│   │ │ symbol           │
│ theme_mode       │   │ │ is_active        │   │ │ order_type       │
│ language         │   │ │ is_running       │   │ │ side (buy/sell)  │
│ two_fa_enabled   │   │ │ exchange         │   │ │ price            │
│ two_fa_secret    │   │ │ symbol           │   │ │ quantity         │
│ avatar_url       │   │ │ timeframe        │   │ │ status           │
│ timezone         │   │ └──────────────────┘   │ │ filled_quantity  │
│ locked_until     │   │                        │ └──────────────────┘
└──────────────────┘   │                        │          │
         │             │                        │          │
         │   ┌─────────┴──────┐                 │          ▼
         │   │                │                 │ ┌──────────────────┐
         ▼   ▼                ▼                 │ │      Trade       │
┌──────────────────┐ ┌──────────────────┐       │ ├──────────────────┤
│   UserSession    │ │   UserApiKey     │       │ │ id (UUID, PK)    │
├──────────────────┤ ├──────────────────┤       │ │ user_id (FK)     │
│ id (UUID, PK)    │ │ id (UUID, PK)    │       │ │ strategy_id (FK) │
│ user_id (FK)     │ │ user_id (FK)     │       │ │ order_id (FK)    │
│ token_hash       │ │ exchange         │       │ │ exchange         │
│ ip_address       │ │ api_key_encrypted│       │ │ symbol           │
│ user_agent       │ │ api_secret_enc.  │       │ │ side             │
│ is_active        │ │ label            │       │ │ price            │
│ expires_at       │ │ permissions (JSON)│      │ │ quantity         │
└──────────────────┘ │ is_active        │       │ │ fee              │
                     └──────────────────┘       │ │ pnl              │
                                                │ └──────────────────┘
┌──────────────────┐ ┌──────────────────┐       │
│    Portfolio     │ │      Alert       │       │
├──────────────────┤ ├──────────────────┤       │
│ id (UUID, PK)    │ │ id (UUID, PK)    │       │
│ user_id (FK)     │ │ user_id (FK)     │       │
│ exchange         │ │ name             │       │
│ total_value_usdt │ │ exchange         │       │
│ available_usdt   │ │ symbol           │       │
│ positions (JSON) │ │ condition        │       │
│ daily_pnl        │ │ threshold        │       │
│ total_pnl        │ │ is_active        │       │
└──────────────────┘ │ is_triggered     │       │
                     └──────────────────┘       │
┌──────────────────┐ ┌──────────────────┐       │
│  OperationLog    │ │  Notification    │       │
├──────────────────┤ ├──────────────────┤       │
│ id (UUID, PK)    │ │ id (UUID, PK)    │       │
│ user_id (FK)     │ │ user_id (FK)     │       │
│ action           │ │ title            │       │
│ resource_type    │ │ content          │       │
│ resource_id      │ │ notification_type│       │
│ details (JSON)   │ │ is_read          │       │
│ ip_address       │ │ related_id       │       │
│ created_at       │ │ created_at       │       │
└──────────────────┘ └──────────────────┘       │
```

### 表关系说明

| 关系 | 说明 |
|------|------|
| User → Strategy | 一对多：一个用户拥有多个策略 |
| User → Order | 一对多：一个用户拥有多个订单 |
| Strategy → Order | 一对多：一个策略产生多个订单 |
| Order → Trade | 一对多：一个订单可能产生多笔成交 |
| User → UserSession | 一对多：多设备登录 |
| User → UserApiKey | 一对多：多个交易所 API 密钥 |
| User → Portfolio | 一对多：每个交易所一个组合记录 |
| User → Alert | 一对多：多个价格告警 |
| User → OperationLog | 一对多：操作审计日志 |
| User → Notification | 一对多：站内通知 |

---

## 认证流程

### JWT 双 Token 认证

```
┌──────────┐                    ┌──────────┐                  ┌──────────┐
│  客户端   │                    │  后端API  │                  │ 数据库    │
└────┬─────┘                    └────┬─────┘                  └────┬─────┘
     │                               │                             │
     │  1. POST /auth/login          │                             │
     │  (email, password, 2fa_code)  │                             │
     │──────────────────────────────►│                             │
     │                               │  2. 验证用户凭据             │
     │                               │────────────────────────────►│
     │                               │◄────────────────────────────│
     │                               │                             │
     │                               │  3. 验证 2FA (如已启用)      │
     │                               │                             │
     │                               │  4. 创建 Session             │
     │                               │────────────────────────────►│
     │                               │                             │
     │  5. 返回 access_token         │                             │
     │     + refresh_token           │                             │
     │◄──────────────────────────────│                             │
     │                               │                             │
     │  6. API 请求                   │                             │
     │  Authorization: Bearer {at}   │                             │
     │──────────────────────────────►│                             │
     │                               │  7. 验证 JWT                │
     │  8. 返回数据                   │                             │
     │◄──────────────────────────────│                             │
     │                               │                             │
     │  9. access_token 过期          │                             │
     │                               │                             │
     │  10. POST /auth/refresh        │                             │
     │  (refresh_token)              │                             │
     │──────────────────────────────►│                             │
     │                               │  11. 验证 refresh_token     │
     │                               │  12. 轮换 refresh_token     │
     │  13. 新 access_token           │────────────────────────────►│
     │     + 新 refresh_token         │                             │
     │◄──────────────────────────────│                             │
     │                               │                             │
```

### Token 说明

| Token | 有效期 | 用途 |
|-------|--------|------|
| Access Token | 30 分钟 | API 请求认证，携带用户 ID |
| Refresh Token | 7 天 | 刷新 Access Token，存储在数据库中（SHA-256 哈希） |

### 安全机制

- **密码哈希**：bcrypt 算法（passlib）
- **JWT 签名**：HS256 算法
- **2FA 验证**：PyOTP TOTP（RFC 6238），支持恢复码
- **API 密钥加密**：AES-256-CBC + 随机 IV
- **登录保护**：失败次数限制 + 账户锁定
- **Token 哈希**：Refresh Token 以 SHA-256 哈希形式存储在数据库

---

## 主题系统设计

### 架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户设置                               │
│                                                         │
│   theme_mode: "light" | "dark" | "auto"                 │
│                                                         │
│   ┌──────────┐  ┌──────────┐  ┌────────────────────┐   │
│   │  亮色模式  │  │  暗色模式  │  │  跟随系统          │   │
│   │  (light)  │  │  (dark)  │  │  (auto)            │   │
│   └──────────┘  └──────────┘  │  prefers-color-     │   │
│                               │  scheme 媒体查询     │   │
│                               └────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Ant Design 主题配置                      │
│                                                         │
│   ConfigProvider                                        │
│   ├── theme.algorithm: defaultAlgorithm / darkAlgorithm │
│   ├── token: { colorPrimary, borderRadius, ... }        │
│   └── components: { Button, Input, Table, ... }         │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    全站组件适配                            │
│                                                         │
│   Dashboard │ Trading │ Strategies │ Portfolio │ ...     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 实现方式

1. **用户偏好持久化**：`User.theme_mode` 字段存储在数据库，通过 `/users/me/settings` API 更新
2. **前端状态管理**：Zustand store 管理当前主题状态
3. **主题配置文件**：`frontend/src/themes/` 目录下定义亮色和暗色主题 Token
4. **Ant Design 集成**：通过 `ConfigProvider` 的 `theme` 属性全局切换算法和 Token
5. **系统跟随**：监听 `prefers-color-scheme` 媒体查询自动切换

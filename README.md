<div align="center">

# 🚀 CryptoQuant - 加密货币量化交易平台

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178c6.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**一站式加密货币量化交易解决方案 — 策略开发 · 回测验证 · 实盘交易 · 风险管理**

</div>

---

## 📖 概述

CryptoQuant 是一个全栈加密货币量化交易平台，提供从策略编写、历史回测到实盘交易的完整工作流。平台内置多种经典量化策略和丰富的技术指标库，支持多交易所接入，具备完善的风险管理和用户权限体系。前后端分离架构，支持 Docker 一键部署，适合个人量化交易者和小型团队使用。

---

## ✨ 功能特性

### 📊 量化引擎
- **技术指标库**：SMA、EMA、RSI、MACD、布林带（Bollinger Bands）、ATR、KDJ、OBV、VWAP、CCI、MFI、Williams %R、ADX、Stochastic 等 15+ 指标
- **事件驱动回测**：支持自定义时间范围、滑点模拟、手续费计算，输出夏普比率、索提诺比率、卡尔马比率、最大回撤、盈亏比等详细指标
- **风险管理**：仓位上限、单日止损、最大回撤限制、最大持仓数量、Kelly 公式仓位计算、固定比例风险仓位

### 🤖 内置策略
- **均线交叉策略（MA Cross）**：支持 SMA/EMA 切换，ATR 动态仓位管理
- **RSI 策略**：超买超卖信号，中线退出机制
- **布林带策略**：挤压检测 + 均值回归交易
- **网格交易策略（Grid Trading）**：自动网格划分，逐级买入卖出
- **DCA 定投策略**：定时定额 + 跌幅加仓 + 止盈退出

### 🔐 用户中心
- **JWT 双 Token 认证**：Access Token + Refresh Token，自动轮换
- **双因素认证（2FA）**：TOTP 动态口令，恢复码备份
- **API 密钥加密存储**：AES-256 加密交易所 API Key
- **会话管理**：多设备登录管理，远程登出
- **操作审计**：全操作日志记录，支持筛选查询

### 📈 实时行情
- **多交易所接入**：通过 CCXT 统一接口支持 Binance、Coinbase、Kraken、Bybit、OKX、Huobi、KuCoin 等 7+ 交易所
- **K 线图 & 深度图**：多时间周期 OHLCV 数据，实时订单簿
- **实时推送**：WebSocket 实时行情和交易通知

### 💼 组合管理
- **多交易所持仓汇总**：统一展示各交易所资产
- **盈亏计算**：已实现 / 未实现盈亏追踪
- **资产分配**：持仓权重分析，再平衡建议

### 🔔 告警系统
- **价格告警**：支持大于、大于等于、小于、小于等于条件
- **告警测试**：模拟触发，验证告警配置
- **推送通知**：站内通知 + 未读计数

### 🎨 主题系统
- **亮色 / 暗色 / 跟随系统**：三种主题模式
- **全站适配**：所有页面组件统一主题切换

### 🌍 国际化
- **中文 / 英文**：全站双语支持（react-i18next）

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **编程语言** | Python 3.11+, TypeScript 5.3 |
| **数据库** | PostgreSQL 15 |
| **缓存/消息** | Redis 7 |
| **任务队列** | Celery（定时任务 + 异步处理） |
| **交易所接口** | CCXT（统一多交易所 API） |
| **前端框架** | React 18 + Ant Design 5 |
| **状态管理** | Zustand |
| **图表** | @ant-design/plots, Lightweight Charts |
| **国际化** | react-i18next |
| **构建工具** | Vite 5 |
| **反向代理** | Nginx（限流 + 安全头 + WebSocket） |
| **容器化** | Docker + Docker Compose |
| **数据库迁移** | Alembic |
| **测试** | pytest + Vitest |

---

## 📦 项目结构

```
CryptoQuant/
├── backend/
│   ├── app/                    # FastAPI 应用
│   │   ├── api/v1/             # REST API 端点
│   │   ├── core/               # 安全、异常处理
│   │   ├── db/                 # 数据库会话
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务逻辑层
│   │   └── utils/              # 工具函数
│   ├── engine/                 # 量化引擎
│   │   ├── backtester.py       # 事件驱动回测器
│   │   ├── indicators.py       # 技术指标库
│   │   ├── strategy_base.py    # 策略基类
│   │   ├── risk_manager.py     # 风险管理器
│   │   ├── execution.py        # 交易执行引擎
│   │   ├── portfolio_manager.py # 组合管理器
│   │   └── data_feed.py        # 数据源连接器
│   ├── strategies/             # 内置策略
│   ├── tasks/                  # Celery 异步任务
│   ├── tests/                  # 测试用例
│   └── alembic/                # 数据库迁移
├── frontend/
│   └── src/
│       ├── api/                # API 客户端
│       ├── components/         # 可复用组件
│       ├── hooks/              # 自定义 Hooks
│       ├── locales/            # i18n 翻译文件
│       ├── pages/              # 页面组件
│       ├── store/              # Zustand 状态管理
│       ├── themes/             # 主题配置
│       └── types/              # TypeScript 类型定义
├── nginx/                      # Nginx 配置
├── docs/                       # 项目文档
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## 🚀 快速开始

### 环境要求

- Docker & Docker Compose（推荐）
- 或：Python 3.11+、Node.js 18+、PostgreSQL 15、Redis 7

### 方式一：Docker Compose 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/CryptoQuant.git
cd CryptoQuant

# 2. 创建环境变量文件
make env
# 编辑 .env 文件，修改 SECRET_KEY、数据库密码等

# 3. 一键启动所有服务
make up

# 4. 运行数据库迁移
make migrate

# 5. 访问应用
# 前端界面：http://localhost:3000
# API 文档：http://localhost:8000/docs
# Nginx 代理：http://localhost
```

### 方式二：本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

### 常用命令

```bash
make up              # 启动所有服务
make down            # 停止所有服务
make logs            # 查看日志（可指定服务：make logs s=backend）
make migrate         # 运行数据库迁移
make test            # 运行全部测试
make lint            # 代码检查
make format          # 代码格式化
make clean           # 清理缓存和构建产物
```

---

## 📝 API 文档

启动后端服务后访问 `http://localhost:8000/docs` 查看 Swagger UI 交互式文档。

主要 API 分组：

| 分组 | 前缀 | 说明 |
|------|------|------|
| 认证 | `/api/v1/auth` | 注册、登录、Token 刷新、登出 |
| 用户 | `/api/v1/users` | 个人信息、设置、2FA、会话、API 密钥、通知、操作日志 |
| 策略 | `/api/v1/strategies` | 策略 CRUD、启动、停止 |
| 回测 | `/api/v1/backtest` | 策略回测执行 |
| 交易 | `/api/v1/trading` | 下单、撤单、交易记录 |
| 行情 | `/api/v1/market-data` | K 线、Ticker、深度、交易所列表 |
| 组合 | `/api/v1/portfolio` | 持仓汇总、盈亏历史 |
| 告警 | `/api/v1/alerts` | 价格告警 CRUD、测试触发 |

> 详细接口文档请查看 [docs/api.md](docs/api.md)

---

## 🧪 测试

```bash
# 运行所有测试
make test

# 仅后端测试（含覆盖率）
make test-backend

# 仅前端测试
make test-frontend
```

后端测试涵盖：API 接口测试、回测引擎测试、技术指标测试、风险管理器测试、策略逻辑测试。

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [架构设计](docs/architecture.md) | 系统架构、模块说明、数据流、认证流程 |
| [API 接口](docs/api.md) | 完整 REST API 参考文档 |
| [策略指南](docs/strategies.md) | 内置策略说明、自定义策略开发指南 |
| [部署指南](docs/deployment.md) | Docker 部署、环境变量、Nginx、SSL、监控 |

---

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。
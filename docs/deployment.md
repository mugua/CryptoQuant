# 🚀 CryptoQuant 部署指南

## 目录

- [Docker Compose 生产部署](#docker-compose-生产部署)
- [环境变量说明](#环境变量说明)
- [数据库迁移](#数据库迁移)
- [Nginx 配置](#nginx-配置)
- [SSL/TLS 配置](#ssltls-配置)
- [监控](#监控)
- [备份策略](#备份策略)

---

## Docker Compose 生产部署

### 前置要求

- Docker 20.10+
- Docker Compose v2.0+
- 至少 2GB 可用内存
- 域名（生产环境需配置 SSL）

### 部署步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-org/CryptoQuant.git
cd CryptoQuant
```

#### 2. 创建环境变量文件

```bash
make env
# 或手动复制
cp .env.example .env
```

#### 3. 编辑环境变量

```bash
vi .env
```

> ⚠️ **生产环境必须修改以下配置：**
> - `SECRET_KEY`：更换为随机强密钥
> - `POSTGRES_PASSWORD`：设置强数据库密码
> - `AES_SECRET_KEY`：更换为 32 字符随机密钥
> - `DEBUG`：设置为 `false`
> - `APP_ENV`：设置为 `production`
> - `CORS_ORIGINS`：设置为实际域名

#### 4. 构建并启动服务

```bash
# 构建所有镜像
make build

# 启动服务（后台运行）
make up
```

#### 5. 运行数据库迁移

```bash
make migrate
```

#### 6. 验证服务

```bash
# 查看服务状态
make ps

# 查看日志
make logs

# 测试后端健康检查
curl http://localhost:8000/api/health
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80, 443 | 对外统一入口 |
| Backend (FastAPI) | 8000 | REST API + WebSocket |
| Frontend (React) | 3000 | 前端应用 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存/消息队列 |

### 服务依赖关系

```
nginx → frontend → backend → postgres + redis
                    celery_worker → postgres + redis
                    celery_beat → celery_worker
```

### 常用运维命令

```bash
# 启动服务
make up

# 停止服务
make down

# 停止并删除数据卷（⚠️ 会丢失数据）
make down-volumes

# 查看日志（指定服务）
make logs s=backend
make logs s=celery_worker

# 进入后端容器
make shell-backend

# 进入数据库
make shell-db

# 重新构建单个服务
docker compose build backend
docker compose up -d backend
```

---

## 环境变量说明

### 应用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_NAME` | `CryptoQuant` | 应用名称 |
| `APP_ENV` | `development` | 环境：`development` / `production` |
| `DEBUG` | `true` | 调试模式（生产环境设为 `false`） |
| `SECRET_KEY` | — | JWT 签名密钥（**必须修改**） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access Token 有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh Token 有效期（天） |

### 数据库配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://...` | 后端数据库连接串 |
| `POSTGRES_USER` | `cryptoquant` | PostgreSQL 用户名 |
| `POSTGRES_PASSWORD` | `password` | PostgreSQL 密码（**必须修改**） |
| `POSTGRES_DB` | `cryptoquant` | 数据库名 |

### Redis 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接（缓存） |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery 消息代理 |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery 结果存储 |

### 安全配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AES_SECRET_KEY` | — | AES-256 加密密钥（32 字符，**必须修改**） |
| `CORS_ORIGINS` | `http://localhost:3000,...` | 允许的跨域来源（逗号分隔） |

### 邮件配置（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP 服务器 |
| `SMTP_PORT` | `587` | SMTP 端口 |
| `SMTP_USER` | — | SMTP 用户名 |
| `SMTP_PASSWORD` | — | SMTP 密码 |

### 生成安全密钥

```bash
# 生成 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# 生成 AES_SECRET_KEY（32 字符）
python3 -c "import secrets; print(secrets.token_urlsafe(24)[:32])"
```

---

## 数据库迁移

CryptoQuant 使用 [Alembic](https://alembic.sqlalchemy.org/) 管理数据库迁移。

### 运行迁移

```bash
# Docker 环境
make migrate

# 本地环境
cd backend
alembic upgrade head
```

### 创建新迁移

```bash
# Docker 环境
make migrate-create msg="add new table"

# 本地环境
cd backend
alembic revision --autogenerate -m "add new table"
```

### 回滚迁移

```bash
# Docker 环境（回退一步）
make migrate-downgrade

# 本地环境
cd backend
alembic downgrade -1
```

### 查看迁移历史

```bash
cd backend
alembic history --verbose
```

### 查看当前版本

```bash
cd backend
alembic current
```

### 迁移文件位置

```
backend/
├── alembic.ini                    # Alembic 配置
└── alembic/
    ├── env.py                     # 迁移环境配置
    └── versions/
        └── 001_initial.py         # 初始迁移
```

---

## Nginx 配置

### 默认配置

Nginx 配置文件位于 `nginx/nginx.conf`，提供以下功能：

### 反向代理

| 路径 | 上游 | 说明 |
|------|------|------|
| `/api/` | `backend:8000` | REST API 请求 |
| `/ws/` | `backend:8000` | WebSocket 连接 |
| `/` | `frontend:3000` | 前端 SPA |

### 限流配置

| 规则 | 限制 | 作用范围 |
|------|------|----------|
| `api_limit` | 60 请求/分钟 | 所有 API 接口 |
| `login_limit` | 10 请求/分钟 | 认证相关接口 |

### 安全头

```nginx
add_header X-Frame-Options SAMEORIGIN;
add_header X-Content-Type-Options nosniff;
add_header Referrer-Policy strict-origin-when-cross-origin;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()";
```

### 性能优化

- **Gzip 压缩**：启用，最小 256 字节
- **静态资源缓存**：JS/CSS/图片等缓存 1 年
- **客户端上传限制**：50MB
- **代理超时**：API 120 秒，WebSocket 3600 秒

### 自定义 Nginx 配置

编辑 `nginx/nginx.conf` 后重启 Nginx：

```bash
docker compose restart nginx
```

---

## SSL/TLS 配置

### 方式一：使用 Let's Encrypt（推荐）

#### 1. 安装 Certbot

```bash
apt-get update && apt-get install -y certbot
```

#### 2. 获取证书

```bash
certbot certonly --standalone -d your-domain.com
```

#### 3. 修改 docker-compose.yml

在 `nginx` 服务中挂载证书：

```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

#### 4. 修改 Nginx 配置

在 `nginx/nginx.conf` 中添加 SSL 配置：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 其他配置保持不变...
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

#### 5. 自动续期

```bash
# 添加 crontab
echo "0 0 1 * * certbot renew --quiet && docker compose restart nginx" | crontab -
```

### 方式二：自签名证书（仅测试）

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/server.key \
  -out nginx/ssl/server.crt \
  -subj "/CN=localhost"
```

---

## 监控

### 健康检查

所有 Docker 服务都配置了健康检查：

| 服务 | 检查方式 | 间隔 |
|------|----------|------|
| PostgreSQL | `pg_isready` | 10 秒 |
| Redis | `redis-cli ping` | 10 秒 |
| Backend | `curl /api/health` | 30 秒 |
| Celery Worker | `celery inspect ping` | 30 秒 |

### 服务状态查看

```bash
# 查看所有服务状态
make ps

# 查看服务日志
make logs           # 所有服务
make logs s=backend # 指定服务

# 查看容器资源使用
docker stats
```

### 日志管理

```bash
# 实时查看后端日志
docker compose logs -f backend

# 查看最近 100 行 Celery Worker 日志
docker compose logs --tail 100 celery_worker

# 查看指定时间范围的日志
docker compose logs --since "2024-01-01T00:00:00" backend
```

### 建议监控方案

对于生产环境，建议部署以下监控工具：

1. **应用监控**：
   - Prometheus + Grafana（采集 FastAPI 指标）
   - Sentry（错误追踪和告警）

2. **基础设施监控**：
   - Docker 容器资源（CPU/内存/磁盘）
   - PostgreSQL 连接数和查询性能
   - Redis 内存使用和命中率

3. **日志聚合**：
   - ELK Stack（Elasticsearch + Logstash + Kibana）
   - 或 Loki + Grafana

---

## 备份策略

### 数据库备份

#### 手动备份

```bash
# 导出完整数据库
docker compose exec postgres pg_dump -U cryptoquant -d cryptoquant > backup_$(date +%Y%m%d_%H%M%S).sql

# 仅导出数据（不含结构）
docker compose exec postgres pg_dump -U cryptoquant -d cryptoquant --data-only > data_backup.sql

# 导出压缩格式
docker compose exec postgres pg_dump -U cryptoquant -d cryptoquant -Fc > backup.dump
```

#### 恢复数据库

```bash
# 从 SQL 文件恢复
cat backup.sql | docker compose exec -T postgres psql -U cryptoquant -d cryptoquant

# 从压缩文件恢复
docker compose exec -T postgres pg_restore -U cryptoquant -d cryptoquant < backup.dump
```

#### 自动备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# 数据库备份
docker compose exec -T postgres pg_dump \
  -U cryptoquant -d cryptoquant -Fc \
  > "$BACKUP_DIR/db_$TIMESTAMP.dump"

# Redis 备份（RDB 快照）
docker compose exec redis redis-cli BGSAVE
sleep 5
docker cp "$(docker compose ps -q redis)":/data/dump.rdb \
  "$BACKUP_DIR/redis_$TIMESTAMP.rdb"

# 清理旧备份
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete

echo "备份完成: $TIMESTAMP"
```

配置定时任务：

```bash
# 每天凌晨 3 点执行备份
echo "0 3 * * * cd /path/to/CryptoQuant && bash scripts/backup.sh" | crontab -
```

### Redis 备份

Redis 配置了 AOF 持久化（`appendonly yes`），数据存储在 Docker volume 中。

```bash
# 手动触发 RDB 快照
docker compose exec redis redis-cli BGSAVE

# 查看最后一次保存时间
docker compose exec redis redis-cli LASTSAVE
```

### 备份建议

| 数据 | 频率 | 保留期 | 说明 |
|------|------|--------|------|
| PostgreSQL 全量 | 每天 | 30 天 | 包含所有用户数据和交易记录 |
| PostgreSQL 增量 | 每小时 | 7 天 | WAL 归档（需额外配置） |
| Redis RDB | 每天 | 7 天 | 缓存数据，可从数据库重建 |
| .env 文件 | 每次修改后 | 永久 | 加密存储，单独备份 |
| Nginx 配置 | 每次修改后 | 永久 | 纳入版本控制 |

### 灾难恢复流程

```
1. 准备新服务器环境（Docker + Docker Compose）
2. 克隆项目代码
3. 恢复 .env 文件
4. 启动基础设施（PostgreSQL + Redis）
   docker compose up -d postgres redis
5. 恢复数据库备份
   cat backup.sql | docker compose exec -T postgres psql -U cryptoquant -d cryptoquant
6. 启动应用服务
   make up
7. 验证服务正常运行
   curl http://localhost:8000/api/health
```

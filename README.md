# OKX 支付监控系统

一个完整的 OKX 支付监控解决方案，支持订单管理、自动匹配、Webhook回调、MySQL存储和签名验证。

## 🎯 系统架构

```
A服务器 (监控服务器)                    B服务器 (业务服务器)
┌─────────────────────┐                ┌─────────────────────┐
│  HTTP API            │  提交订单      │  订单提交接口       │
│    ↓                 │  <==========   │    ↓                │
│  订单管理            │                │  业务逻辑处理       │
│    ↓                 │                │    ↓                │
│  OKX API监控         │  回调通知      │  Webhook接收器      │
│    ↓                 │  =========>    │    ↓                │
│  自动匹配订单        │  (HMAC签名)    │  你的业务系统       │
│    ↓                 │                │                     │
│  MySQL数据库         │                │                     │
└─────────────────────┘                └─────────────────────┘
```

## ✨ 功能特点

- ✅ **订单管理** - B服务器通过HTTP API提交支付订单
- ✅ **实时监控** - 自动检测OKX账户转账流入
- ✅ **自动匹配** - 转账金额与订单金额自动匹配
- ✅ **Webhook回调** - 匹配成功后自动回调B服务器
- ✅ **签名验证** - HMAC-SHA256签名保证数据安全
- ✅ **MySQL存储** - 订单和转账记录持久化存储
- ✅ **配置管理** - API密钥安全存储在数据库
- ✅ **交互式配置** - 首次运行通过终端向导配置
- ✅ **状态跟踪** - 记录订单状态和回调结果

## 🚀 快速开始

### 1. 安装依赖

\`\`\`bash
pip3 install -r requirements.txt
\`\`\`

### 2. 准备MySQL数据库

\`\`\`bash
mysql -u root -p
CREATE DATABASE okx_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
\`\`\`

或者使用提供的初始化脚本：

\`\`\`bash
mysql -u root -p okx_monitor < database_init.sql
\`\`\`

### 3. 运行配置向导

\`\`\`bash
python3 config_manager.py
\`\`\`

按提示输入：
- MySQL数据库信息
- OKX API密钥
- Webhook配置

### 4. 启动监控服务

\`\`\`bash
# 使用环境变量
export DB_PASSWORD='your_mysql_password'
python3 payment_monitor.py

# 或使用命令行参数
python3 payment_monitor.py 'your_mysql_password'

# 后台运行
nohup python3 payment_monitor.py > monitor.log 2>&1 &
\`\`\`

启动成功后，系统会：
- 启动HTTP API服务（默认端口5000）
- 启动OKX转账监控线程
- 提供以下API接口：
  - `POST /api/order/create` - 创建支付订单
  - `GET /api/order/status/<order_id>` - 查询订单状态
  - `GET /health` - 健康检查

## 📁 文件说明

### 核心文件

- \`payment_monitor.py\` - 支付监控主程序（HTTP API + 监控服务）
- \`config_manager.py\` - 配置管理器（交互式配置向导）
- \`database_init.sql\` - 数据库初始化脚本

### 示例代码

- \`b_server_example_new.py\` - B服务器完整示例（订单提交 + Webhook接收）

### 依赖文件

- \`requirements.txt\` - Python依赖包

## 🔄 工作流程

1. **B服务器提交订单**
   - 调用 `POST /api/order/create` 创建支付订单
   - 订单包含：订单号、金额、币种、回调地址

2. **A服务器监控转账**
   - 定期查询OKX账户转账记录
   - 检测到新转账后，尝试匹配待支付订单

3. **自动匹配订单**
   - 根据金额和币种匹配订单
   - 匹配成功后更新订单状态

4. **回调B服务器**
   - 使用HMAC-SHA256签名
   - 发送订单匹配结果到B服务器的回调地址

## 🔐 安全特性

- ✅ API密钥加密存储在数据库
- ✅ Webhook使用HMAC-SHA256签名
- ✅ 签名时间戳验证（防重放攻击）
- ✅ 敏感信息输入不显示

## 🔧 常用命令

\`\`\`bash
# 查看监控进程
ps aux | grep payment_monitor

# 查看日志
tail -f monitor.log

# 重新配置
python3 config_manager.py

# 查看订单记录
mysql -u root -p okx_monitor -e "SELECT * FROM payment_orders ORDER BY id DESC LIMIT 10;"

# 查看转账记录
mysql -u root -p okx_monitor -e "SELECT * FROM okx_transfers ORDER BY id DESC LIMIT 10;"
\`\`\`

## 📊 数据库表

### okx_config - 配置表
存储API密钥、Webhook配置、数据库配置等

### payment_orders - 支付订单表
存储B服务器提交的支付订单，包括订单状态、匹配信息、回调状态等

### okx_transfers - 转账记录表
存储所有检测到的OKX转账记录和匹配状态

### system_logs - 系统日志表（可选）
存储系统运行日志，便于问题排查

## ⚠️ 安全提示

- 不要将数据库密码提交到Git
- 定期更换API密钥和Webhook密钥
- 使用只读权限的API Key（如果只需要监控）
- 生产环境使用HTTPS

## �� 许可证

MIT License

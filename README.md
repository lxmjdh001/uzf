# OKX 转账监控系统

一个完整的 OKX 转账监控解决方案，支持实时监控、Webhook推送、MySQL存储和签名验证。

## 🎯 系统架构

```
A服务器 (监控服务器)                    B服务器 (业务服务器)
┌─────────────────────┐                ┌─────────────────────┐
│  OKX API            │                │  Webhook接收器      │
│    ↓                │   Webhook      │    ↓                │
│  监控程序           │  =========>    │  业务逻辑处理       │
│    ↓                │  (HMAC签名)    │    ↓                │
│  MySQL数据库        │                │  你的业务系统       │
└─────────────────────┘                └─────────────────────┘
```

## ✨ 功能特点

- ✅ **实时监控** - 自动检测OKX账户转账流入
- ✅ **Webhook推送** - 检测到转账后立即推送到B服务器
- ✅ **签名验证** - HMAC-SHA256签名保证数据安全
- ✅ **MySQL存储** - 转账记录持久化存储
- ✅ **配置管理** - API密钥安全存储在数据库
- ✅ **交互式配置** - 首次运行通过终端向导配置
- ✅ **推送状态跟踪** - 记录每次Webhook推送结果

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

### 3. 运行配置向导

\`\`\`bash
python3 config_manager.py
\`\`\`

按提示输入：
- MySQL数据库信息
- OKX API密钥
- Webhook配置

### 4. 启动监控

\`\`\`bash
# 使用环境变量
export DB_PASSWORD='your_mysql_password'
python3 okx_webhook_monitor.py

# 或使用命令行参数
python3 okx_webhook_monitor.py 'your_mysql_password'

# 后台运行
nohup python3 okx_webhook_monitor.py > monitor.log 2>&1 &
\`\`\`

## 📁 文件说明

### 核心文件

- \`okx_webhook_monitor.py\` - Webhook监控主程序
- \`config_manager.py\` - 配置管理器（交互式配置向导）
- \`test_connection.py\` - API连接测试工具

### 示例和文档

- \`b_server_example.py\` - B服务器Webhook接收示例
- \`WEBHOOK_SETUP.md\` - 完整部署文档
- \`requirements.txt\` - Python依赖包

## 📖 详细文档

查看 [WEBHOOK_SETUP.md](WEBHOOK_SETUP.md) 获取：
- 完整部署步骤
- 签名验证机制
- 数据库表结构
- 常见问题解答

## 🔐 安全特性

- ✅ API密钥加密存储在数据库
- ✅ Webhook使用HMAC-SHA256签名
- ✅ 签名时间戳验证（防重放攻击）
- ✅ 敏感信息输入不显示

## 🔧 常用命令

\`\`\`bash
# 查看监控进程
ps aux | grep okx_webhook_monitor

# 查看日志
tail -f monitor.log

# 重新配置
python3 config_manager.py

# 查看转账记录
mysql -u root -p okx_monitor -e "SELECT * FROM okx_transfers ORDER BY id DESC LIMIT 10;"
\`\`\`

## 📊 数据库表

### okx_config - 配置表
存储API密钥、Webhook配置等

### okx_transfers - 转账记录表
存储所有检测到的转账记录和推送状态

## ⚠️ 安全提示

- 不要将数据库密码提交到Git
- 定期更换API密钥和Webhook密钥
- 使用只读权限的API Key（如果只需要监控）
- 生产环境使用HTTPS

## �� 许可证

MIT License

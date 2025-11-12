# OKX Webhook监控系统 - 完整部署指南

## 📋 系统架构

```
A服务器 (监控服务器)                    B服务器 (业务服务器)
┌─────────────────────┐                ┌─────────────────────┐
│                     │                │                     │
│  OKX API            │                │  Webhook接收器      │
│    ↓                │                │    ↓                │
│  监控程序           │   Webhook      │  业务逻辑处理       │
│    ↓                │  =========>    │    ↓                │
│  MySQL数据库        │   (HMAC签名)   │  你的业务系统       │
│                     │                │                     │
└─────────────────────┘                └─────────────────────┘
```

## 🚀 A服务器部署步骤

### 1. 安装依赖

```bash
# 安装Python依赖
pip3 install pymysql requests flask

# 或使用requirements.txt
pip3 install -r requirements.txt
```

### 2. 准备MySQL数据库

```bash
# 登录MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE okx_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 创建用户（可选）
CREATE USER 'okx_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON okx_monitor.* TO 'okx_user'@'localhost';
FLUSH PRIVILEGES;

# 退出
EXIT;
```

### 3. 运行配置向导

```bash
# 第一次运行，配置所有参数
python3 config_manager.py
```

配置向导会要求你输入：

1. **MySQL数据库信息**
   - 数据库地址 (默认: localhost)
   - 数据库端口 (默认: 3306)
   - 数据库用户名 (默认: root)
   - 数据库密码
   - 数据库名 (默认: okx_monitor)

2. **OKX API信息**
   - API Key
   - Secret Key
   - Passphrase
   - 是否为模拟盘

3. **Webhook配置**
   - Webhook URL (B服务器接收地址)
   - Webhook Secret (签名密钥)

### 4. 启动监控程序

```bash
# 方式1: 使用环境变量
export DB_PASSWORD='your_mysql_password'
python3 okx_webhook_monitor.py

# 方式2: 使用命令行参数
python3 okx_webhook_monitor.py 'your_mysql_password'

# 方式3: 使用nohup后台运行
export DB_PASSWORD='your_mysql_password'
nohup python3 okx_webhook_monitor.py > monitor.log 2>&1 &

# 查看日志
tail -f monitor.log
```

### 5. 设置开机自启（可选）

创建systemd服务文件：

```bash
sudo nano /etc/systemd/system/okx-monitor.service
```

内容：

```ini
[Unit]
Description=OKX Transfer Monitor
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/uzf/uzf
Environment="DB_PASSWORD=your_mysql_password"
ExecStart=/usr/bin/python3 /www/wwwroot/uzf/uzf/okx_webhook_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable okx-monitor
sudo systemctl start okx-monitor

# 查看状态
sudo systemctl status okx-monitor

# 查看日志
sudo journalctl -u okx-monitor -f
```

---

## 🎯 B服务器部署步骤

### 1. 安装依赖

```bash
pip3 install flask
```

### 2. 配置Webhook接收器

编辑 `b_server_example.py`：

```python
# 修改这个密钥，必须与A服务器配置的相同
WEBHOOK_SECRET = "your_webhook_secret_key_here"
```

### 3. 启动Webhook接收器

```bash
# 开发环境
python3 b_server_example.py

# 生产环境（使用gunicorn）
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 b_server_example:app

# 后台运行
nohup gunicorn -w 4 -b 0.0.0.0:5000 b_server_example:app > webhook.log 2>&1 &
```

### 4. 测试Webhook接收

```bash
# 健康检查
curl http://your-b-server.com:5000/api/health
```

---

## 🔐 签名验证机制

### A服务器（发送方）

1. 将转账数据转换为JSON字符串（按key排序）
2. 使用HMAC-SHA256算法，用`WEBHOOK_SECRET`对JSON字符串签名
3. 将签名放在HTTP请求头 `X-Webhook-Signature` 中
4. 将当前时间戳放在 `X-Webhook-Timestamp` 中

### B服务器（接收方）

1. 接收到请求后，获取请求体和请求头中的签名
2. 使用相同的`WEBHOOK_SECRET`对请求体计算签名
3. 比较计算出的签名与请求头中的签名是否一致
4. 检查时间戳是否在有效期内（默认5分钟）

### 签名示例

```python
import hmac
import hashlib
import json

# 数据
data = {
    "bill_id": "123456",
    "amount": "100.5",
    "currency": "USDT"
}

# 转换为JSON（按key排序）
payload = json.dumps(data, sort_keys=True)

# 计算签名
secret = "your_webhook_secret_key"
signature = hmac.new(
    bytes(secret, encoding='utf8'),
    bytes(payload, encoding='utf-8'),
    digestmod=hashlib.sha256
).hexdigest()

print(f"Signature: {signature}")
```

---

## 📊 数据库表结构

### okx_config 配置表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| config_key | VARCHAR(50) | 配置键 |
| config_value | TEXT | 配置值 |
| config_type | VARCHAR(20) | 配置类型 |
| description | VARCHAR(200) | 配置描述 |
| is_encrypted | TINYINT | 是否加密 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### okx_transfers 转账记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| bill_id | VARCHAR(50) | 账单ID（唯一） |
| amount | DECIMAL(20,8) | 转账金额 |
| currency | VARCHAR(20) | 币种 |
| balance | DECIMAL(20,8) | 当前余额 |
| transfer_type | VARCHAR(50) | 转账类型 |
| sub_type | VARCHAR(10) | 子类型代码 |
| bill_timestamp | BIGINT | 账单时间戳 |
| bill_time | DATETIME | 账单时间 |
| monitor_timestamp | BIGINT | 监控时间戳 |
| monitor_time | DATETIME | 监控时间 |
| webhook_status | TINYINT | Webhook状态 (0=未推送 1=成功 2=失败) |
| webhook_response | TEXT | Webhook响应 |
| created_at | TIMESTAMP | 创建时间 |

---

## 🔧 常用命令

### A服务器

```bash
# 查看监控进程
ps aux | grep okx_webhook_monitor

# 停止监控
kill -9 $(ps aux | grep "okx_webhook_monitor" | grep -v grep | awk '{print $2}')

# 查看日志
tail -f monitor.log

# 重新配置
python3 config_manager.py

# 查看数据库记录
mysql -u root -p okx_monitor -e "SELECT * FROM okx_transfers ORDER BY id DESC LIMIT 10;"
```

### B服务器

```bash
# 查看接收日志
tail -f received_transfers.log

# 测试Webhook
curl -X POST http://localhost:5000/api/webhook/transfer \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: test" \
  -H "X-Webhook-Timestamp: $(date +%s)000" \
  -d '{"bill_id":"test","amount":"100"}'
```

---

## ❓ 常见问题

### 1. 数据库连接失败

```bash
# 检查MySQL是否运行
systemctl status mysql

# 检查数据库是否存在
mysql -u root -p -e "SHOW DATABASES;"

# 检查用户权限
mysql -u root -p -e "SHOW GRANTS FOR 'root'@'localhost';"
```

### 2. Webhook推送失败

- 检查B服务器是否可访问
- 检查防火墙设置
- 检查Webhook Secret是否一致
- 查看数据库中的 `webhook_response` 字段

### 3. 重新配置

```bash
# 删除旧配置
mysql -u root -p okx_monitor -e "DELETE FROM okx_config;"

# 重新运行配置向导
python3 config_manager.py
```

---

## 📝 Webhook数据格式

### 请求示例

```http
POST /api/webhook/transfer HTTP/1.1
Host: your-b-server.com
Content-Type: application/json
X-Webhook-Signature: a1b2c3d4e5f6...
X-Webhook-Timestamp: 1699876543210

{
    "bill_id": "3014552990502871040",
    "amount": "146.13",
    "currency": "USDT",
    "balance": "1788.06",
    "transfer_type": "转入",
    "sub_type": "11",
    "bill_timestamp": 1762343080077,
    "bill_time": "2025-11-05 19:44:40",
    "monitor_timestamp": 1762922891742,
    "monitor_time": "2025-11-12 12:48:11"
}
```

### 响应示例

```json
{
    "success": true,
    "message": "转账通知已接收",
    "bill_id": "3014552990502871040"
}
```

---

## 🎉 完成

现在你的系统已经完全配置好了！

- ✅ A服务器监控OKX转账
- ✅ 自动保存到MySQL数据库
- ✅ 通过Webhook推送到B服务器
- ✅ 使用HMAC-SHA256签名验证
- ✅ 配置信息安全存储在数据库

有任何问题请查看日志文件或数据库记录！


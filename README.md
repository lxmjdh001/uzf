# OKX 支付监控系统 - USDT支付系统

一个轻量级的 OKX 支付监控解决方案，使用JSON文件存储转账记录，支持签名验证的查询接口。

## 🎯 系统架构

```
A服务器 (监控服务器)                    B服务器 (业务服务器)
┌─────────────────────┐                ┌─────────────────────┐
│  OKX Monitor         │                │  用户下单           │
│    ↓                 │                │    ↓                │
│  转账记录            │                │  等待支付           │
│    ↓                 │                │    ↓                │
│  JSON 文件           │  查询请求      │  查询API            │
│  (2小时有效)         │  <========     │  (带签名验证)       │
│    ↓                 │  ========>     │    ↓                │
│  Query API           │  返回结果      │  验证支付           │
│  (签名验证)          │                │    ↓                │
│                      │                │  完成订单           │
└─────────────────────┘                └─────────────────────┘
```

## ✨ 核心特点

### 简化架构
- ✅ **无数据库依赖** - 使用JSON文件存储，部署简单
- ✅ **自动过期** - 只保留近2小时的转账记录
- ✅ **实时监控** - 定期查询OKX API并更新JSON
- ✅ **签名验证** - HMAC-SHA256确保查询安全
- ✅ **独立服务** - A服务器监控，B服务器按需查询

### 工作流程
1. **A服务器** - 运行`okx_monitor.py`持续监控OKX转账，保存到JSON
2. **A服务器** - 运行`query_api.py`提供带签名验证的查询接口
3. **B服务器** - 用户支付后，调用A服务器API查询是否到账
4. **自动清理** - 超过2小时的记录自动过滤，JSON文件始终保持最新

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

requirements.txt:
```
requests
Flask
pymysql
urllib3
```

### 2. 配置文件

复制示例配置并修改：

```bash
cp config.json.example config.json
nano config.json
```

config.json 配置说明：

```json
{
  "okx": {
    "api_key": "your_okx_api_key",           // OKX API Key
    "secret_key": "your_okx_secret_key",     // OKX Secret Key
    "passphrase": "your_okx_passphrase",     // OKX API密码
    "is_demo": false                          // 是否模拟盘
  },
  "monitor": {
    "interval": 10,                           // 监控间隔（秒）
    "json_file": "okx_transfers.json"        // JSON存储文件
  },
  "query_api": {
    "host": "0.0.0.0",                       // API监听地址
    "port": 6000,                             // API端口
    "secret": "your_secret_key_change_this"  // 查询API密钥（重要！）
  }
}
```

### 3. 启动A服务器

#### 方式1: 终端运行（测试用）

```bash
# 终端1: 启动监控服务
python3 okx_monitor.py

# 终端2: 启动查询API
python3 query_api.py
```

#### 方式2: 后台运行（生产环境）

```bash
# 启动监控服务
nohup python3 okx_monitor.py > monitor.log 2>&1 &

# 启动查询API
nohup python3 query_api.py > query_api.log 2>&1 &

# 查看进程
ps aux | grep python3

# 查看日志
tail -f monitor.log
tail -f query_api.log
```

### 4. B服务器集成

#### 方式1: 直接使用示例代码

```bash
# 查看使用示例
python3 b_server_query_example.py

# 启动Flask服务
python3 b_server_query_example.py flask
```

#### 方式2: 集成到你的项目

```python
from b_server_query_example import OKXPaymentChecker

# 配置
A_SERVER_URL = "http://192.168.1.100:6000"
API_SECRET = "your_secret_key_change_this"

# 创建检查器
checker = OKXPaymentChecker(A_SERVER_URL, API_SECRET)

# 检查支付
result = checker.check_payment(88.02, 'USDT')

if result['success'] and result['data']['found']:
    print("✓ 支付已到账!")
    transfer = result['data']['transfer']
    print(f"金额: {transfer['amount']} {transfer['currency']}")
    print(f"时间: {transfer['bill_time']}")
else:
    print("⚠️ 支付未到账")
```

## 📁 文件说明

### A服务器文件

- **okx_monitor.py** - OKX监控服务（读取OKX API → 写入JSON）
- **query_api.py** - 查询API服务（读取JSON → 返回给B服务器）
- **config.json** - 配置文件（包含OKX API密钥和查询API密钥）
- **okx_transfers.json** - 转账记录存储文件（自动生成）

### B服务器文件

- **b_server_query_example.py** - B服务器示例代码
  - 包含签名生成
  - 包含查询函数
  - 包含Flask集成示例

### 配置文件

- **config.json.example** - 配置文件示例

## 🔌 API接口文档

### 1. 查询转账记录

**接口**: `GET/POST /api/query`

**参数**:
- `amount` (可选) - 精确金额查询
- `currency` (可选) - 币种，默认USDT
- `min_amount` (可选) - 最小金额
- `max_amount` (可选) - 最大金额
- `signature` (必需) - 请求签名
- `timestamp` (必需) - 请求时间戳

**签名算法**:
```python
# 1. 参数按字母排序
sorted_params = sorted(params.items())
param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

# 2. 拼接签名字符串
sign_str = f"{param_str}&timestamp={timestamp}&secret={API_SECRET}"

# 3. 计算HMAC-SHA256
signature = hmac.new(
    bytes(API_SECRET, encoding='utf8'),
    bytes(sign_str, encoding='utf-8'),
    digestmod=hashlib.sha256
).hexdigest()
```

**返回示例**:
```json
{
  "success": true,
  "data": {
    "last_update": "2025-11-15 12:30:00",
    "last_update_timestamp": 1731650400,
    "transfers": [
      {
        "bill_id": "3020596814559830016",
        "amount": 88.02,
        "currency": "USDT",
        "balance": 1250.50,
        "transfer_type": "转入",
        "bill_timestamp": 1731648000000,
        "bill_time": "2025-11-15 12:00:00",
        "monitor_timestamp": 1731648010,
        "monitor_time": "2025-11-15 12:00:10"
      }
    ],
    "count": 1,
    "total_count": 10
  }
}
```

### 2. 快速检查支付

**接口**: `GET /api/check`

**参数**:
- `amount` (必需) - 金额
- `currency` (可选) - 币种，默认USDT
- `signature` (必需) - 请求签名
- `timestamp` (必需) - 请求时间戳

**返回示例**:
```json
{
  "success": true,
  "data": {
    "found": true,
    "transfer": {
      "bill_id": "3020596814559830016",
      "amount": 88.02,
      "currency": "USDT",
      "bill_time": "2025-11-15 12:00:00"
    }
  }
}
```

### 3. 健康检查

**接口**: `GET /health`

**返回**:
```json
{
  "status": "ok",
  "service": "okx-query-api",
  "timestamp": 1731650400
}
```

## 🔐 安全特性

1. **签名验证** - HMAC-SHA256签名，防止未授权访问
2. **时间戳验证** - 30分钟内有效，防止重放攻击
3. **密钥隔离** - OKX API密钥只在A服务器，B服务器只需查询密钥
4. **自动过期** - 只保留2小时记录，减少数据泄露风险

## 🔧 常用命令

```bash
# 查看监控进程
ps aux | grep okx_monitor
ps aux | grep query_api

# 查看日志
tail -f monitor.log
tail -f query_api.log

# 查看JSON数据
cat okx_transfers.json | python3 -m json.tool

# 停止服务
pkill -f okx_monitor.py
pkill -f query_api.py

# 测试查询API
curl http://localhost:6000/health
```

## 📊 JSON文件格式

okx_transfers.json 格式：

```json
{
  "last_update": "2025-11-15 12:30:00",
  "last_update_timestamp": 1731650400,
  "count": 5,
  "transfers": [
    {
      "bill_id": "3020596814559830016",
      "amount": 88.02,
      "currency": "USDT",
      "balance": 1250.50,
      "transfer_type": "转入",
      "bill_timestamp": 1731648000000,
      "bill_time": "2025-11-15 12:00:00",
      "bill_time_utc": "2025-11-15T04:00:00+00:00",
      "monitor_timestamp": 1731648010,
      "monitor_time": "2025-11-15 12:00:10"
    }
  ]
}
```

## 🆚 新旧版本对比

| 特性 | 旧版本 | 新版本 (JSON) |
|------|--------|---------------|
| 数据存储 | MySQL数据库 | JSON文件 |
| 部署复杂度 | 高（需要MySQL） | 低（无数据库依赖） |
| 工作模式 | B服务器推送订单到A服务器 | B服务器查询A服务器 |
| 回调机制 | A服务器主动回调B服务器 | 无回调，B服务器主动查询 |
| 数据保留 | 永久保存 | 只保留2小时 |
| 适用场景 | 需要完整历史记录 | 只需验证近期支付 |

## ⚠️ 注意事项

1. **网络安全**
   - 生产环境建议使用HTTPS
   - 防火墙只开放必要端口
   - 定期更换API密钥

2. **性能优化**
   - 监控间隔建议10-30秒
   - JSON文件会自动清理，无需担心过大

3. **时区问题**
   - OKX API返回UTC时间
   - 代码已自动处理时区转换

4. **错误处理**
   - 建议监控日志文件
   - 网络异常会自动重试

## 🔄 迁移指南

从旧版本（MySQL版本）迁移：

1. **备份旧数据**（可选）
```bash
mysqldump -u root -p okx_monitor > backup.sql
```

2. **停止旧服务**
```bash
pkill -f payment_monitor.py
```

3. **部署新服务**
```bash
# 创建配置文件
cp config.json.example config.json
nano config.json

# 启动新服务
python3 okx_monitor.py &
python3 query_api.py &
```

4. **更新B服务器代码**
   - 替换为新的查询方式
   - 参考 `b_server_query_example.py`

## 📝 使用示例

### 示例1: 用户支付验证

```python
# B服务器代码
from b_server_query_example import OKXPaymentChecker

checker = OKXPaymentChecker("http://a-server:6000", "your_secret")

# 用户下单
order_id = "ORDER123456"
amount = 88.02
currency = "USDT"

# 生成支付信息
print(f"请向OKX账户转账: {amount} {currency}")

# 轮询检查支付（用户支付后）
import time
for i in range(60):  # 最多检查5分钟
    result = checker.check_payment(amount, currency)

    if result['success'] and result['data']['found']:
        print("✓ 支付已到账!")
        # 处理订单...
        break

    time.sleep(5)  # 每5秒检查一次
else:
    print("⚠️ 支付超时")
```

### 示例2: 批量查询

```python
# 查询所有USDT转账
result = checker.query_transfers(currency='USDT')

if result['success']:
    for transfer in result['data']['transfers']:
        print(f"{transfer['amount']} {transfer['currency']} - {transfer['bill_time']}")
```

## 📞 技术支持

如有问题，请检查：
1. 配置文件是否正确
2. OKX API密钥是否有效
3. 网络是否正常
4. 日志文件中的错误信息

## 📄 许可证

MIT License

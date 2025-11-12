# OKX账户交易资金变动监控工具 - 项目总结

## 📋 项目概述

本项目是一个基于Python的OKX交易所账户资金变动监控工具,通过OKX官方API实时监控账户交易记录,重点关注资金变动情况。

## 🎯 核心功能

### 已实现功能

✅ **实时监控** - 持续监控账户资金变动  
✅ **详细记录** - 记录监控时间戳、变动金额、产生时间  
✅ **类型识别** - 自动识别账单类型(交易、划转、资金费等)  
✅ **数据保存** - 支持保存到JSON文件和SQLite数据库  
✅ **过滤功能** - 支持按产品类型和金额过滤  
✅ **通知功能** - 支持钉钉、企业微信、Webhook通知  
✅ **安全认证** - 完整的API签名验证机制  

## 📁 文件结构

```
uzf/
├── okx_monitor.py              # 基础版监控脚本
├── okx_monitor_advanced.py     # 高级版监控脚本(支持数据保存)
├── test_connection.py          # API连接测试工具
├── examples.py                 # 扩展功能示例
├── config_example.py           # 配置文件示例
├── requirements.txt            # Python依赖
├── README.md                   # 详细文档
├── QUICKSTART.md              # 快速开始指南
├── PROJECT_SUMMARY.md         # 项目总结(本文件)
└── .gitignore                 # Git忽略文件
```

## 🔧 技术实现

### API接口

- **主要接口**: `/api/v5/account/bills` (账单流水查询)
- **认证方式**: HMAC-SHA256签名
- **限速**: 6次/秒
- **数据范围**: 近7天

### 核心技术

- **语言**: Python 3.x
- **HTTP库**: requests
- **签名算法**: HMAC-SHA256 + Base64
- **数据格式**: JSON

### 关键实现

1. **签名生成**
```python
message = timestamp + method + request_path + body
signature = base64.b64encode(
    hmac.new(secret_key, message, hashlib.sha256).digest()
)
```

2. **去重机制**
```python
if self.last_bill_id and bill_id <= self.last_bill_id:
    continue
self.last_bill_id = bill_id
```

3. **数据处理**
```python
result = {
    'monitor_timestamp': int(time.time() * 1000),
    'bill_timestamp': bill.get('ts'),
    'amount': bill.get('balChg'),
    'currency': bill.get('ccy'),
    # ...
}
```

## 📊 数据输出格式

### 控制台输出

```
================================================================================
【资金变动监控】
监控时间戳: 1699876543210
监控时间: 2024-11-12 15:30:45
账单产生时间: 2024-11-12 15:30:40
账单时间戳: 1699876540000
变动金额: -0.5 USDT
当前余额: 1000.5 USDT
交易产品: BTC-USDT
账单类型: 交易 - 买入
账单ID: 123456789
================================================================================
```

### JSON格式

```json
{
  "monitor_timestamp": 1699876543210,
  "monitor_time": "2024-11-12 15:30:45",
  "bill_timestamp": "1699876540000",
  "bill_time": "2024-11-12 15:30:40",
  "amount": "-0.5",
  "currency": "USDT",
  "balance": "1000.5",
  "inst_id": "BTC-USDT",
  "type": "交易 - 买入",
  "bill_id": "123456789"
}
```

## 🚀 使用流程

### 1. 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 测试API连接
python test_connection.py

# 启动监控
python okx_monitor.py
```

### 2. 配置说明

在 `okx_monitor.py` 中配置:

```python
API_KEY = "your_api_key"
SECRET_KEY = "your_secret_key"
PASSPHRASE = "your_passphrase"
MONITOR_INTERVAL = 10  # 监控间隔(秒)
INST_TYPE = None       # 产品类型过滤
```

### 3. 扩展功能

参考 `examples.py` 实现:
- 数据库保存
- 通知推送
- 交易策略触发

## 📈 支持的账单类型

| 类型代码 | 说明 | 类型代码 | 说明 |
|---------|------|---------|------|
| 1 | 划转 | 15 | 一键借币 |
| 2 | 交易 | 16 | 手动借币 |
| 3 | 交割 | 17 | 一键还币 |
| 4 | 自动换币 | 18 | 手动还币 |
| 5 | 强平 | 19 | 自动还币 |
| 6 | 保证金划转 | 20 | 借币利息 |
| 7 | 扣息 | 22 | 买入 |
| 8 | 资金费 | 23 | 卖出 |
| 9 | 自动减仓 | 24 | 开多 |
| 10 | 穿仓补偿 | 25 | 开空 |
| 11 | 系统换币 | 26 | 平多 |
| 12 | 策略划转 | 27 | 平空 |
| 13 | 对冲减仓 | - | - |
| 14 | 大宗交易 | - | - |

## 🔒 安全建议

### API权限设置

- ✅ **读取权限** - 必须
- ❌ **交易权限** - 不需要
- ❌ **提币权限** - 不需要

### 安全措施

1. 使用IP白名单限制访问
2. 定期更换API密钥
3. 不要上传包含真实API信息的代码
4. 使用环境变量或配置文件存储敏感信息
5. 启用.gitignore保护配置文件

## 📝 扩展示例

### 1. 钉钉通知

```python
from examples import send_dingtalk_notification

def callback(bill_data):
    send_dingtalk_notification(
        bill_data,
        webhook_url="https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
    )
```

### 2. 数据库保存

```python
from examples import save_to_database

def callback(bill_data):
    save_to_database(bill_data, db_path='okx_bills.db')
```

### 3. 交易策略

```python
from examples import trigger_trading_strategy

def callback(bill_data):
    trigger_trading_strategy(bill_data)
```

## 🐛 常见问题

### 1. 签名错误

**问题**: `Invalid signature`  
**解决**: 检查API Key、Secret Key、Passphrase是否正确,确认系统时间准确

### 2. 权限错误

**问题**: `Permission denied`  
**解决**: 确认API Key具有读取权限

### 3. 限速错误

**问题**: `Rate limit exceeded`  
**解决**: 增加监控间隔时间

### 4. 无数据

**问题**: 没有监控到任何数据  
**解决**: 检查账户是否有交易记录,调整产品类型过滤

## 📚 参考文档

- [OKX API官方文档](https://www.okx.com/docs-v5/zh/)
- [账单流水接口](https://www.okx.com/docs-v5/zh/#trading-account-rest-api-get-bills-details-last-7-days)
- [REST API认证](https://www.okx.com/docs-v5/zh/#overview-rest-authentication)

## 🎓 学习要点

### Python技能

- HTTP请求处理
- HMAC签名算法
- JSON数据处理
- 异步轮询机制
- 文件I/O操作

### API对接

- REST API调用
- 签名认证机制
- 错误处理
- 限速控制
- 数据解析

### 实战经验

- 实时数据监控
- 去重机制设计
- 日志记录
- 异常处理
- 扩展性设计

## 🔮 未来扩展

### 可能的改进方向

1. **WebSocket支持** - 使用WebSocket实现真正的实时推送
2. **多账户监控** - 同时监控多个OKX账户
3. **数据分析** - 添加资金流向分析和统计功能
4. **可视化界面** - 开发Web界面展示监控数据
5. **智能告警** - 基于规则的智能告警系统
6. **策略回测** - 基于历史数据的策略回测功能

## 📄 许可证

MIT License

## 🙏 致谢

- OKX官方API文档
- Python requests库
- 开源社区

---

**项目创建时间**: 2024-11-12  
**最后更新**: 2024-11-12  
**版本**: 1.0.0


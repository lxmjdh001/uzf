# 快速开始指南

## 5分钟快速上手

### 步骤1: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤2: 获取OKX API密钥

1. 访问 [OKX官网](https://www.okx.com) 并登录
2. 进入 **个人中心** → **API管理**
3. 点击 **创建API Key**
4. 设置以下权限:
   - ✅ **读取** (必须)
   - ❌ 交易 (不需要)
   - ❌ 提币 (不需要)
5. 记录以下信息:
   - **API Key**
   - **Secret Key** (只显示一次!)
   - **Passphrase** (你设置的密码)

### 步骤3: 测试API连接

运行测试脚本验证API配置:

```bash
python test_connection.py
```

按提示输入你的API信息,如果看到 "✓ 所有测试通过!" 说明配置正确。

### 步骤4: 配置监控脚本

编辑 `okx_monitor.py` 文件,找到 `main()` 函数中的配置区:

```python
# ==================== 配置区 ====================
API_KEY = "your_api_key_here"          # 替换为你的API Key
SECRET_KEY = "your_secret_key_here"    # 替换为你的Secret Key
PASSPHRASE = "your_passphrase_here"    # 替换为你的Passphrase
IS_DEMO = False                         # True=模拟盘, False=实盘

# 监控配置
MONITOR_INTERVAL = 10  # 监控间隔(秒)
INST_TYPE = None       # 产品类型: None=全部, "SPOT"=币币, "SWAP"=合约
# ===============================================
```

### 步骤5: 启动监控

```bash
python okx_monitor.py
```

## 输出示例

```
开始监控OKX账户资金变动...
监控间隔: 10秒
产品类型: 全部
--------------------------------------------------------------------------------

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

## 高级功能

### 使用高级版本(支持数据保存)

```bash
python okx_monitor_advanced.py
```

高级版本会自动保存数据到:
- `data/bills_YYYY-MM-DD.jsonl` - 每日账单数据
- `logs/monitor_YYYY-MM-DD.log` - 监控日志

### 只监控特定类型的交易

编辑配置,设置 `INST_TYPE`:

```python
INST_TYPE = "SPOT"    # 只监控币币交易
# 或
INST_TYPE = "SWAP"    # 只监控永续合约
```

### 过滤小额变动

在高级版本中,可以设置金额过滤:

```python
FILTER_AMOUNT = 1.0  # 只显示变动金额 > 1.0 的记录
```

## 常见问题

### Q1: 提示 "Invalid signature" 错误?

**A:** 检查以下几点:
1. API Key、Secret Key、Passphrase 是否正确
2. 系统时间是否准确(误差不能超过30秒)
3. 是否有多余的空格

### Q2: 提示 "Permission denied" 错误?

**A:** 确认API Key具有 **读取** 权限

### Q3: 没有监控到任何数据?

**A:** 可能原因:
1. 账户最近7天没有交易记录
2. 监控间隔太长,错过了新记录
3. 产品类型过滤太严格

### Q4: 如何停止监控?

**A:** 按 `Ctrl+C` 停止

## 数据说明

### 返回字段

| 字段 | 说明 | 示例 |
|------|------|------|
| monitor_timestamp | 监控时间戳(毫秒) | 1699876543210 |
| monitor_time | 监控时间 | 2024-11-12 15:30:45 |
| bill_timestamp | 账单时间戳(毫秒) | 1699876540000 |
| bill_time | 账单时间 | 2024-11-12 15:30:40 |
| amount | 变动金额 | -0.5 |
| currency | 币种 | USDT |
| balance | 当前余额 | 1000.5 |
| inst_id | 交易产品 | BTC-USDT |
| type | 账单类型 | 交易 - 买入 |

### 账单类型

- **交易** - 买入/卖出/开多/开空/平多/平空
- **划转** - 账户间资金划转
- **资金费** - 永续合约资金费用
- **借币/还币** - 杠杆借币和还币
- **利息** - 借币利息

## 安全建议

⚠️ **重要提示:**

1. **不要分享** 你的API Key和Secret Key
2. **只授予读取权限**,不要授予交易和提币权限
3. **使用IP白名单** 限制API访问
4. **定期更换** API密钥
5. **不要上传** 包含真实API信息的代码到公开仓库

## 下一步

- 查看 [README.md](README.md) 了解更多功能
- 修改 `_process_bill()` 方法实现自定义逻辑
- 添加邮件/Webhook通知功能
- 集成到你的交易策略中

## 技术支持

- [OKX API官方文档](https://www.okx.com/docs-v5/zh/)
- [账单流水接口文档](https://www.okx.com/docs-v5/zh/#trading-account-rest-api-get-bills-details-last-7-days)

---

祝你使用愉快! 🚀


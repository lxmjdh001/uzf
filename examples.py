#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX监控扩展示例
展示如何添加自定义功能
"""

import json
import requests
from typing import Dict


# ============================================================================
# 示例1: 发送Webhook通知
# ============================================================================

def send_webhook_notification(bill_data: Dict, webhook_url: str):
    """
    发送Webhook通知
    
    Args:
        bill_data: 账单数据
        webhook_url: Webhook URL
    """
    try:
        payload = {
            "text": f"OKX资金变动提醒",
            "attachments": [{
                "color": "good" if float(bill_data['amount']) > 0 else "danger",
                "fields": [
                    {"title": "监控时间", "value": bill_data['monitor_time'], "short": True},
                    {"title": "账单时间", "value": bill_data['bill_time'], "short": True},
                    {"title": "变动金额", "value": f"{bill_data['amount']} {bill_data['currency']}", "short": True},
                    {"title": "当前余额", "value": f"{bill_data['balance']} {bill_data['currency']}", "short": True},
                    {"title": "交易产品", "value": bill_data['inst_id'] or 'N/A', "short": True},
                    {"title": "账单类型", "value": bill_data['type'], "short": True},
                ]
            }]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✓ Webhook通知已发送")
        else:
            print(f"✗ Webhook发送失败: {response.status_code}")
    except Exception as e:
        print(f"✗ Webhook发送异常: {str(e)}")


# ============================================================================
# 示例2: 发送钉钉机器人通知
# ============================================================================

def send_dingtalk_notification(bill_data: Dict, webhook_url: str, secret: str = None):
    """
    发送钉钉机器人通知
    
    Args:
        bill_data: 账单数据
        webhook_url: 钉钉机器人Webhook URL
        secret: 钉钉机器人加签密钥(可选)
    """
    try:
        import time
        import hmac
        import hashlib
        import base64
        from urllib.parse import quote_plus
        
        # 如果有加签,生成签名
        if secret:
            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = '{}\n{}'.format(timestamp, secret)
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = quote_plus(base64.b64encode(hmac_code))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
        # 构建消息
        amount_float = float(bill_data['amount'])
        emoji = "📈" if amount_float > 0 else "📉"
        color = "green" if amount_float > 0 else "red"
        
        message = f"""## {emoji} OKX资金变动提醒
        
**监控时间:** {bill_data['monitor_time']}  
**账单时间:** {bill_data['bill_time']}  
**变动金额:** <font color='{color}'>{bill_data['amount']} {bill_data['currency']}</font>  
**当前余额:** {bill_data['balance']} {bill_data['currency']}  
**交易产品:** {bill_data['inst_id'] or 'N/A'}  
**账单类型:** {bill_data['type']}  
**账单ID:** {bill_data['bill_id']}
"""
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "OKX资金变动",
                "text": message
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✓ 钉钉通知已发送")
            else:
                print(f"✗ 钉钉通知失败: {result.get('errmsg')}")
        else:
            print(f"✗ 钉钉通知发送失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 钉钉通知异常: {str(e)}")


# ============================================================================
# 示例3: 发送企业微信通知
# ============================================================================

def send_wecom_notification(bill_data: Dict, webhook_url: str):
    """
    发送企业微信机器人通知
    
    Args:
        bill_data: 账单数据
        webhook_url: 企业微信机器人Webhook URL
    """
    try:
        amount_float = float(bill_data['amount'])
        color = "info" if amount_float > 0 else "warning"
        
        message = f"""OKX资金变动提醒
>监控时间: <font color="comment">{bill_data['monitor_time']}</font>
>账单时间: <font color="comment">{bill_data['bill_time']}</font>
>变动金额: <font color="{color}">{bill_data['amount']} {bill_data['currency']}</font>
>当前余额: {bill_data['balance']} {bill_data['currency']}
>交易产品: {bill_data['inst_id'] or 'N/A'}
>账单类型: {bill_data['type']}
"""
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": message
            }
        }
        
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✓ 企业微信通知已发送")
            else:
                print(f"✗ 企业微信通知失败: {result.get('errmsg')}")
        else:
            print(f"✗ 企业微信通知发送失败: {response.status_code}")
    except Exception as e:
        print(f"✗ 企业微信通知异常: {str(e)}")


# ============================================================================
# 示例4: 保存到数据库(SQLite)
# ============================================================================

def save_to_database(bill_data: Dict, db_path: str = 'okx_bills.db'):
    """
    保存账单到SQLite数据库
    
    Args:
        bill_data: 账单数据
        db_path: 数据库文件路径
    """
    try:
        import sqlite3
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建表(如果不存在)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bills (
                bill_id TEXT PRIMARY KEY,
                monitor_timestamp INTEGER,
                monitor_time TEXT,
                bill_timestamp TEXT,
                bill_time TEXT,
                amount TEXT,
                currency TEXT,
                balance TEXT,
                inst_id TEXT,
                type TEXT,
                bill_type TEXT,
                sub_type TEXT,
                raw_data TEXT
            )
        ''')
        
        # 插入数据
        cursor.execute('''
            INSERT OR REPLACE INTO bills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            bill_data['bill_id'],
            bill_data['monitor_timestamp'],
            bill_data['monitor_time'],
            bill_data['bill_timestamp'],
            bill_data['bill_time'],
            bill_data['amount'],
            bill_data['currency'],
            bill_data['balance'],
            bill_data['inst_id'],
            bill_data['type'],
            bill_data['bill_type'],
            bill_data['sub_type'],
            json.dumps(bill_data['raw_data'])
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✓ 数据已保存到数据库: {db_path}")
    except Exception as e:
        print(f"✗ 数据库保存失败: {str(e)}")


# ============================================================================
# 示例5: 触发交易策略
# ============================================================================

def trigger_trading_strategy(bill_data: Dict):
    """
    根据资金变动触发交易策略
    
    Args:
        bill_data: 账单数据
    """
    try:
        # 示例: 当检测到大额资金流入时触发策略
        amount = float(bill_data['amount'])
        currency = bill_data['currency']
        
        # 策略1: 大额USDT流入提醒
        if currency == 'USDT' and amount > 1000:
            print(f"⚠️ 检测到大额USDT流入: {amount} USDT")
            # 这里可以添加你的交易逻辑
            # 例如: 自动买入某个币种
            
        # 策略2: 检测到交易亏损
        if bill_data['bill_type'] == '2' and amount < 0:  # 类型2=交易
            print(f"⚠️ 检测到交易亏损: {amount} {currency}")
            # 这里可以添加止损逻辑
            
        # 策略3: 资金费监控
        if bill_data['bill_type'] == '8':  # 类型8=资金费
            print(f"💰 资金费: {amount} {currency}")
            # 这里可以添加资金费优化策略
            
    except Exception as e:
        print(f"✗ 策略执行异常: {str(e)}")


# ============================================================================
# 示例6: 综合回调函数
# ============================================================================

def comprehensive_callback(bill_data: Dict, config: Dict = None):
    """
    综合回调函数,整合多种功能
    
    Args:
        bill_data: 账单数据
        config: 配置字典,包含各种通知的配置信息
    """
    if config is None:
        config = {}
    
    # 1. 保存到数据库
    if config.get('save_to_db'):
        save_to_database(bill_data, config.get('db_path', 'okx_bills.db'))
    
    # 2. 发送通知(根据金额阈值)
    amount = abs(float(bill_data['amount']))
    threshold = config.get('notification_threshold', 0)
    
    if amount >= threshold:
        # 钉钉通知
        if config.get('dingtalk_webhook'):
            send_dingtalk_notification(
                bill_data,
                config['dingtalk_webhook'],
                config.get('dingtalk_secret')
            )
        
        # 企业微信通知
        if config.get('wecom_webhook'):
            send_wecom_notification(bill_data, config['wecom_webhook'])
        
        # 自定义Webhook
        if config.get('custom_webhook'):
            send_webhook_notification(bill_data, config['custom_webhook'])
    
    # 3. 触发交易策略
    if config.get('enable_strategy'):
        trigger_trading_strategy(bill_data)


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    # 模拟账单数据
    sample_bill = {
        'monitor_timestamp': 1699876543210,
        'monitor_time': '2024-11-12 15:30:45',
        'bill_timestamp': '1699876540000',
        'bill_time': '2024-11-12 15:30:40',
        'amount': '-0.5',
        'currency': 'USDT',
        'balance': '1000.5',
        'inst_id': 'BTC-USDT',
        'type': '交易 - 买入',
        'bill_type': '2',
        'sub_type': '1',
        'bill_id': '123456789',
        'raw_data': {}
    }
    
    print("="*80)
    print("OKX监控扩展功能示例")
    print("="*80)
    
    # 示例1: 保存到数据库
    print("\n[示例1] 保存到数据库")
    save_to_database(sample_bill)
    
    # 示例2: 触发交易策略
    print("\n[示例2] 触发交易策略")
    trigger_trading_strategy(sample_bill)
    
    # 示例3: 综合回调
    print("\n[示例3] 综合回调")
    config = {
        'save_to_db': True,
        'db_path': 'okx_bills.db',
        'notification_threshold': 0.1,
        'enable_strategy': True,
        # 'dingtalk_webhook': 'https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN',
        # 'wecom_webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY',
    }
    comprehensive_callback(sample_bill, config)
    
    print("\n" + "="*80)
    print("提示: 取消注释webhook配置以启用通知功能")
    print("="*80)


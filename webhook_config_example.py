#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook监控配置文件示例
复制此文件为 webhook_config.py 并填入真实配置
"""

# ==================== OKX API 配置 ====================
OKX_CONFIG = {
    'api_key': 'your_api_key_here',
    'secret_key': 'your_secret_key_here',
    'passphrase': 'your_passphrase_here',
    'is_demo': False  # True=模拟盘, False=实盘
}

# ==================== Webhook 配置 ====================
WEBHOOK_CONFIG = {
    # B服务器接收Webhook的地址
    'url': 'http://your-b-server.com/api/webhook/transfer',
    
    # Webhook签名密钥（A和B服务器需要使用相同的密钥）
    'secret': 'your_webhook_secret_key_here',
    
    # 推送超时时间（秒）
    'timeout': 10,
    
    # 推送失败重试次数
    'retry_times': 3
}

# ==================== MySQL 配置 ====================
DB_CONFIG = {
    'host': 'localhost',      # 数据库地址
    'port': 3306,             # 数据库端口
    'user': 'root',           # 数据库用户名
    'password': 'your_mysql_password',  # 数据库密码
    'database': 'okx_monitor',  # 数据库名
    'charset': 'utf8mb4'
}

# ==================== 监控配置 ====================
MONITOR_CONFIG = {
    'interval': 10,      # 监控间隔(秒)
    'min_amount': 0,     # 最小金额过滤，0表示不过滤
}


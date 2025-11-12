#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX API 配置文件示例
请复制此文件为 config.py 并填入你的真实API信息
"""

# OKX API 配置
OKX_CONFIG = {
    # API Key (在OKX网站创建)
    'api_key': 'your_api_key_here',
    
    # Secret Key (在OKX网站创建时显示,请妥善保管)
    'secret_key': 'your_secret_key_here',
    
    # API密码 (创建API Key时设置的密码)
    'passphrase': 'your_passphrase_here',
    
    # 是否为模拟盘 (True=模拟盘, False=实盘)
    'is_demo': False,
}

# 监控配置
MONITOR_CONFIG = {
    # 监控间隔(秒)
    'interval': 10,
    
    # 产品类型过滤
    # None = 全部
    # 'SPOT' = 币币交易
    # 'MARGIN' = 杠杆交易
    # 'SWAP' = 永续合约
    # 'FUTURES' = 交割合约
    # 'OPTION' = 期权
    'inst_type': None,
    
    # 每次查询的记录数量 (最大100)
    'limit': 10,
}


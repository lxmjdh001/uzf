#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX API 连接测试脚本
用于测试API配置是否正确
"""

import hmac
import base64
import hashlib
import requests
from datetime import datetime


def test_okx_connection(api_key: str, secret_key: str, passphrase: str, is_demo: bool = False):
    """
    测试OKX API连接
    
    Args:
        api_key: API Key
        secret_key: Secret Key
        passphrase: API密码
        is_demo: 是否为模拟盘
    """
    print("="*80)
    print("OKX API 连接测试")
    print("="*80)
    
    # API地址
    base_url = "https://www.okx.com"
    
    # 测试1: 获取系统时间(公共接口,不需要签名)
    print("\n[测试1] 获取系统时间...")
    try:
        response = requests.get(f"{base_url}/api/v5/public/time", timeout=10)
        data = response.json()
        if data.get('code') == '0':
            server_time = data['data'][0]['ts']
            print(f"✓ 服务器时间: {datetime.fromtimestamp(int(server_time)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"✗ 获取失败: {data.get('msg')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False
    
    # 测试2: 获取账户配置(需要签名)
    print("\n[测试2] 测试API签名和权限...")
    try:
        request_path = '/api/v5/account/config'
        from datetime import timezone
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

        # 生成签名
        message = timestamp + 'GET' + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('code') == '0':
            account_data = data['data'][0]
            print(f"✓ API签名验证成功")
            print(f"  账户等级: {account_data.get('acctLv', 'N/A')}")
            print(f"  持仓模式: {account_data.get('posMode', 'N/A')}")
            print(f"  自动借币: {account_data.get('autoLoan', 'N/A')}")
        else:
            print(f"✗ 验证失败: {data.get('msg')} (code: {data.get('code')})")
            if data.get('code') == '50111':
                print("  提示: API Key权限不足,请确保已授予读取权限")
            elif data.get('code') == '50113':
                print("  提示: 签名错误,请检查Secret Key和Passphrase是否正确")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False
    
    # 测试3: 获取账单流水
    print("\n[测试3] 测试账单流水查询...")
    try:
        request_path = '/api/v5/account/bills?limit=1'
        from datetime import timezone
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

        # 生成签名
        message = timestamp + 'GET' + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('code') == '0':
            bills = data.get('data', [])
            print(f"✓ 账单查询成功")
            print(f"  最近账单数量: {len(bills)}")
            if bills:
                bill = bills[0]
                print(f"  最新账单时间: {datetime.fromtimestamp(int(bill['ts'])/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  币种: {bill.get('ccy', 'N/A')}")
                print(f"  变动金额: {bill.get('balChg', 'N/A')}")
        else:
            print(f"✗ 查询失败: {data.get('msg')} (code: {data.get('code')})")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {str(e)}")
        return False
    
    print("\n" + "="*80)
    print("✓ 所有测试通过! API配置正确,可以开始监控")
    print("="*80)
    return True


def main():
    """主函数"""
    print("\n请输入你的OKX API信息:")
    print("-" * 80)
    
    api_key = input("API Key: ").strip()
    secret_key = input("Secret Key: ").strip()
    passphrase = input("Passphrase: ").strip()
    is_demo_input = input("是否为模拟盘? (y/n, 默认n): ").strip().lower()
    
    is_demo = is_demo_input == 'y'
    
    if not api_key or not secret_key or not passphrase:
        print("\n错误: API信息不能为空!")
        return
    
    print("\n开始测试...")
    test_okx_connection(api_key, secret_key, passphrase, is_demo)


if __name__ == "__main__":
    main()


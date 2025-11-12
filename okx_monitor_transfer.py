#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 转账监控专用脚本
只监控别人给你转账的记录（资金流入）
"""

import hmac
import base64
import hashlib
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional


class OKXTransferMonitor:
    """OKX 转账监控类"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, is_demo: bool = False):
        """
        初始化OKX转账监控器
        
        Args:
            api_key: API Key
            secret_key: Secret Key
            passphrase: API密码
            is_demo: 是否为模拟盘
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        # API地址
        self.base_url = "https://www.okx.com"
        self.last_bill_id = None
        
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        """获取请求头"""
        from datetime import timezone
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        return headers
    
    def get_bills(self, limit: int = 100) -> List[Dict]:
        """
        获取账单流水
        
        Args:
            limit: 返回结果数量
            
        Returns:
            账单列表
        """
        request_path = '/api/v5/account/bills'
        params = {'limit': str(limit)}
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_path = f"{request_path}?{query_string}"
        
        headers = self._get_headers('GET', full_path)
        url = self.base_url + full_path
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0':
                return data.get('data', [])
            else:
                print(f"API错误: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return []
        except Exception as e:
            print(f"请求失败: {str(e)}")
            return []
    
    def monitor_transfers(self, interval: int = 10, min_amount: float = 0):
        """
        持续监控转账（只监控资金流入）
        
        Args:
            interval: 监控间隔(秒)
            min_amount: 最小金额过滤，只显示大于此金额的转账
        """
        print("="*80)
        print("OKX 转账监控启动")
        print("="*80)
        print(f"监控间隔: {interval}秒")
        print(f"监控类型: 只监控转账流入（别人给你转账）")
        if min_amount > 0:
            print(f"金额过滤: 只显示 >= {min_amount} 的转账")
        print("-" * 80)
        
        while True:
            try:
                bills = self.get_bills(limit=20)
                
                if bills:
                    # 反转列表，从旧到新处理
                    bills.reverse()
                    
                    for bill in bills:
                        bill_id = bill.get('billId')
                        
                        # 去重：跳过已处理的账单
                        if self.last_bill_id and bill_id <= self.last_bill_id:
                            continue
                        
                        self.last_bill_id = bill_id
                        
                        # 过滤条件1: 只处理划转类型 (type='1')
                        bill_type = bill.get('type', '')
                        if bill_type != '1':
                            continue
                        
                        # 过滤条件2: 只处理资金流入（正数）
                        balance_change = float(bill.get('balChg', '0'))
                        if balance_change <= 0:
                            continue
                        
                        # 过滤条件3: 金额过滤
                        if balance_change < min_amount:
                            continue
                        
                        # 处理并显示转账记录
                        self._process_transfer(bill)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n" + "="*80)
                print("监控已停止")
                print("="*80)
                break
            except Exception as e:
                print(f"监控出错: {str(e)}")
                time.sleep(interval)
    
    def _process_transfer(self, bill: Dict):
        """处理单条转账记录"""
        # 当前监控时间戳
        monitor_timestamp = int(time.time() * 1000)
        monitor_time = datetime.fromtimestamp(monitor_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # 转账产生时间
        bill_timestamp = bill.get('ts', '')
        bill_time = datetime.fromtimestamp(int(bill_timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # 转账金额
        amount = bill.get('balChg', '0')
        currency = bill.get('ccy', '')
        balance = bill.get('bal', '0')
        
        # 子类型说明
        sub_type = bill.get('subType', '')
        sub_type_desc = self._get_subtype_description(sub_type)
        
        # 输出转账信息
        print(f"\n{'='*80}")
        print(f"🎉 检测到转账流入!")
        print(f"{'='*80}")
        print(f"监控时间戳: {monitor_timestamp}")
        print(f"监控时间: {monitor_time}")
        print(f"转账时间: {bill_time}")
        print(f"转账时间戳: {bill_timestamp}")
        print(f"转账金额: +{amount} {currency}")
        print(f"当前余额: {balance} {currency}")
        print(f"转账类型: {sub_type_desc}")
        print(f"账单ID: {bill.get('billId', '')}")
        print(f"{'='*80}")
    
    def _get_subtype_description(self, sub_type: str) -> str:
        """获取子类型描述"""
        subtype_map = {
            '1': '买入',
            '2': '卖出',
            '3': '开多',
            '4': '开空',
            '5': '平多',
            '6': '平空',
            '9': '市场借币转入',
            '11': '转入',
            '12': '转出',
            '160': '手动追加保证金',
            '161': '手动减少保证金',
            '162': '自动追加保证金',
            '114': '自动换币转入',
            '115': '自动换币转出',
            '118': '系统换币转入',
            '119': '系统换币转出',
            '100': '资金账户转入',
            '101': '资金账户转出',
            '102': '交易账户转入',
            '103': '交易账户转出',
        }
        
        return subtype_map.get(sub_type, f'划转 (子类型: {sub_type})')


def main():
    """主函数"""
    # ==================== 配置区 ====================
    API_KEY = "your_api_key_here"
    SECRET_KEY = "your_secret_key_here"
    PASSPHRASE = "your_passphrase_here"
    IS_DEMO = False
    
    # 监控配置
    MONITOR_INTERVAL = 10    # 监控间隔(秒)
    MIN_AMOUNT = 0           # 最小金额过滤，0表示不过滤
    # ===============================================
    
    if API_KEY == "your_api_key_here":
        print("错误: 请先配置你的API Key!")
        print("\n请编辑 okx_monitor_transfer.py 文件，在 main() 函数中填入你的API信息")
        return
    
    # 创建监控器
    monitor = OKXTransferMonitor(
        api_key=API_KEY,
        secret_key=SECRET_KEY,
        passphrase=PASSPHRASE,
        is_demo=IS_DEMO
    )
    
    # 开始监控转账
    monitor.monitor_transfers(
        interval=MONITOR_INTERVAL,
        min_amount=MIN_AMOUNT
    )


if __name__ == "__main__":
    main()


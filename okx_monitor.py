#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 账户交易资金变动监控脚本
监控账户交易记录,重点关注资金变动
"""

import hmac
import base64
import hashlib
import time
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional


class OKXMonitor:
    """OKX API 监控类"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, is_demo: bool = False):
        """
        初始化OKX监控器
        
        Args:
            api_key: API Key
            secret_key: Secret Key
            passphrase: API密码
            is_demo: 是否为模拟盘 (True=模拟盘, False=实盘)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        # 根据是否模拟盘选择不同的API地址
        if is_demo:
            self.base_url = "https://www.okx.com"  # 模拟盘
        else:
            self.base_url = "https://www.okx.com"  # 实盘
            
        self.last_bill_id = None  # 记录最后一条账单ID,避免重复
        
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """
        生成签名
        
        Args:
            timestamp: 时间戳
            method: 请求方法 (GET/POST)
            request_path: 请求路径
            body: 请求体
            
        Returns:
            签名字符串
        """
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        """
        获取请求头
        
        Args:
            method: 请求方法
            request_path: 请求路径
            body: 请求体
            
        Returns:
            请求头字典
        """
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
    
    def get_bills(self, inst_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        获取账单流水(近7天)
        
        Args:
            inst_type: 产品类型 (SPOT=币币, MARGIN=杠杆, SWAP=永续合约, FUTURES=交割合约, OPTION=期权)
            limit: 返回结果数量,最大100
            
        Returns:
            账单列表
        """
        request_path = '/api/v5/account/bills'
        params = {'limit': str(limit)}
        
        if inst_type:
            params['instType'] = inst_type
            
        # 构建查询字符串
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
                print(f"API错误: {data.get('msg', '未知错误')}")
                return []
        except Exception as e:
            print(f"请求失败: {str(e)}")
            return []
    
    def monitor_bills(self, interval: int = 10, inst_type: Optional[str] = None):
        """
        持续监控账单流水
        
        Args:
            interval: 监控间隔(秒)
            inst_type: 产品类型
        """
        print(f"开始监控OKX账户资金变动...")
        print(f"监控间隔: {interval}秒")
        print(f"产品类型: {inst_type if inst_type else '全部'}")
        print("-" * 80)
        
        while True:
            try:
                bills = self.get_bills(inst_type=inst_type, limit=10)
                
                if bills:
                    # 反转列表,从旧到新处理
                    bills.reverse()
                    
                    for bill in bills:
                        bill_id = bill.get('billId')
                        
                        # 跳过已处理的账单
                        if self.last_bill_id and bill_id <= self.last_bill_id:
                            continue
                        
                        # 更新最后处理的账单ID
                        self.last_bill_id = bill_id
                        
                        # 提取关键信息
                        self._process_bill(bill)
                
                # 等待下一次检查
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n监控已停止")
                break
            except Exception as e:
                print(f"监控出错: {str(e)}")
                time.sleep(interval)
    
    def _process_bill(self, bill: Dict):
        """
        处理单条账单记录
        
        Args:
            bill: 账单数据
        """
        # 当前监控时间戳
        monitor_timestamp = int(time.time() * 1000)
        monitor_time = datetime.fromtimestamp(monitor_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # 账单产生时间
        bill_timestamp = bill.get('ts', '')
        bill_time = datetime.fromtimestamp(int(bill_timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # 资金变动金额
        balance_change = bill.get('balChg', '0')
        
        # 币种
        currency = bill.get('ccy', '')
        
        # 账单类型
        bill_type = bill.get('type', '')
        
        # 子类型
        sub_type = bill.get('subType', '')
        
        # 产品ID
        inst_id = bill.get('instId', '')
        
        # 余额
        balance = bill.get('bal', '0')
        
        # 账单类型说明
        type_desc = self._get_type_description(bill_type, sub_type)
        
        # 输出监控信息
        print(f"\n{'='*80}")
        print(f"【资金变动监控】")
        print(f"监控时间戳: {monitor_timestamp}")
        print(f"监控时间: {monitor_time}")
        print(f"账单产生时间: {bill_time}")
        print(f"账单时间戳: {bill_timestamp}")
        print(f"变动金额: {balance_change} {currency}")
        print(f"当前余额: {balance} {currency}")
        print(f"交易产品: {inst_id if inst_id else 'N/A'}")
        print(f"账单类型: {type_desc}")
        print(f"账单ID: {bill.get('billId', '')}")
        print(f"{'='*80}")
        
        # 返回格式化的监控结果
        return {
            'monitor_timestamp': monitor_timestamp,
            'monitor_time': monitor_time,
            'bill_timestamp': bill_timestamp,
            'bill_time': bill_time,
            'amount': balance_change,
            'currency': currency,
            'balance': balance,
            'type': type_desc
        }
    
    def _get_type_description(self, bill_type: str, sub_type: str) -> str:
        """
        获取账单类型描述
        
        Args:
            bill_type: 账单类型
            sub_type: 子类型
            
        Returns:
            类型描述
        """
        type_map = {
            '1': '划转',
            '2': '交易',
            '3': '交割',
            '4': '自动换币',
            '5': '强平',
            '6': '保证金划转',
            '7': '扣息',
            '8': '资金费',
            '9': '自动减仓',
            '10': '穿仓补偿',
            '11': '系统换币',
            '12': '策略划转',
            '13': '对冲减仓',
            '14': '大宗交易',
            '15': '一键借币',
            '16': '手动借币',
            '17': '一键还币',
            '18': '手动还币',
            '19': '自动还币',
            '20': '借币利息',
            '21': '手动借币利息',
            '22': '买入',
            '23': '卖出',
            '24': '开多',
            '25': '开空',
            '26': '平多',
            '27': '平空',
        }
        
        desc = type_map.get(bill_type, f'未知类型({bill_type})')
        if sub_type:
            desc += f" - {sub_type}"
        
        return desc


def main():
    """主函数"""
    # ==================== 配置区 ====================
    # 请在这里填入你的OKX API信息
    API_KEY = "your_api_key_here"
    SECRET_KEY = "your_secret_key_here"
    PASSPHRASE = "your_passphrase_here"
    IS_DEMO = False  # True=模拟盘, False=实盘
    
    # 监控配置
    MONITOR_INTERVAL = 10  # 监控间隔(秒)
    INST_TYPE = None  # 产品类型: None=全部, SPOT=币币, MARGIN=杠杆, SWAP=永续, FUTURES=交割, OPTION=期权
    # ===============================================
    
    # 检查API配置
    if API_KEY == "your_api_key_here":
        print("错误: 请先配置你的API Key!")
        print("请编辑脚本,填入正确的 API_KEY, SECRET_KEY 和 PASSPHRASE")
        return
    
    # 创建监控器
    monitor = OKXMonitor(
        api_key=API_KEY,
        secret_key=SECRET_KEY,
        passphrase=PASSPHRASE,
        is_demo=IS_DEMO
    )
    
    # 开始监控
    monitor.monitor_bills(interval=MONITOR_INTERVAL, inst_type=INST_TYPE)


if __name__ == "__main__":
    main()


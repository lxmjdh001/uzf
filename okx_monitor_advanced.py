#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 账户交易资金变动监控脚本 - 高级版
支持数据保存、日志记录、JSON输出等功能
"""

import hmac
import base64
import hashlib
import time
import requests
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class OKXMonitor:
    """OKX API 监控类"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, 
                 is_demo: bool = False, save_to_file: bool = True):
        """
        初始化OKX监控器
        
        Args:
            api_key: API Key
            secret_key: Secret Key
            passphrase: API密码
            is_demo: 是否为模拟盘
            save_to_file: 是否保存到文件
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.save_to_file = save_to_file
        
        # API地址
        if is_demo:
            self.base_url = "https://www.okx.com"
        else:
            self.base_url = "https://www.okx.com"
            
        self.last_bill_id = None
        
        # 创建数据目录
        if self.save_to_file:
            os.makedirs('data', exist_ok=True)
            os.makedirs('logs', exist_ok=True)
        
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
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        return headers
    
    def get_bills(self, inst_type: Optional[str] = None, limit: int = 100, 
                  after: Optional[str] = None, before: Optional[str] = None) -> List[Dict]:
        """
        获取账单流水
        
        Args:
            inst_type: 产品类型
            limit: 返回结果数量
            after: 请求此ID之前的分页内容
            before: 请求此ID之后的分页内容
            
        Returns:
            账单列表
        """
        request_path = '/api/v5/account/bills'
        params = {'limit': str(limit)}
        
        if inst_type:
            params['instType'] = inst_type
        if after:
            params['after'] = after
        if before:
            params['before'] = before
            
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
                error_msg = f"API错误: {data.get('msg', '未知错误')} (code: {data.get('code')})"
                self._log(error_msg, level='ERROR')
                return []
        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            self._log(error_msg, level='ERROR')
            return []
    
    def monitor_bills(self, interval: int = 10, inst_type: Optional[str] = None, 
                     callback=None, filter_amount: Optional[float] = None):
        """
        持续监控账单流水
        
        Args:
            interval: 监控间隔(秒)
            inst_type: 产品类型
            callback: 回调函数,接收处理后的账单数据
            filter_amount: 金额过滤,只显示绝对值大于此值的变动
        """
        print(f"开始监控OKX账户资金变动...")
        print(f"监控间隔: {interval}秒")
        print(f"产品类型: {inst_type if inst_type else '全部'}")
        if filter_amount:
            print(f"金额过滤: 只显示变动金额绝对值 > {filter_amount}")
        print("-" * 80)
        
        self._log("监控启动", level='INFO')
        
        while True:
            try:
                bills = self.get_bills(inst_type=inst_type, limit=10)
                
                if bills:
                    bills.reverse()
                    
                    for bill in bills:
                        bill_id = bill.get('billId')
                        
                        if self.last_bill_id and bill_id <= self.last_bill_id:
                            continue
                        
                        self.last_bill_id = bill_id
                        
                        # 金额过滤
                        if filter_amount:
                            balance_change = float(bill.get('balChg', '0'))
                            if abs(balance_change) < filter_amount:
                                continue
                        
                        # 处理账单
                        result = self._process_bill(bill)
                        
                        # 保存到文件
                        if self.save_to_file:
                            self._save_bill(result)
                        
                        # 执行回调
                        if callback:
                            callback(result)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n监控已停止")
                self._log("监控停止", level='INFO')
                break
            except Exception as e:
                error_msg = f"监控出错: {str(e)}"
                print(error_msg)
                self._log(error_msg, level='ERROR')
                time.sleep(interval)
    
    def _process_bill(self, bill: Dict) -> Dict:
        """处理单条账单记录"""
        # 当前监控时间戳
        monitor_timestamp = int(time.time() * 1000)
        monitor_time = datetime.fromtimestamp(monitor_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # 账单产生时间
        bill_timestamp = bill.get('ts', '')
        bill_time = datetime.fromtimestamp(int(bill_timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        
        # 资金变动金额
        balance_change = bill.get('balChg', '0')
        currency = bill.get('ccy', '')
        bill_type = bill.get('type', '')
        sub_type = bill.get('subType', '')
        inst_id = bill.get('instId', '')
        balance = bill.get('bal', '0')
        
        # 账单类型说明
        type_desc = self._get_type_description(bill_type, sub_type)
        
        # 构建结果
        result = {
            'monitor_timestamp': monitor_timestamp,
            'monitor_time': monitor_time,
            'bill_timestamp': bill_timestamp,
            'bill_time': bill_time,
            'amount': balance_change,
            'currency': currency,
            'balance': balance,
            'inst_id': inst_id,
            'type': type_desc,
            'bill_type': bill_type,
            'sub_type': sub_type,
            'bill_id': bill.get('billId', ''),
            'raw_data': bill
        }
        
        # 输出到控制台
        self._print_bill(result)
        
        return result
    
    def _print_bill(self, result: Dict):
        """打印账单信息到控制台"""
        print(f"\n{'='*80}")
        print(f"【资金变动监控】")
        print(f"监控时间戳: {result['monitor_timestamp']}")
        print(f"监控时间: {result['monitor_time']}")
        print(f"账单产生时间: {result['bill_time']}")
        print(f"账单时间戳: {result['bill_timestamp']}")
        print(f"变动金额: {result['amount']} {result['currency']}")
        print(f"当前余额: {result['balance']} {result['currency']}")
        print(f"交易产品: {result['inst_id'] if result['inst_id'] else 'N/A'}")
        print(f"账单类型: {result['type']}")
        print(f"账单ID: {result['bill_id']}")
        print(f"{'='*80}")
    
    def _save_bill(self, result: Dict):
        """保存账单到文件"""
        try:
            # 按日期保存
            date_str = datetime.now().strftime('%Y-%m-%d')
            filename = f"data/bills_{date_str}.jsonl"
            
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        except Exception as e:
            self._log(f"保存文件失败: {str(e)}", level='ERROR')
    
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        
        # 输出到控制台
        if level == 'ERROR':
            print(log_message)
        
        # 保存到日志文件
        if self.save_to_file:
            try:
                date_str = datetime.now().strftime('%Y-%m-%d')
                log_file = f"logs/monitor_{date_str}.log"
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_message + '\n')
            except Exception as e:
                print(f"写入日志失败: {str(e)}")
    
    def _get_type_description(self, bill_type: str, sub_type: str) -> str:
        """获取账单类型描述"""
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
    
    def export_to_csv(self, date: Optional[str] = None):
        """
        导出数据为CSV格式
        
        Args:
            date: 日期(YYYY-MM-DD),默认为今天
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        input_file = f"data/bills_{date}.jsonl"
        output_file = f"data/bills_{date}.csv"
        
        if not os.path.exists(input_file):
            print(f"文件不存在: {input_file}")
            return
        
        try:
            import csv
            
            with open(input_file, 'r', encoding='utf-8') as f_in:
                lines = f_in.readlines()
            
            if not lines:
                print("没有数据可导出")
                return
            
            # 解析JSON
            data = [json.loads(line) for line in lines]
            
            # 写入CSV
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f_out:
                fieldnames = ['monitor_time', 'bill_time', 'amount', 'currency', 
                             'balance', 'inst_id', 'type', 'bill_id']
                writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                
                writer.writeheader()
                for item in data:
                    writer.writerow({k: item.get(k, '') for k in fieldnames})
            
            print(f"导出成功: {output_file}")
        except Exception as e:
            print(f"导出失败: {str(e)}")


def main():
    """主函数"""
    # ==================== 配置区 ====================
    API_KEY = "your_api_key_here"
    SECRET_KEY = "your_secret_key_here"
    PASSPHRASE = "your_passphrase_here"
    IS_DEMO = False
    
    # 监控配置
    MONITOR_INTERVAL = 10
    INST_TYPE = None
    SAVE_TO_FILE = True  # 是否保存到文件
    FILTER_AMOUNT = None  # 金额过滤,例如 0.01 表示只显示变动金额>0.01的记录
    # ===============================================
    
    if API_KEY == "your_api_key_here":
        print("错误: 请先配置你的API Key!")
        return
    
    # 创建监控器
    monitor = OKXMonitor(
        api_key=API_KEY,
        secret_key=SECRET_KEY,
        passphrase=PASSPHRASE,
        is_demo=IS_DEMO,
        save_to_file=SAVE_TO_FILE
    )
    
    # 自定义回调函数(可选)
    def custom_callback(bill_data):
        """自定义处理逻辑"""
        # 这里可以添加自定义逻辑,例如:
        # - 发送邮件通知
        # - 发送Webhook
        # - 触发交易策略
        # - 写入数据库
        pass
    
    # 开始监控
    monitor.monitor_bills(
        interval=MONITOR_INTERVAL,
        inst_type=INST_TYPE,
        callback=custom_callback,
        filter_amount=FILTER_AMOUNT
    )


if __name__ == "__main__":
    main()


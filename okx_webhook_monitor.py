#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 转账监控 - Webhook版本
检测到转账后推送到B服务器，并保存到MySQL数据库
"""

import hmac
import base64
import hashlib
import time
import requests
import json
import pymysql
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional
from config_manager import ConfigManager


class OKXWebhookMonitor:
    """OKX 转账监控 - Webhook推送版"""
    
    def __init__(self, 
                 api_key: str, 
                 secret_key: str, 
                 passphrase: str,
                 webhook_url: str,
                 webhook_secret: str,
                 db_config: Dict,
                 is_demo: bool = False):
        """
        初始化OKX Webhook监控器
        
        Args:
            api_key: OKX API Key
            secret_key: OKX Secret Key
            passphrase: OKX API密码
            webhook_url: B服务器的Webhook接口地址
            webhook_secret: Webhook签名密钥
            db_config: MySQL数据库配置
            is_demo: 是否为模拟盘
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret
        self.db_config = db_config
        
        # API地址
        self.base_url = "https://www.okx.com"
        self.last_bill_id = None
        
        # 初始化数据库
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 创建转账记录表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS okx_transfers (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                bill_id VARCHAR(50) UNIQUE NOT NULL COMMENT '账单ID',
                amount DECIMAL(20, 8) NOT NULL COMMENT '转账金额',
                currency VARCHAR(20) NOT NULL COMMENT '币种',
                balance DECIMAL(20, 8) NOT NULL COMMENT '当前余额',
                transfer_type VARCHAR(50) COMMENT '转账类型',
                sub_type VARCHAR(10) COMMENT '子类型代码',
                bill_timestamp BIGINT NOT NULL COMMENT '账单时间戳',
                bill_time DATETIME NOT NULL COMMENT '账单时间',
                monitor_timestamp BIGINT NOT NULL COMMENT '监控时间戳',
                monitor_time DATETIME NOT NULL COMMENT '监控时间',
                webhook_status TINYINT DEFAULT 0 COMMENT 'Webhook推送状态 0=未推送 1=成功 2=失败',
                webhook_response TEXT COMMENT 'Webhook响应',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_bill_time (bill_time),
                INDEX idx_currency (currency),
                INDEX idx_webhook_status (webhook_status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OKX转账记录表';
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✓ 数据库初始化成功")
            
        except Exception as e:
            print(f"✗ 数据库初始化失败: {str(e)}")
            raise
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成OKX API签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        """获取OKX API请求头"""
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
    
    def _generate_webhook_signature(self, data: str) -> str:
        """生成Webhook签名"""
        mac = hmac.new(
            bytes(self.webhook_secret, encoding='utf8'),
            bytes(data, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return mac.hexdigest()
    
    def get_bills(self, limit: int = 100) -> List[Dict]:
        """获取账单流水"""
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
    
    def _save_to_database(self, transfer_data: Dict) -> bool:
        """保存转账记录到数据库"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            insert_sql = """
            INSERT INTO okx_transfers 
            (bill_id, amount, currency, balance, transfer_type, sub_type, 
             bill_timestamp, bill_time, monitor_timestamp, monitor_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE id=id
            """
            
            cursor.execute(insert_sql, (
                transfer_data['bill_id'],
                transfer_data['amount'],
                transfer_data['currency'],
                transfer_data['balance'],
                transfer_data['transfer_type'],
                transfer_data['sub_type'],
                transfer_data['bill_timestamp'],
                transfer_data['bill_time'],
                transfer_data['monitor_timestamp'],
                transfer_data['monitor_time']
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"✗ 数据库保存失败: {str(e)}")
            return False
    
    def _update_webhook_status(self, bill_id: str, status: int, response: str = ''):
        """更新Webhook推送状态"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            update_sql = """
            UPDATE okx_transfers 
            SET webhook_status = %s, webhook_response = %s
            WHERE bill_id = %s
            """
            
            cursor.execute(update_sql, (status, response, bill_id))
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"✗ 更新Webhook状态失败: {str(e)}")
    
    def _send_webhook(self, transfer_data: Dict) -> bool:
        """发送Webhook到B服务器"""
        try:
            # 准备推送数据
            payload = {
                'bill_id': transfer_data['bill_id'],
                'amount': str(transfer_data['amount']),
                'currency': transfer_data['currency'],
                'balance': str(transfer_data['balance']),
                'transfer_type': transfer_data['transfer_type'],
                'sub_type': transfer_data['sub_type'],
                'bill_timestamp': transfer_data['bill_timestamp'],
                'bill_time': transfer_data['bill_time'],
                'monitor_timestamp': transfer_data['monitor_timestamp'],
                'monitor_time': transfer_data['monitor_time']
            }
            
            # 生成签名
            payload_str = json.dumps(payload, sort_keys=True)
            signature = self._generate_webhook_signature(payload_str)
            
            # 发送请求
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'X-Webhook-Timestamp': str(transfer_data['monitor_timestamp'])
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            # 更新推送状态
            if response.status_code == 200:
                self._update_webhook_status(
                    transfer_data['bill_id'],
                    1,  # 成功
                    f"Status: {response.status_code}, Response: {response.text[:500]}"
                )
                print(f"✓ Webhook推送成功: {self.webhook_url}")
                return True
            else:
                self._update_webhook_status(
                    transfer_data['bill_id'],
                    2,  # 失败
                    f"Status: {response.status_code}, Response: {response.text[:500]}"
                )
                print(f"✗ Webhook推送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            self._update_webhook_status(transfer_data['bill_id'], 2, error_msg)
            print(f"✗ Webhook推送异常: {str(e)}")
            return False
    
    def monitor_transfers(self, interval: int = 10, min_amount: float = 0):
        """持续监控转账"""
        print("="*80)
        print("OKX 转账监控启动 (Webhook + MySQL)")
        print("="*80)
        print(f"监控间隔: {interval}秒")
        print(f"Webhook地址: {self.webhook_url}")
        print(f"数据库: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
        if min_amount > 0:
            print(f"金额过滤: >= {min_amount}")
        print("-" * 80)
        
        while True:
            try:
                bills = self.get_bills(limit=20)
                
                if bills:
                    bills.reverse()
                    
                    for bill in bills:
                        bill_id = bill.get('billId')
                        
                        if self.last_bill_id and bill_id <= self.last_bill_id:
                            continue
                        
                        self.last_bill_id = bill_id
                        
                        # 只处理划转类型且金额为正
                        bill_type = bill.get('type', '')
                        if bill_type != '1':
                            continue
                        
                        balance_change = float(bill.get('balChg', '0'))
                        if balance_change <= 0:
                            continue
                        
                        if balance_change < min_amount:
                            continue
                        
                        # 处理转账
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
        amount = float(bill.get('balChg', '0'))
        currency = bill.get('ccy', '')
        balance = float(bill.get('bal', '0'))

        # 子类型说明
        sub_type = bill.get('subType', '')
        sub_type_desc = self._get_subtype_description(sub_type)

        # 构建转账数据
        transfer_data = {
            'bill_id': bill.get('billId', ''),
            'amount': amount,
            'currency': currency,
            'balance': balance,
            'transfer_type': sub_type_desc,
            'sub_type': sub_type,
            'bill_timestamp': int(bill_timestamp),
            'bill_time': bill_time,
            'monitor_timestamp': monitor_timestamp,
            'monitor_time': monitor_time
        }

        # 输出转账信息
        print(f"\n{'='*80}")
        print(f"🎉 检测到转账流入!")
        print(f"{'='*80}")
        print(f"监控时间: {monitor_time} ({monitor_timestamp})")
        print(f"转账时间: {bill_time} ({bill_timestamp})")
        print(f"转账金额: +{amount} {currency}")
        print(f"当前余额: {balance} {currency}")
        print(f"转账类型: {sub_type_desc}")
        print(f"账单ID: {transfer_data['bill_id']}")
        print(f"{'-'*80}")

        # 保存到数据库
        if self._save_to_database(transfer_data):
            print("✓ 已保存到数据库")
        else:
            print("✗ 数据库保存失败")

        # 发送Webhook
        if self._send_webhook(transfer_data):
            print("✓ Webhook推送成功")
        else:
            print("✗ Webhook推送失败")

        print(f"{'='*80}")

    def _get_subtype_description(self, sub_type: str) -> str:
        """获取子类型描述"""
        subtype_map = {
            '1': '买入',
            '2': '卖出',
            '11': '转入',
            '12': '转出',
            '100': '资金账户转入',
            '101': '资金账户转出',
            '102': '交易账户转入',
            '103': '交易账户转出',
        }
        return subtype_map.get(sub_type, f'划转 (子类型: {sub_type})')


def main():
    """主函数"""
    print("="*80)
    print("OKX 转账监控系统启动")
    print("="*80)

    # ==================== 从数据库加载配置 ====================
    # 首先需要数据库基本配置（可以从环境变量或配置文件读取）
    import os

    # 优先从环境变量读取数据库配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'okx_monitor'),
        'charset': 'utf8mb4'
    }

    # 如果环境变量中没有密码，尝试从命令行参数读取
    if not db_config['password'] and len(sys.argv) > 1:
        db_config['password'] = sys.argv[1]

    # 如果还是没有密码，提示用户
    if not db_config['password']:
        print("\n错误: 未配置数据库密码!")
        print("\n请使用以下方式之一配置:")
        print("1. 设置环境变量: export DB_PASSWORD='your_password'")
        print("2. 命令行参数: python3 okx_webhook_monitor.py 'your_password'")
        print("3. 运行配置向导: python3 config_manager.py")
        print("="*80)
        return

    # 测试数据库连接
    print("\n正在连接数据库...")
    try:
        conn = pymysql.connect(**db_config)
        conn.close()
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        print("\n请检查数据库配置或运行配置向导: python3 config_manager.py")
        return

    # 创建配置管理器
    config_manager = ConfigManager(db_config)

    # 从数据库加载OKX配置
    print("正在加载OKX API配置...")
    okx_config = config_manager.get_all_okx_config()
    if not okx_config:
        print("✗ 未找到OKX API配置!")
        print("\n请先运行配置向导: python3 config_manager.py")
        return
    print("✓ OKX API配置加载成功")

    # 从数据库加载Webhook配置
    print("正在加载Webhook配置...")
    webhook_config = config_manager.get_webhook_config()
    if not webhook_config:
        print("✗ 未找到Webhook配置!")
        print("\n请先运行配置向导: python3 config_manager.py")
        return
    print("✓ Webhook配置加载成功")

    # 监控配置
    MONITOR_INTERVAL = int(config_manager.get_config('monitor_interval', '10'))
    MIN_AMOUNT = float(config_manager.get_config('min_amount', '0'))

    print("\n" + "="*80)
    print("配置加载完成，准备启动监控...")
    print("="*80)

    # 创建监控器
    monitor = OKXWebhookMonitor(
        api_key=okx_config['api_key'],
        secret_key=okx_config['secret_key'],
        passphrase=okx_config['passphrase'],
        webhook_url=webhook_config['url'],
        webhook_secret=webhook_config['secret'],
        db_config=db_config,
        is_demo=okx_config['is_demo']
    )

    # 开始监控
    monitor.monitor_transfers(
        interval=MONITOR_INTERVAL,
        min_amount=MIN_AMOUNT
    )


if __name__ == "__main__":
    main()


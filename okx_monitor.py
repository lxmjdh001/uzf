#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 支付监控系统 - JSON版本
功能：
1. 定期监控OKX转账记录
2. 保存到JSON文件（只保留近2小时记录）
3. 自动过滤过期记录
"""

import hmac
import base64
import hashlib
import time
import requests
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OKXMonitor:
    """OKX转账监控器"""

    def __init__(self, api_key: str, secret_key: str, passphrase: str,
                 json_file: str = "okx_transfers.json", is_demo: bool = False):
        """
        初始化OKX监控器

        Args:
            api_key: OKX API Key
            secret_key: OKX Secret Key
            passphrase: OKX API密码
            json_file: JSON存储文件路径
            is_demo: 是否为模拟盘
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.json_file = json_file

        # API地址
        self.base_url = "https://www.okx.com" if not is_demo else "https://www.okx.com"

        # 2小时的时间窗口（秒）
        self.time_window = 2 * 60 * 60

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """生成OKX API签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()

    def _get_okx_bills(self) -> List[Dict]:
        """获取OKX账单流水"""
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            request_path = '/api/v5/account/bills?instType=&type=1'
            method = 'GET'

            signature = self._generate_signature(timestamp, method, request_path)

            headers = {
                'OK-ACCESS-KEY': self.api_key,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': self.passphrase,
                'Content-Type': 'application/json'
            }

            response = requests.get(
                self.base_url + request_path,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    return data.get('data', [])
                else:
                    print(f"✗ OKX API错误: {data.get('msg', 'Unknown error')}")
            else:
                print(f"✗ HTTP错误: {response.status_code}")

            return []

        except Exception as e:
            print(f"✗ 获取OKX账单失败: {str(e)}")
            return []

    def _load_json_data(self) -> List[Dict]:
        """从JSON文件加载数据"""
        try:
            if os.path.exists(self.json_file):
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('transfers', [])
            return []
        except Exception as e:
            print(f"✗ 加载JSON文件失败: {str(e)}")
            return []

    def _save_json_data(self, transfers: List[Dict]):
        """保存数据到JSON文件"""
        try:
            data = {
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_update_timestamp': int(time.time()),
                'transfers': transfers,
                'count': len(transfers)
            }

            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✓ 数据已保存: {len(transfers)} 条记录")

        except Exception as e:
            print(f"✗ 保存JSON文件失败: {str(e)}")

    def _filter_old_records(self, transfers: List[Dict]) -> List[Dict]:
        """过滤掉超过2小时的记录"""
        current_time = int(time.time())
        cutoff_time = current_time - self.time_window

        filtered = [
            t for t in transfers
            if t.get('bill_timestamp', 0) / 1000 >= cutoff_time  # bill_timestamp是毫秒，需要转换为秒
        ]

        removed_count = len(transfers) - len(filtered)
        if removed_count > 0:
            print(f"🗑️  已过滤 {removed_count} 条过期记录（超过2小时）")

        return filtered

    def _process_bills(self, bills: List[Dict]) -> List[Dict]:
        """处理账单，转换为标准格式"""
        transfers = []

        for bill in bills:
            # 只处理转入（type=1, balChg>0）
            if bill.get('type') == '1' and float(bill.get('balChg', 0)) > 0:
                # OKX时间戳是UTC时间（毫秒）
                bill_timestamp_ms = int(bill['ts'])
                bill_time = datetime.fromtimestamp(bill_timestamp_ms / 1000, tz=timezone.utc)

                # 监控时间戳（当前时间，秒）
                monitor_timestamp = int(time.time())
                monitor_time = datetime.now()

                transfer = {
                    'bill_id': bill['billId'],
                    'amount': abs(float(bill['balChg'])),
                    'currency': bill['ccy'],
                    'balance': float(bill['bal']),
                    'transfer_type': '转入',
                    'bill_timestamp': bill_timestamp_ms,
                    'bill_time': bill_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'bill_time_utc': bill_time.isoformat(),
                    'monitor_timestamp': monitor_timestamp,
                    'monitor_time': monitor_time.strftime('%Y-%m-%d %H:%M:%S'),
                }

                transfers.append(transfer)

        return transfers

    def update_records(self):
        """更新转账记录"""
        print("-" * 80)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新...")

        # 1. 获取OKX账单
        bills = self._get_okx_bills()
        if not bills:
            print("⚠️  未获取到新账单")
            return

        print(f"✓ 获取到 {len(bills)} 条账单记录")

        # 2. 加载现有数据
        existing_transfers = self._load_json_data()
        existing_bill_ids = {t['bill_id'] for t in existing_transfers}

        # 3. 处理新账单
        new_transfers = self._process_bills(bills)

        # 4. 合并数据（去重）
        merged_transfers = existing_transfers.copy()
        new_count = 0

        for transfer in new_transfers:
            if transfer['bill_id'] not in existing_bill_ids:
                merged_transfers.append(transfer)
                existing_bill_ids.add(transfer['bill_id'])
                new_count += 1

                print(f"✓ 新转账: {transfer['amount']} {transfer['currency']} - {transfer['bill_time']}")

        if new_count == 0:
            print("ℹ️  没有新的转账记录")
        else:
            print(f"✓ 新增 {new_count} 条转账记录")

        # 5. 过滤过期记录
        merged_transfers = self._filter_old_records(merged_transfers)

        # 6. 按时间排序（最新的在前）
        merged_transfers.sort(key=lambda x: x['monitor_timestamp'], reverse=True)

        # 7. 保存到JSON
        self._save_json_data(merged_transfers)

        print(f"✓ 当前共 {len(merged_transfers)} 条有效记录（近2小时）")

    def monitor_loop(self, interval: int = 10):
        """监控循环"""
        print("=" * 80)
        print("OKX 转账监控系统 - JSON版本")
        print("=" * 80)
        print(f"监控间隔: {interval}秒")
        print(f"数据文件: {self.json_file}")
        print(f"时间窗口: 2小时")
        print("-" * 80)

        while True:
            try:
                self.update_records()
            except Exception as e:
                print(f"✗ 监控循环异常: {str(e)}")

            print(f"💤 等待 {interval} 秒...")
            time.sleep(interval)


def main():
    """主函数"""
    print("=" * 80)
    print("OKX 转账监控系统启动")
    print("=" * 80)

    # 加载配置
    config_file = 'config.json'

    if not os.path.exists(config_file):
        print(f"✗ 配置文件不存在: {config_file}")
        print("\n请先创建配置文件 config.json，参考格式：")
        print(json.dumps({
            "okx": {
                "api_key": "your_api_key",
                "secret_key": "your_secret_key",
                "passphrase": "your_passphrase",
                "is_demo": False
            },
            "monitor": {
                "interval": 10,
                "json_file": "okx_transfers.json"
            }
        }, indent=2, ensure_ascii=False))
        return

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"✗ 加载配置文件失败: {str(e)}")
        return

    # 获取配置
    okx_config = config.get('okx', {})
    monitor_config = config.get('monitor', {})

    if not okx_config.get('api_key') or not okx_config.get('secret_key'):
        print("✗ 配置文件中缺少OKX API配置")
        return

    print("✓ 配置文件加载成功")

    # 创建监控实例
    monitor = OKXMonitor(
        api_key=okx_config['api_key'],
        secret_key=okx_config['secret_key'],
        passphrase=okx_config['passphrase'],
        json_file=monitor_config.get('json_file', 'okx_transfers.json'),
        is_demo=okx_config.get('is_demo', False)
    )

    # 启动监控
    interval = monitor_config.get('interval', 10)
    monitor.monitor_loop(interval)


if __name__ == '__main__':
    main()

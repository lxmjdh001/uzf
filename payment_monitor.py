#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 支付监控系统
功能：
1. 提供HTTP API接收B服务器订单
2. 监控OKX转账并自动匹配订单
3. 订单匹配成功/超时后回调B服务器
"""

import hmac
import base64
import hashlib
import time
import requests
import json
import pymysql
import sys
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from flask import Flask, request, jsonify
from config_manager import get_db_config, get_okx_config, get_webhook_config

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PaymentMonitor:
    """支付监控系统"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str,
                 webhook_secret: str, db_config: Dict, is_demo: bool = False):
        """
        初始化支付监控系统
        
        Args:
            api_key: OKX API Key
            secret_key: OKX Secret Key
            passphrase: OKX API密码
            webhook_secret: Webhook签名密钥
            db_config: MySQL数据库配置
            is_demo: 是否为模拟盘
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
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
            
            # 创建订单表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_orders (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                order_id VARCHAR(100) UNIQUE NOT NULL,
                amount DECIMAL(20, 8) NOT NULL,
                currency VARCHAR(20) DEFAULT 'USDT',
                create_time DATETIME NOT NULL,
                expire_time DATETIME NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                matched_bill_id VARCHAR(100),
                matched_time DATETIME,
                callback_url VARCHAR(500),
                callback_status TINYINT DEFAULT 0,
                callback_response TEXT,
                callback_time DATETIME,
                remark VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_order_id (order_id),
                INDEX idx_status (status),
                INDEX idx_expire_time (expire_time),
                INDEX idx_amount (amount)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 创建转账记录表
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS okx_transfers (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                bill_id VARCHAR(100) UNIQUE NOT NULL,
                amount DECIMAL(20, 8) NOT NULL,
                currency VARCHAR(20) NOT NULL,
                balance DECIMAL(20, 8) NOT NULL,
                transfer_type VARCHAR(50) NOT NULL,
                bill_timestamp BIGINT NOT NULL,
                bill_time DATETIME NOT NULL,
                matched_order_id VARCHAR(100),
                matched_time DATETIME,
                is_matched TINYINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_bill_id (bill_id),
                INDEX idx_bill_time (bill_time),
                INDEX idx_amount (amount),
                INDEX idx_is_matched (is_matched)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
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
            
            return []
            
        except Exception as e:
            print(f"✗ 获取OKX账单失败: {str(e)}")
            return []
    
    def _save_transfer(self, bill: Dict) -> bool:
        """保存转账记录到数据库"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            # OKX时间戳是UTC时间，转换为本地时间用于数据库存储
            bill_time = datetime.fromtimestamp(int(bill['ts']) / 1000, tz=timezone.utc).replace(tzinfo=None)
            # 监控时间戳（当前时间）
            monitor_timestamp = datetime.now()
            
            insert_sql = """
            INSERT INTO okx_transfers 
            (bill_id, amount, currency, balance, transfer_type, bill_timestamp, bill_time, monitor_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE bill_id=bill_id
            """
            
            cursor.execute(insert_sql, (
                bill['billId'],
                abs(float(bill['balChg'])),
                bill['ccy'],
                float(bill['bal']),
                '转入' if float(bill['balChg']) > 0 else '转出',
                int(bill['ts']),
                bill_time,
                monitor_timestamp
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"✗ 保存转账记录失败: {str(e)}")
            return False
    
    def _match_order(self, bill: Dict) -> Optional[Dict]:
        """匹配订单（使用事务锁定防止并发问题）"""
        try:
            # 只处理转入
            if float(bill['balChg']) <= 0:
                return None
            
            amount = abs(float(bill['balChg']))
            currency = bill['ccy']
            # 使用UTC时间确保时区正确
            bill_time = datetime.fromtimestamp(int(bill['ts']) / 1000, tz=timezone.utc)
            # 转换为本地时间用于数据库比较（假设数据库存储的是本地时间）
            bill_time_local = bill_time.replace(tzinfo=None)
            
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            try:
                # 开始事务
                conn.begin()
                
                # 查找匹配的订单：金额完全一致 + 在时间范围内 + 状态为pending
                # 使用 FOR UPDATE 锁定行，防止并发匹配
                select_sql = """
                SELECT * FROM payment_orders 
                WHERE status = 'pending'
                AND amount = %s
                AND currency = %s
                AND create_time <= %s
                AND expire_time >= %s
                ORDER BY create_time ASC
                LIMIT 1
                FOR UPDATE
                """
                
                cursor.execute(select_sql, (amount, currency, bill_time_local, bill_time_local))
                order = cursor.fetchone()
                
                if order:
                    # 再次检查状态（防止在锁定期间状态被改变）
                    if order['status'] != 'pending':
                        conn.rollback()
                        cursor.close()
                        conn.close()
                        return None
                    
                    # 更新订单状态
                    update_order_sql = """
                    UPDATE payment_orders 
                    SET status = 'matched', 
                        matched_bill_id = %s,
                        matched_time = %s
                    WHERE order_id = %s
                    AND status = 'pending'
                    """
                    rows_affected = cursor.execute(update_order_sql, (bill['billId'], bill_time_local, order['order_id']))
                    
                    if rows_affected == 0:
                        # 订单已被其他进程匹配
                        conn.rollback()
                        cursor.close()
                        conn.close()
                        return None
                    
                    # 更新转账记录
                    update_transfer_sql = """
                    UPDATE okx_transfers 
                    SET matched_order_id = %s,
                        matched_time = %s,
                        is_matched = 1
                    WHERE bill_id = %s
                    AND is_matched = 0
                    """
                    cursor.execute(update_transfer_sql, (order['order_id'], bill_time_local, bill['billId']))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    return order
                else:
                    conn.rollback()
                    cursor.close()
                    conn.close()
                    return None
                    
            except Exception as e:
                conn.rollback()
                cursor.close()
                conn.close()
                raise
            
        except Exception as e:
            print(f"✗ 订单匹配失败: {str(e)}")
            return None

    def _send_callback(self, order: Dict, success: bool) -> bool:
        """发送回调到B服务器（防止重复回调）"""
        try:
            if not order.get('callback_url'):
                print(f"订单 {order['order_id']} 没有配置回调地址")
                return False

            # 检查是否已经回调过（防止重复回调）
            if order.get('callback_status', 0) != 0:
                print(f"订单 {order['order_id']} 已回调过，跳过")
                return True

            # 准备回调数据
            payload = {
                'order_id': order['order_id'],
                'amount': str(order['amount']),
                'currency': order['currency'],
                'create_time': order['create_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'success' if success else 'failed',
                'matched_bill_id': order.get('matched_bill_id'),
                'matched_time': order['matched_time'].strftime('%Y-%m-%d %H:%M:%S') if order.get('matched_time') else None,
                'timestamp': int(time.time())
            }

            # 生成签名
            payload_str = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                bytes(self.webhook_secret, encoding='utf8'),
                bytes(payload_str, encoding='utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()

            # 发送回调
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'X-Webhook-Timestamp': str(payload['timestamp'])
            }

            response = requests.post(
                order['callback_url'],
                json=payload,
                headers=headers,
                timeout=10,
                verify=False
            )

            # 更新回调状态（使用原子更新防止重复回调）
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            callback_status = 1 if response.status_code == 200 else 2
            update_sql = """
            UPDATE payment_orders
            SET callback_status = %s,
                callback_response = %s,
                callback_time = %s
            WHERE order_id = %s
            AND callback_status = 0
            """

            rows_affected = cursor.execute(update_sql, (
                callback_status,
                response.text[:1000],
                datetime.now(),
                order['order_id']
            ))

            conn.commit()
            cursor.close()
            conn.close()

            if rows_affected == 0:
                print(f"⚠️ 订单 {order['order_id']} 回调状态已被其他进程更新，跳过")
                return True

            if response.status_code == 200:
                print(f"✓ 回调成功: {order['order_id']}")
                return True
            else:
                print(f"✗ 回调失败: {order['order_id']}, 状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ 回调异常: {order['order_id']}, {str(e)}")
            # 记录异常到数据库
            try:
                conn = pymysql.connect(**self.db_config)
                cursor = conn.cursor()
                update_sql = """
                UPDATE payment_orders
                SET callback_status = 2,
                    callback_response = %s,
                    callback_time = %s
                WHERE order_id = %s
                AND callback_status = 0
                """
                cursor.execute(update_sql, (str(e)[:1000], datetime.now(), order['order_id']))
                conn.commit()
                cursor.close()
                conn.close()
            except:
                pass
            return False

    def _check_expired_orders(self):
        """检查并处理过期订单"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            # 查找已过期但状态仍为pending且未回调的订单
            select_sql = """
            SELECT * FROM payment_orders
            WHERE status = 'pending'
            AND expire_time < %s
            AND callback_status = 0
            """

            cursor.execute(select_sql, (datetime.now(),))
            expired_orders = cursor.fetchall()

            for order in expired_orders:
                # 更新订单状态为expired（使用原子更新防止并发问题）
                update_sql = """
                UPDATE payment_orders
                SET status = 'expired'
                WHERE order_id = %s
                AND status = 'pending'
                """
                rows_affected = cursor.execute(update_sql, (order['order_id'],))
                
                if rows_affected > 0:
                    conn.commit()
                    print(f"⏰ 订单超时: {order['order_id']}, 金额: {order['amount']} {order['currency']}")
                    
                    # 发送失败回调
                    self._send_callback(order, success=False)
                else:
                    # 订单已被其他进程处理
                    conn.rollback()

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"✗ 检查过期订单失败: {str(e)}")

    def monitor_loop(self, interval: int = 10):
        """监控循环"""
        print("="*80)
        print("OKX 支付监控系统 - 监控启动")
        print("="*80)
        print(f"监控间隔: {interval}秒")
        print(f"数据库: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
        print("-"*80)

        while True:
            try:
                # 1. 获取OKX账单
                bills = self._get_okx_bills()

                # 2. 处理新账单
                new_bills_processed = False
                for bill in bills:
                    # 只处理转入（type=1, balChg>0）
                    if bill.get('type') == '1' and float(bill.get('balChg', 0)) > 0:
                        # 检查是否已处理（如果遇到已处理的账单，说明后续都是已处理的，可以跳出）
                        if self.last_bill_id and bill['billId'] == self.last_bill_id:
                            break

                        # 保存转账记录（如果已存在会跳过）
                        self._save_transfer(bill)

                        # 尝试匹配订单
                        matched_order = self._match_order(bill)

                        if matched_order:
                            # OKX时间戳是UTC时间，转换为本地时间用于数据库存储
                            bill_time = datetime.fromtimestamp(int(bill['ts']) / 1000, tz=timezone.utc).replace(tzinfo=None)
                            print("="*80)
                            print("🎉 订单匹配成功!")
                            print("="*80)
                            print(f"订单号: {matched_order['order_id']}")
                            print(f"金额: {bill['balChg']} {bill['ccy']}")
                            print(f"转账时间: {bill_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"账单ID: {bill['billId']}")
                            print("-"*80)

                            # 发送成功回调
                            self._send_callback(matched_order, success=True)
                            print("="*80)
                        
                        # 记录已处理的最新账单ID
                        if not new_bills_processed:
                            self.last_bill_id = bill['billId']
                            new_bills_processed = True

                # 3. 检查过期订单
                self._check_expired_orders()

            except Exception as e:
                print(f"✗ 监控循环异常: {str(e)}")

            time.sleep(interval)


# Flask API服务
app = Flask(__name__)
monitor = None  # 全局监控实例


@app.route('/api/order/create', methods=['POST'])
def create_order():
    """
    创建支付订单

    请求格式:
    {
        "order_id": "ORDER123456",
        "amount": "88.02",
        "currency": "USDT",
        "create_time": "2025-11-15 12:30:00",
        "callback_url": "https://your-b-server.com/api/callback"
    }
    """
    try:
        data = request.json

        # 验证必需字段
        required_fields = ['order_id', 'amount', 'create_time', 'callback_url']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'缺少必需字段: {field}'}), 400

        # 解析时间
        create_time = datetime.strptime(data['create_time'], '%Y-%m-%d %H:%M:%S')
        expire_time = create_time + timedelta(minutes=60)

        # 保存订单到数据库
        conn = pymysql.connect(**monitor.db_config)
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO payment_orders
        (order_id, amount, currency, create_time, expire_time, callback_url, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
        """

        cursor.execute(insert_sql, (
            data['order_id'],
            float(data['amount']),
            data.get('currency', 'USDT'),
            create_time,
            expire_time,
            data['callback_url']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✓ 订单创建成功: {data['order_id']}, 金额: {data['amount']} {data.get('currency', 'USDT')}")

        return jsonify({
            'success': True,
            'message': '订单创建成功',
            'data': {
                'order_id': data['order_id'],
                'amount': data['amount'],
                'currency': data.get('currency', 'USDT'),
                'create_time': create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'expire_time': expire_time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'pending'
            }
        }), 200

    except pymysql.IntegrityError as e:
        return jsonify({'success': False, 'message': f'订单号已存在: {data["order_id"]}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建订单失败: {str(e)}'}), 500


@app.route('/api/order/status/<order_id>', methods=['GET'])
def get_order_status(order_id):
    """查询订单状态"""
    try:
        conn = pymysql.connect(**monitor.db_config)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        select_sql = "SELECT * FROM payment_orders WHERE order_id = %s"
        cursor.execute(select_sql, (order_id,))
        order = cursor.fetchone()

        cursor.close()
        conn.close()

        if not order:
            return jsonify({'success': False, 'message': '订单不存在'}), 404

        return jsonify({
            'success': True,
            'data': {
                'order_id': order['order_id'],
                'amount': str(order['amount']),
                'currency': order['currency'],
                'create_time': order['create_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'expire_time': order['expire_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'status': order['status'],
                'matched_bill_id': order['matched_bill_id'],
                'matched_time': order['matched_time'].strftime('%Y-%m-%d %H:%M:%S') if order['matched_time'] else None
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'payment-monitor'}), 200


def main():
    """主函数"""
    global monitor

    print("="*80)
    print("OKX 支付监控系统启动")
    print("="*80)

    # 从配置文件加载数据库配置
    print("\n正在加载配置文件...")
    db_config = get_db_config()
    if not db_config:
        print("✗ 未找到配置文件或数据库配置!")
        print("\n请运行配置向导创建配置文件:")
        print("  python3 config_manager.py")
        print("\n或者复制示例配置文件:")
        print("  cp config.json.example config.json")
        print("  然后编辑 config.json 填入你的配置")
        print("="*80)
        return
    print(f"✓ 从配置文件加载数据库配置: {db_config['user']}@{db_config['host']}/{db_config['database']}")

    # 测试数据库连接
    print("\n正在连接数据库...")
    try:
        conn = pymysql.connect(**db_config)
        conn.close()
        print("✓ 数据库连接成功!")
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        print("\n请检查数据库配置或运行配置向导: python3 config_manager.py")
        return

    # 加载OKX配置
    print("\n正在加载OKX API配置...")
    okx_config = get_okx_config()
    if not okx_config:
        print("✗ 未找到OKX API配置")
        print("\n请运行配置向导: python3 config_manager.py")
        return
    print("✓ OKX API配置加载成功")

    # 加载Webhook配置
    print("正在加载Webhook配置...")
    webhook_config = get_webhook_config()
    if not webhook_config:
        print("✗ 未找到Webhook配置")
        print("\n请运行配置向导: python3 config_manager.py")
        return
    print("✓ Webhook配置加载成功")

    # 创建监控实例
    print("\n正在初始化监控系统...")
    monitor = PaymentMonitor(
        api_key=okx_config['api_key'],
        secret_key=okx_config['secret_key'],
        passphrase=okx_config['passphrase'],
        webhook_secret=webhook_config['secret'],
        db_config=db_config,
        is_demo=okx_config['is_demo']
    )

    print("\n="*80)
    print("系统启动成功!")
    print("="*80)
    print(f"API服务地址: http://0.0.0.0:5000")
    print(f"创建订单: POST http://0.0.0.0:5000/api/order/create")
    print(f"查询订单: GET http://0.0.0.0:5000/api/order/status/<order_id>")
    print(f"健康检查: GET http://0.0.0.0:5000/health")
    print("="*80)

    # 启动监控线程
    monitor_thread = threading.Thread(target=monitor.monitor_loop, args=(10,), daemon=True)
    monitor_thread.start()

    # 启动Flask API服务
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()


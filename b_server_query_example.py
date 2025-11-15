#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B服务器示例代码 - 查询版本
演示如何：
1. 生成签名
2. 查询A服务器的OKX转账记录
3. 验证用户支付
"""

import requests
import hmac
import hashlib
import time
from typing import Optional, Dict, List


class OKXPaymentChecker:
    """OKX支付检查器 - 用于B服务器查询A服务器的转账记录"""

    def __init__(self, api_url: str, api_secret: str):
        """
        初始化支付检查器

        Args:
            api_url: A服务器查询API地址 (例如: http://192.168.1.100:6000)
            api_secret: 查询API密钥（与A服务器config.json中的query_api.secret一致）
        """
        self.api_url = api_url.rstrip('/')
        self.api_secret = api_secret

    def _generate_signature(self, params: dict, timestamp: str) -> str:
        """
        生成请求签名

        Args:
            params: 请求参数
            timestamp: 请求时间戳

        Returns:
            str: HMAC-SHA256签名
        """
        # 参数按字母排序
        sorted_params = sorted(params.items())
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # 生成签名字符串
        sign_str = f"{param_str}&timestamp={timestamp}&secret={self.api_secret}"

        # 计算HMAC-SHA256
        signature = hmac.new(
            bytes(self.api_secret, encoding='utf8'),
            bytes(sign_str, encoding='utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        return signature

    def query_transfers(self, amount: Optional[float] = None,
                       currency: str = 'USDT',
                       min_amount: Optional[float] = None,
                       max_amount: Optional[float] = None) -> Dict:
        """
        查询转账记录

        Args:
            amount: 精确金额查询（可选）
            currency: 币种，默认USDT
            min_amount: 最小金额（可选）
            max_amount: 最大金额（可选）

        Returns:
            dict: 查询结果
        """
        try:
            # 构建查询参数
            params = {}

            if amount is not None:
                params['amount'] = str(amount)

            if currency:
                params['currency'] = currency

            if min_amount is not None:
                params['min_amount'] = str(min_amount)

            if max_amount is not None:
                params['max_amount'] = str(max_amount)

            # 生成时间戳
            timestamp = str(int(time.time()))

            # 生成签名
            signature = self._generate_signature(params, timestamp)

            # 添加签名和时间戳
            params['signature'] = signature
            params['timestamp'] = timestamp

            # 发送请求
            response = requests.get(
                f"{self.api_url}/api/query",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'message': f'HTTP错误: {response.status_code}',
                    'response': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'查询异常: {str(e)}'
            }

    def check_payment(self, amount: float, currency: str = 'USDT') -> Dict:
        """
        检查支付是否存在

        Args:
            amount: 金额
            currency: 币种，默认USDT

        Returns:
            dict: 检查结果，包含found字段表示是否找到
        """
        try:
            # 构建查询参数
            params = {
                'amount': str(amount),
                'currency': currency
            }

            # 生成时间戳
            timestamp = str(int(time.time()))

            # 生成签名
            signature = self._generate_signature(params, timestamp)

            # 添加签名和时间戳
            params['signature'] = signature
            params['timestamp'] = timestamp

            # 发送请求
            response = requests.get(
                f"{self.api_url}/api/check",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'message': f'HTTP错误: {response.status_code}',
                    'response': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'检查异常: {str(e)}'
            }


# ==================== 使用示例 ====================

def example_usage():
    """使用示例"""

    # 配置（请修改为实际值）
    A_SERVER_URL = "http://192.168.1.100:6000"  # A服务器查询API地址
    API_SECRET = "your_query_api_secret_key_change_this"  # 与A服务器配置一致

    # 创建检查器
    checker = OKXPaymentChecker(A_SERVER_URL, API_SECRET)

    print("=" * 80)
    print("OKX 支付查询示例")
    print("=" * 80)

    # 示例1: 查询所有转账记录
    print("\n1. 查询所有USDT转账记录:")
    print("-" * 80)
    result = checker.query_transfers(currency='USDT')

    if result['success']:
        data = result['data']
        print(f"✓ 查询成功!")
        print(f"  最后更新: {data['last_update']}")
        print(f"  记录总数: {data['total_count']}")
        print(f"  符合条件: {data['count']} 条")

        if data['transfers']:
            print("\n  转账记录:")
            for i, transfer in enumerate(data['transfers'][:5], 1):  # 只显示前5条
                print(f"  [{i}] {transfer['amount']} {transfer['currency']} - {transfer['bill_time']}")
        else:
            print("  无转账记录")
    else:
        print(f"✗ 查询失败: {result['message']}")

    # 示例2: 查询特定金额
    print("\n2. 查询特定金额 88.02 USDT:")
    print("-" * 80)
    result = checker.query_transfers(amount=88.02, currency='USDT')

    if result['success']:
        data = result['data']
        print(f"✓ 查询成功!")
        print(f"  找到 {data['count']} 条匹配记录")

        if data['transfers']:
            for transfer in data['transfers']:
                print(f"  - {transfer['amount']} {transfer['currency']}")
                print(f"    转账时间: {transfer['bill_time']}")
                print(f"    账单ID: {transfer['bill_id']}")
        else:
            print("  ⚠️  未找到匹配的转账记录")
    else:
        print(f"✗ 查询失败: {result['message']}")

    # 示例3: 快速检查支付
    print("\n3. 快速检查支付 88.02 USDT:")
    print("-" * 80)
    result = checker.check_payment(88.02, 'USDT')

    if result['success']:
        data = result['data']
        if data['found']:
            print("✓ 支付已找到!")
            transfer = data['transfer']
            print(f"  金额: {transfer['amount']} {transfer['currency']}")
            print(f"  转账时间: {transfer['bill_time']}")
            print(f"  账单ID: {transfer['bill_id']}")
        else:
            print("⚠️  支付未找到（可能还未到账或已超过2小时）")
    else:
        print(f"✗ 检查失败: {result['message']}")

    # 示例4: 查询金额范围
    print("\n4. 查询金额范围 50-100 USDT:")
    print("-" * 80)
    result = checker.query_transfers(min_amount=50, max_amount=100, currency='USDT')

    if result['success']:
        data = result['data']
        print(f"✓ 查询成功!")
        print(f"  找到 {data['count']} 条记录")

        if data['transfers']:
            for transfer in data['transfers'][:5]:  # 只显示前5条
                print(f"  - {transfer['amount']} {transfer['currency']} - {transfer['bill_time']}")
    else:
        print(f"✗ 查询失败: {result['message']}")

    print("\n" + "=" * 80)


# ==================== Flask集成示例 ====================

from flask import Flask, request, jsonify

app = Flask(__name__)

# 全局配置
A_SERVER_URL = "http://192.168.1.100:6000"
API_SECRET = "your_query_api_secret_key_change_this"
checker = OKXPaymentChecker(A_SERVER_URL, API_SECRET)


@app.route('/api/verify_payment', methods=['POST'])
def verify_payment():
    """
    验证用户支付接口

    POST JSON:
    {
        "order_id": "ORDER123456",
        "amount": 88.02,
        "currency": "USDT"
    }

    返回:
    {
        "success": true,
        "paid": true,
        "transfer": {...}
    }
    """
    try:
        data = request.json

        if not data or 'amount' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需参数: amount'
            }), 400

        amount = float(data['amount'])
        currency = data.get('currency', 'USDT')

        # 检查支付
        result = checker.check_payment(amount, currency)

        if not result['success']:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500

        # 返回结果
        return jsonify({
            'success': True,
            'paid': result['data']['found'],
            'transfer': result['data']['transfer'],
            'order_id': data.get('order_id')
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'验证失败: {str(e)}'
        }), 500


@app.route('/api/query_recent', methods=['GET'])
def query_recent():
    """
    查询最近的转账记录

    GET参数:
    - currency: 币种（可选，默认USDT）
    - min_amount: 最小金额（可选）
    - max_amount: 最大金额（可选）
    """
    try:
        currency = request.args.get('currency', 'USDT')
        min_amount = request.args.get('min_amount')
        max_amount = request.args.get('max_amount')

        # 转换参数
        if min_amount:
            min_amount = float(min_amount)
        if max_amount:
            max_amount = float(max_amount)

        # 查询
        result = checker.query_transfers(
            currency=currency,
            min_amount=min_amount,
            max_amount=max_amount
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询失败: {str(e)}'
        }), 500


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'flask':
        # Flask服务模式
        print("=" * 80)
        print("B服务器 - Flask服务模式")
        print("=" * 80)
        print("验证支付: POST http://localhost:8000/api/verify_payment")
        print("查询记录: GET http://localhost:8000/api/query_recent")
        print("=" * 80)

        app.run(host='0.0.0.0', port=8000, debug=True)
    else:
        # 示例模式
        example_usage()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B服务器示例代码
演示如何：
1. 向A服务器提交支付订单
2. 接收A服务器的支付结果回调
"""

from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import json
import time
from datetime import datetime

app = Flask(__name__)

# ==================== 配置 ====================
A_SERVER_URL = "http://your-a-server-ip:5000"  # A服务器地址
WEBHOOK_SECRET = "CHUHAI7COM"  # Webhook签名密钥（与A服务器配置一致）


# ==================== 1. 向A服务器提交订单 ====================
def create_payment_order(order_id: str, amount: float, currency: str = 'USDT'):
    """
    创建支付订单
    
    Args:
        order_id: 订单号
        amount: 金额
        currency: 币种
    
    Returns:
        dict: 订单创建结果
    """
    try:
        # 准备订单数据
        order_data = {
            'order_id': order_id,
            'amount': str(amount),
            'currency': currency,
            'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'callback_url': 'http://your-b-server.com/api/payment/callback'  # 你的回调地址
        }
        
        # 发送到A服务器
        response = requests.post(
            f"{A_SERVER_URL}/api/order/create",
            json=order_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ 订单创建成功: {order_id}")
            return result
        else:
            print(f"✗ 订单创建失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ 订单创建异常: {str(e)}")
        return None


# ==================== 2. 查询订单状态 ====================
def query_order_status(order_id: str):
    """
    查询订单状态
    
    Args:
        order_id: 订单号
    
    Returns:
        dict: 订单状态信息
    """
    try:
        response = requests.get(
            f"{A_SERVER_URL}/api/order/status/{order_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            print(f"✗ 查询失败: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ 查询异常: {str(e)}")
        return None


# ==================== 3. 接收A服务器回调 ====================
@app.route('/api/payment/callback', methods=['POST'])
def payment_callback():
    """
    接收A服务器的支付结果回调
    
    回调数据格式:
    {
        "order_id": "ORDER123456",
        "amount": "88.02",
        "currency": "USDT",
        "create_time": "2025-11-15 12:30:00",
        "status": "success" or "failed",
        "matched_bill_id": "3020596814559830016",
        "matched_time": "2025-11-15 12:35:20",
        "timestamp": 1762927448
    }
    
    Headers:
    X-Webhook-Signature: HMAC-SHA256签名
    X-Webhook-Timestamp: 时间戳
    """
    try:
        # 获取签名和时间戳
        signature = request.headers.get('X-Webhook-Signature')
        timestamp = request.headers.get('X-Webhook-Timestamp')
        
        if not signature or not timestamp:
            return jsonify({'success': False, 'message': '缺少签名或时间戳'}), 400
        
        # 验证时间戳（5分钟内有效）
        current_time = int(time.time())
        request_time = int(timestamp)
        if abs(current_time - request_time) > 300:
            return jsonify({'success': False, 'message': '请求已过期'}), 400
        
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': '无效的JSON数据'}), 400
        
        # 验证签名（使用排序后的JSON字符串，与A服务器保持一致）
        payload_str = json.dumps(data, sort_keys=True)
        expected_signature = hmac.new(
            bytes(WEBHOOK_SECRET, encoding='utf8'),
            bytes(payload_str, encoding='utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if signature != expected_signature:
            return jsonify({'success': False, 'message': '签名验证失败'}), 403
        
        # 处理回调数据
        print("="*80)
        print("收到支付回调")
        print("="*80)
        print(f"订单号: {data['order_id']}")
        print(f"金额: {data['amount']} {data['currency']}")
        print(f"状态: {data['status']}")
        print(f"创建时间: {data['create_time']}")
        
        if data['status'] == 'success':
            print(f"匹配账单: {data['matched_bill_id']}")
            print(f"匹配时间: {data['matched_time']}")
            print("✓ 支付成功!")
            
            # TODO: 在这里处理你的业务逻辑
            # 例如：更新订单状态、发货、通知用户等
            
        else:
            print("✗ 支付失败（超时未收到款项）")
            
            # TODO: 在这里处理支付失败的逻辑
            # 例如：取消订单、通知用户等
        
        print("="*80)
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '回调处理成功',
            'order_id': data['order_id']
        }), 200
        
    except Exception as e:
        print(f"✗ 回调处理异常: {str(e)}")
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'}), 500


# ==================== 测试示例 ====================
@app.route('/test/create_order', methods=['GET'])
def test_create_order():
    """测试创建订单"""
    import random
    
    order_id = f"TEST{int(time.time())}{random.randint(1000, 9999)}"
    amount = 88.02
    
    result = create_payment_order(order_id, amount)
    
    if result:
        return jsonify({
            'success': True,
            'message': '测试订单创建成功',
            'order_id': order_id,
            'amount': amount,
            'tip': f'请在60分钟内向OKX账户转账 {amount} USDT'
        }), 200
    else:
        return jsonify({'success': False, 'message': '订单创建失败'}), 500


@app.route('/test/query_order/<order_id>', methods=['GET'])
def test_query_order(order_id):
    """测试查询订单"""
    result = query_order_status(order_id)
    
    if result:
        return jsonify(result), 200
    else:
        return jsonify({'success': False, 'message': '查询失败'}), 500


if __name__ == '__main__':
    print("="*80)
    print("B服务器示例启动")
    print("="*80)
    print("测试接口:")
    print("  创建订单: GET http://localhost:8000/test/create_order")
    print("  查询订单: GET http://localhost:8000/test/query_order/<order_id>")
    print("  回调接口: POST http://localhost:8000/api/payment/callback")
    print("="*80)
    
    app.run(host='0.0.0.0', port=8000, debug=True)


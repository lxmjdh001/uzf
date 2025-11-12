#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B服务器 Webhook接收示例
这是一个简单的Flask服务器，用于接收A服务器推送的转账通知
"""

from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import time

app = Flask(__name__)

# ==================== 配置 ====================
# 这个密钥必须与A服务器的WEBHOOK_SECRET相同
WEBHOOK_SECRET = "your_webhook_secret_key_here"

# 签名有效期（秒）
SIGNATURE_VALID_SECONDS = 300  # 5分钟
# =============================================


def verify_signature(payload: str, signature: str, timestamp: str) -> bool:
    """
    验证Webhook签名
    
    Args:
        payload: 请求体JSON字符串
        signature: 请求头中的签名
        timestamp: 请求头中的时间戳
        
    Returns:
        是否验证通过
    """
    # 检查时间戳是否在有效期内
    try:
        request_time = int(timestamp) / 1000  # 转换为秒
        current_time = time.time()
        
        if abs(current_time - request_time) > SIGNATURE_VALID_SECONDS:
            print(f"✗ 签名已过期: 请求时间={request_time}, 当前时间={current_time}")
            return False
    except:
        print("✗ 时间戳格式错误")
        return False
    
    # 计算签名
    expected_signature = hmac.new(
        bytes(WEBHOOK_SECRET, encoding='utf8'),
        bytes(payload, encoding='utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # 比较签名
    if signature != expected_signature:
        print(f"✗ 签名验证失败")
        print(f"  期望: {expected_signature}")
        print(f"  实际: {signature}")
        return False
    
    return True


@app.route('/api/webhook/transfer', methods=['POST'])
def receive_transfer():
    """
    接收转账通知的Webhook接口
    
    请求格式:
    {
        "bill_id": "账单ID",
        "amount": "转账金额",
        "currency": "币种",
        "balance": "当前余额",
        "transfer_type": "转账类型",
        "sub_type": "子类型代码",
        "bill_timestamp": 账单时间戳,
        "bill_time": "账单时间",
        "monitor_timestamp": 监控时间戳,
        "monitor_time": "监控时间"
    }
    
    请求头:
    X-Webhook-Signature: 签名
    X-Webhook-Timestamp: 时间戳
    """
    try:
        # 获取请求头
        signature = request.headers.get('X-Webhook-Signature', '')
        timestamp = request.headers.get('X-Webhook-Timestamp', '')
        
        if not signature or not timestamp:
            return jsonify({
                'success': False,
                'error': '缺少签名或时间戳'
            }), 400
        
        # 获取请求体
        payload = request.get_data(as_text=True)
        
        # 验证签名
        if not verify_signature(payload, signature, timestamp):
            return jsonify({
                'success': False,
                'error': '签名验证失败'
            }), 401
        
        # 解析数据
        data = json.loads(payload)
        
        # 打印接收到的数据
        print("\n" + "="*80)
        print("🎉 收到转账通知!")
        print("="*80)
        print(f"账单ID: {data.get('bill_id')}")
        print(f"转账金额: +{data.get('amount')} {data.get('currency')}")
        print(f"当前余额: {data.get('balance')} {data.get('currency')}")
        print(f"转账类型: {data.get('transfer_type')}")
        print(f"转账时间: {data.get('bill_time')} ({data.get('bill_timestamp')})")
        print(f"监控时间: {data.get('monitor_time')} ({data.get('monitor_timestamp')})")
        print("="*80)
        
        # ==================== 在这里添加你的业务逻辑 ====================
        # 例如:
        # 1. 保存到数据库
        # save_to_database(data)
        
        # 2. 发送通知
        # send_notification(data)
        
        # 3. 触发其他业务流程
        # trigger_business_logic(data)
        
        # 示例: 保存到文件
        with open('received_transfers.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        # ===============================================================
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '转账通知已接收',
            'bill_id': data.get('bill_id')
        }), 200
        
    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'error': 'JSON格式错误'
        }), 400
        
    except Exception as e:
        print(f"✗ 处理Webhook时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'service': 'B Server Webhook Receiver',
        'timestamp': int(time.time() * 1000)
    })


@app.route('/', methods=['GET'])
def index():
    """首页"""
    return """
    <h1>B服务器 Webhook接收器</h1>
    <p>状态: 运行中</p>
    <p>Webhook接口: POST /api/webhook/transfer</p>
    <p>健康检查: GET /api/health</p>
    """


if __name__ == '__main__':
    print("="*80)
    print("B服务器 Webhook接收器启动")
    print("="*80)
    print(f"Webhook接口: http://0.0.0.0:5000/api/webhook/transfer")
    print(f"健康检查: http://0.0.0.0:5000/api/health")
    print("="*80)
    
    # 启动Flask服务器
    # 生产环境建议使用 gunicorn 或 uwsgi
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False  # 生产环境设置为False
    )


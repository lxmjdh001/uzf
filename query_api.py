#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX 转账记录查询API - 带签名验证
功能：
1. 提供HTTP API供B服务器查询转账记录
2. 使用HMAC-SHA256签名验证请求
3. 只返回近2小时的有效记录
"""

from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

# 全局配置
CONFIG = {}
JSON_FILE = "okx_transfers.json"
API_SECRET = ""


def load_config():
    """加载配置文件"""
    global CONFIG, JSON_FILE, API_SECRET

    config_file = 'config.json'

    if not os.path.exists(config_file):
        print(f"✗ 配置文件不存在: {config_file}")
        return False

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            CONFIG = json.load(f)

        JSON_FILE = CONFIG.get('monitor', {}).get('json_file', 'okx_transfers.json')
        API_SECRET = CONFIG.get('query_api', {}).get('secret', '')

        if not API_SECRET:
            print("✗ 配置文件中缺少 query_api.secret")
            return False

        print("✓ 配置文件加载成功")
        return True

    except Exception as e:
        print(f"✗ 加载配置文件失败: {str(e)}")
        return False


def verify_signature(params: dict, signature: str, timestamp: str) -> bool:
    """
    验证请求签名

    Args:
        params: 请求参数
        signature: 客户端提供的签名
        timestamp: 请求时间戳

    Returns:
        bool: 签名是否有效
    """
    try:
        # 1. 验证时间戳（30分钟内有效，防重放攻击）
        current_time = int(time.time())
        request_time = int(timestamp)

        if abs(current_time - request_time) > 1800:
            print(f"⚠️  请求已过期: 当前时间={current_time}, 请求时间={request_time}")
            return False

        # 2. 生成签名字符串（参数按字母排序）
        sorted_params = sorted(params.items())
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        sign_str = f"{param_str}&timestamp={timestamp}&secret={API_SECRET}"

        # 3. 计算HMAC-SHA256签名
        expected_signature = hmac.new(
            bytes(API_SECRET, encoding='utf8'),
            bytes(sign_str, encoding='utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        # 4. 比对签名
        if signature != expected_signature:
            print(f"⚠️  签名验证失败")
            print(f"   预期: {expected_signature}")
            print(f"   实际: {signature}")
            return False

        return True

    except Exception as e:
        print(f"✗ 签名验证异常: {str(e)}")
        return False


def load_transfers_from_json() -> dict:
    """从JSON文件加载转账记录"""
    try:
        if not os.path.exists(JSON_FILE):
            return {
                'success': False,
                'message': 'JSON文件不存在，请先启动监控服务',
                'transfers': [],
                'count': 0
            }

        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return {
            'success': True,
            'last_update': data.get('last_update', ''),
            'last_update_timestamp': data.get('last_update_timestamp', 0),
            'transfers': data.get('transfers', []),
            'count': data.get('count', 0)
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'读取JSON文件失败: {str(e)}',
            'transfers': [],
            'count': 0
        }


@app.route('/api/query', methods=['GET', 'POST'])
def query_transfers():
    """
    查询转账记录接口

    GET参数或POST JSON:
    - amount: (可选) 金额筛选
    - currency: (可选) 币种筛选，默认USDT
    - min_amount: (可选) 最小金额
    - max_amount: (可选) 最大金额
    - signature: (必需) 请求签名
    - timestamp: (必需) 请求时间戳

    返回:
    {
        "success": true,
        "data": {
            "last_update": "2025-11-15 12:30:00",
            "transfers": [...],
            "count": 10
        }
    }
    """
    try:
        # 获取参数
        if request.method == 'POST':
            params = request.json or {}
        else:
            params = request.args.to_dict()

        # 提取签名和时间戳
        signature = params.pop('signature', '')
        timestamp = params.pop('timestamp', '')

        if not signature or not timestamp:
            return jsonify({
                'success': False,
                'message': '缺少签名或时间戳参数'
            }), 400

        # 验证签名
        if not verify_signature(params, signature, timestamp):
            return jsonify({
                'success': False,
                'message': '签名验证失败'
            }), 403

        # 加载转账记录
        result = load_transfers_from_json()

        if not result['success']:
            return jsonify(result), 500

        # 筛选记录
        transfers = result['transfers']

        # 按金额筛选
        if 'amount' in params:
            try:
                amount = float(params['amount'])
                transfers = [t for t in transfers if abs(t['amount'] - amount) < 0.00000001]
            except ValueError:
                return jsonify({'success': False, 'message': '金额格式错误'}), 400

        # 按币种筛选
        if 'currency' in params:
            currency = params['currency'].upper()
            transfers = [t for t in transfers if t['currency'] == currency]

        # 按最小金额筛选
        if 'min_amount' in params:
            try:
                min_amount = float(params['min_amount'])
                transfers = [t for t in transfers if t['amount'] >= min_amount]
            except ValueError:
                return jsonify({'success': False, 'message': '最小金额格式错误'}), 400

        # 按最大金额筛选
        if 'max_amount' in params:
            try:
                max_amount = float(params['max_amount'])
                transfers = [t for t in transfers if t['amount'] <= max_amount]
            except ValueError:
                return jsonify({'success': False, 'message': '最大金额格式错误'}), 400

        # 记录查询日志
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 查询请求: {params} -> {len(transfers)} 条记录")

        # 返回结果
        return jsonify({
            'success': True,
            'data': {
                'last_update': result['last_update'],
                'last_update_timestamp': result['last_update_timestamp'],
                'transfers': transfers,
                'count': len(transfers),
                'total_count': result['count']
            }
        }), 200

    except Exception as e:
        print(f"✗ 查询异常: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'查询失败: {str(e)}'
        }), 500


@app.route('/api/check', methods=['GET'])
def check_payment():
    """
    检查支付接口 - 快速验证某笔金额是否存在

    GET参数:
    - amount: (必需) 金额
    - currency: (可选) 币种，默认USDT
    - signature: (必需) 请求签名
    - timestamp: (必需) 请求时间戳

    返回:
    {
        "success": true,
        "data": {
            "found": true,
            "transfer": {...}  // 找到的转账记录
        }
    }
    """
    try:
        # 获取参数
        params = request.args.to_dict()

        # 提取签名和时间戳
        signature = params.pop('signature', '')
        timestamp = params.pop('timestamp', '')

        if not signature or not timestamp:
            return jsonify({
                'success': False,
                'message': '缺少签名或时间戳参数'
            }), 400

        # 验证必需参数
        if 'amount' not in params:
            return jsonify({
                'success': False,
                'message': '缺少金额参数'
            }), 400

        # 验证签名
        if not verify_signature(params, signature, timestamp):
            return jsonify({
                'success': False,
                'message': '签名验证失败'
            }), 403

        # 加载转账记录
        result = load_transfers_from_json()

        if not result['success']:
            return jsonify(result), 500

        # 查找匹配的转账
        try:
            amount = float(params['amount'])
            currency = params.get('currency', 'USDT').upper()

            for transfer in result['transfers']:
                if (abs(transfer['amount'] - amount) < 0.00000001 and
                    transfer['currency'] == currency):
                    # 找到匹配
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 支付检查: {amount} {currency} -> 已找到")

                    return jsonify({
                        'success': True,
                        'data': {
                            'found': True,
                            'transfer': transfer
                        }
                    }), 200

            # 未找到
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 支付检查: {amount} {currency} -> 未找到")

            return jsonify({
                'success': True,
                'data': {
                    'found': False,
                    'transfer': None
                }
            }), 200

        except ValueError:
            return jsonify({'success': False, 'message': '金额格式错误'}), 400

    except Exception as e:
        print(f"✗ 检查异常: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'检查失败: {str(e)}'
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'service': 'okx-query-api',
        'timestamp': int(time.time())
    }), 200


def main():
    """主函数"""
    print("=" * 80)
    print("OKX 转账记录查询API")
    print("=" * 80)

    # 加载配置
    if not load_config():
        return

    # 获取API配置
    api_config = CONFIG.get('query_api', {})
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 6000)

    print(f"\n数据文件: {JSON_FILE}")
    print(f"API地址: http://{host}:{port}")
    print(f"查询接口: GET/POST http://{host}:{port}/api/query")
    print(f"检查接口: GET http://{host}:{port}/api/check")
    print(f"健康检查: GET http://{host}:{port}/health")
    print("=" * 80)

    # 启动Flask服务
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()

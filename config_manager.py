#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 从配置文件读取和保存配置
"""

import json
import os
import pymysql
from typing import Dict, Optional


CONFIG_FILE = 'config.json'


def load_config() -> Optional[Dict]:
    """
    从配置文件加载配置
    
    Returns:
        配置字典，如果文件不存在返回 None
    """
    if not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"✗ 读取配置文件失败: {str(e)}")
        return None


def save_config(config: Dict):
    """
    保存配置到文件
    
    Args:
        config: 配置字典
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 设置文件权限为仅所有者可读（600）
        os.chmod(CONFIG_FILE, 0o600)
        print(f"✓ 配置已保存到 {CONFIG_FILE}")
    except Exception as e:
        print(f"✗ 保存配置文件失败: {str(e)}")
        raise


def get_db_config() -> Optional[Dict]:
    """
    从配置文件获取数据库配置
    
    Returns:
        数据库配置字典
    """
    config = load_config()
    if not config or 'database' not in config:
        return None
    
    db = config['database']
    return {
        'host': db.get('host', 'localhost'),
        'port': int(db.get('port', 3306)),
        'user': db.get('user', 'root'),
        'password': db.get('password', ''),
        'database': db.get('database', 'okx_monitor'),
        'charset': 'utf8mb4'
    }


def get_okx_config() -> Optional[Dict]:
    """
    从配置文件获取OKX配置
    
    Returns:
        OKX配置字典
    """
    config = load_config()
    if not config or 'okx' not in config:
        return None
    
    okx = config['okx']
    if not all([okx.get('api_key'), okx.get('secret_key'), okx.get('passphrase')]):
        return None
    
    return {
        'api_key': okx['api_key'],
        'secret_key': okx['secret_key'],
        'passphrase': okx['passphrase'],
        'is_demo': okx.get('is_demo', False)
    }


def get_webhook_config() -> Optional[Dict]:
    """
    从配置文件获取Webhook配置
    
    Returns:
        Webhook配置字典
    """
    config = load_config()
    if not config or 'webhook' not in config:
        return None
    
    webhook = config['webhook']
    if not all([webhook.get('url'), webhook.get('secret')]):
        return None
    
    return {
        'url': webhook['url'],
        'secret': webhook['secret']
    }


def main():
    """主函数 - 配置向导"""
    print("="*80)
    print("OKX 监控系统 - 配置向导")
    print("="*80)
    
    # 加载现有配置
    config = load_config() or {}
    
    # 配置数据库
    print("\n" + "="*80)
    print("数据库配置")
    print("="*80)
    
    if 'database' in config:
        print("\n当前配置:")
        db = config['database']
        print(f"  地址: {db.get('host', 'localhost')}")
        print(f"  端口: {db.get('port', 3306)}")
        print(f"  用户: {db.get('user', 'root')}")
        print(f"  数据库: {db.get('database', 'okx_monitor')}")
        
        change = input("\n是否修改数据库配置? (y/N): ").strip().lower()
        if change != 'y':
            db_config = {
                'host': db.get('host', 'localhost'),
                'port': int(db.get('port', 3306)),
                'user': db.get('user', 'root'),
                'password': db.get('password', ''),
                'database': db.get('database', 'okx_monitor')
            }
        else:
            db_host = input("数据库地址 (默认: localhost): ").strip() or 'localhost'
            db_port = input("数据库端口 (默认: 3306): ").strip() or '3306'
            db_user = input("数据库用户名 (默认: root): ").strip() or 'root'
            db_password = input("数据库密码: ").strip()
            db_name = input("数据库名 (默认: okx_monitor): ").strip() or 'okx_monitor'
            
            config['database'] = {
                'host': db_host,
                'port': int(db_port),
                'user': db_user,
                'password': db_password,
                'database': db_name
            }
            db_config = {
                'host': db_host,
                'port': int(db_port),
                'user': db_user,
                'password': db_password,
                'database': db_name,
                'charset': 'utf8mb4'
            }
    else:
        print("\n请输入MySQL数据库连接信息:\n")
        db_host = input("数据库地址 (默认: localhost): ").strip() or 'localhost'
        db_port = input("数据库端口 (默认: 3306): ").strip() or '3306'
        db_user = input("数据库用户名 (默认: root): ").strip() or 'root'
        db_password = input("数据库密码: ").strip()
        db_name = input("数据库名 (默认: okx_monitor): ").strip() or 'okx_monitor'
        
        config['database'] = {
            'host': db_host,
            'port': int(db_port),
            'user': db_user,
            'password': db_password,
            'database': db_name
        }
        db_config = {
            'host': db_host,
            'port': int(db_port),
            'user': db_user,
            'password': db_password,
            'database': db_name,
            'charset': 'utf8mb4'
        }
    
    # 测试数据库连接
    print("\n正在测试数据库连接...")
    try:
        conn = pymysql.connect(**db_config)
        conn.close()
        print("✓ 数据库连接成功!")
    except Exception as e:
        print(f"✗ 数据库连接失败: {str(e)}")
        print("\n请检查数据库配置后重试")
        return
    
    # 配置OKX API
    print("\n" + "="*80)
    print("OKX API 配置")
    print("="*80)
    
    if 'okx' in config:
        print("\n当前配置:")
        okx = config['okx']
        print(f"  API Key: {okx.get('api_key', '')[:10]}..." if okx.get('api_key') else "  API Key: 未配置")
        print(f"  模拟盘: {'是' if okx.get('is_demo') else '否'}")
        
        change = input("\n是否修改OKX API配置? (y/N): ").strip().lower()
        if change != 'y':
            pass  # 保持现有配置
        else:
            print("\n请输入你的OKX API信息:\n")
            api_key = input("API Key: ").strip()
            secret_key = input("Secret Key: ").strip()
            passphrase = input("Passphrase: ").strip()
            is_demo_input = input("是否为模拟盘? (y/N): ").strip().lower()
            is_demo = is_demo_input == 'y'
            
            config['okx'] = {
                'api_key': api_key,
                'secret_key': secret_key,
                'passphrase': passphrase,
                'is_demo': is_demo
            }
    else:
        print("\n请输入你的OKX API信息:\n")
        api_key = input("API Key: ").strip()
        secret_key = input("Secret Key: ").strip()
        passphrase = input("Passphrase: ").strip()
        is_demo_input = input("是否为模拟盘? (y/N): ").strip().lower()
        is_demo = is_demo_input == 'y'
        
        config['okx'] = {
            'api_key': api_key,
            'secret_key': secret_key,
            'passphrase': passphrase,
            'is_demo': is_demo
        }
    
    # 配置Webhook
    print("\n" + "="*80)
    print("Webhook 配置")
    print("="*80)
    
    if 'webhook' in config:
        print("\n当前配置:")
        webhook = config['webhook']
        print(f"  URL: {webhook.get('url', '未配置')}")
        
        change = input("\n是否修改Webhook配置? (y/N): ").strip().lower()
        if change != 'y':
            pass  # 保持现有配置
        else:
            print("\n请输入Webhook配置信息:\n")
            webhook_url = input("Webhook URL (B服务器接收地址): ").strip()
            webhook_secret = input("Webhook Secret (签名密钥): ").strip()
            
            config['webhook'] = {
                'url': webhook_url,
                'secret': webhook_secret
            }
    else:
        print("\n请输入Webhook配置信息:\n")
        webhook_url = input("Webhook URL (B服务器接收地址): ").strip()
        webhook_secret = input("Webhook Secret (签名密钥): ").strip()
        
        config['webhook'] = {
            'url': webhook_url,
            'secret': webhook_secret
        }
    
    # 保存配置
    print("\n" + "="*80)
    print("保存配置")
    print("="*80)
    save_config(config)
    
    print("\n" + "="*80)
    print("✓ 所有配置已完成!")
    print("="*80)
    print(f"\n配置文件已保存到: {CONFIG_FILE}")
    print("\n现在可以运行监控程序:")
    print("  python3 payment_monitor.py")
    print("\n或者重新配置:")
    print("  python3 config_manager.py")
    print("="*80)


if __name__ == "__main__":
    main()

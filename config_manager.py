#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 从数据库读取和保存配置
"""

import pymysql
import getpass
from typing import Dict, Optional


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, db_config: Dict):
        """
        初始化配置管理器
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 创建配置表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS okx_config (
                id INT PRIMARY KEY AUTO_INCREMENT,
                config_key VARCHAR(50) UNIQUE NOT NULL COMMENT '配置键',
                config_value TEXT NOT NULL COMMENT '配置值',
                config_type VARCHAR(20) DEFAULT 'string' COMMENT '配置类型',
                description VARCHAR(200) COMMENT '配置描述',
                is_encrypted TINYINT DEFAULT 0 COMMENT '是否加密 0=否 1=是',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_config_key (config_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='OKX配置表';
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            cursor.close()
            conn.close()
            
            print("✓ 配置表初始化成功")
            
        except Exception as e:
            print(f"✗ 配置表初始化失败: {str(e)}")
            raise
    
    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """
        获取配置
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            select_sql = "SELECT config_value FROM okx_config WHERE config_key = %s"
            cursor.execute(select_sql, (key,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                return result[0]
            return default
            
        except Exception as e:
            print(f"✗ 获取配置失败: {str(e)}")
            return default
    
    def set_config(self, key: str, value: str, config_type: str = 'string', description: str = '', is_encrypted: bool = False):
        """
        设置配置

        Args:
            key: 配置键
            value: 配置值
            config_type: 配置类型 (database/okx/webhook/string)
            description: 配置描述
            is_encrypted: 是否为敏感信息
        """
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            insert_sql = """
            INSERT INTO okx_config (config_key, config_value, config_type, description, is_encrypted)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                config_value = VALUES(config_value),
                config_type = VALUES(config_type),
                description = VALUES(description),
                is_encrypted = VALUES(is_encrypted)
            """

            cursor.execute(insert_sql, (key, value, config_type, description, 1 if is_encrypted else 0))
            conn.commit()
            cursor.close()
            conn.close()

            return True

        except Exception as e:
            print(f"✗ 设置配置失败: {str(e)}")
            return False
    
    def has_config(self, key: str) -> bool:
        """
        检查配置是否存在
        
        Args:
            key: 配置键
            
        Returns:
            是否存在
        """
        return self.get_config(key) is not None
    
    def get_all_okx_config(self) -> Optional[Dict]:
        """
        获取所有OKX配置
        
        Returns:
            配置字典
        """
        api_key = self.get_config('okx_api_key')
        secret_key = self.get_config('okx_secret_key')
        passphrase = self.get_config('okx_passphrase')
        
        if not all([api_key, secret_key, passphrase]):
            return None
        
        return {
            'api_key': api_key,
            'secret_key': secret_key,
            'passphrase': passphrase,
            'is_demo': self.get_config('okx_is_demo', 'false') == 'true'
        }
    
    def setup_okx_config_interactive(self):
        """
        交互式配置OKX API
        """
        print("="*80)
        print("OKX API 配置向导")
        print("="*80)
        print("\n请输入你的OKX API信息:\n")

        # 输入API Key
        api_key = input("API Key: ").strip()

        # 输入Secret Key (可见)
        secret_key = input("Secret Key: ").strip()

        # 输入Passphrase (可见)
        passphrase = input("Passphrase: ").strip()

        # 选择是否为模拟盘
        is_demo_input = input("是否为模拟盘? (y/N): ").strip().lower()
        is_demo = 'true' if is_demo_input == 'y' else 'false'

        # 确认信息
        print("\n" + "-"*80)
        print("请确认以下信息:")
        print(f"API Key: {api_key}")
        print(f"Secret Key: {secret_key}")
        print(f"Passphrase: {passphrase}")
        print(f"模拟盘: {'是' if is_demo == 'true' else '否'}")
        print("-"*80)

        confirm = input("\n确认保存? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("已取消配置")
            return False

        # 保存到数据库
        print("\n正在保存配置...")

        success = True
        success &= self.set_config('okx_api_key', api_key, 'okx', 'OKX API Key', True)
        success &= self.set_config('okx_secret_key', secret_key, 'okx', 'OKX Secret Key', True)
        success &= self.set_config('okx_passphrase', passphrase, 'okx', 'OKX API Passphrase', True)
        success &= self.set_config('okx_is_demo', is_demo, 'okx', 'OKX 是否为模拟盘', False)

        if success:
            print("✓ OKX API配置保存成功!")
            return True
        else:
            print("✗ OKX API配置保存失败!")
            return False
    
    def setup_webhook_config_interactive(self):
        """
        交互式配置Webhook
        """
        print("\n" + "="*80)
        print("Webhook 配置向导")
        print("="*80)
        print("\n请输入Webhook配置信息:\n")

        # 输入Webhook URL
        webhook_url = input("Webhook URL (B服务器接收地址): ").strip()

        # 输入Webhook Secret (可见)
        webhook_secret = input("Webhook Secret (签名密钥): ").strip()

        # 确认信息
        print("\n" + "-"*80)
        print("请确认以下信息:")
        print(f"Webhook URL: {webhook_url}")
        print(f"Webhook Secret: {webhook_secret}")
        print("-"*80)

        confirm = input("\n确认保存? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("已取消配置")
            return False

        # 保存到数据库
        print("\n正在保存配置...")

        success = True
        success &= self.set_config('webhook_url', webhook_url, 'webhook', 'Webhook推送地址', False)
        success &= self.set_config('webhook_secret', webhook_secret, 'webhook', 'Webhook签名密钥', True)

        if success:
            print("✓ Webhook配置保存成功!")
            return True
        else:
            print("✗ Webhook配置保存失败!")
            return False
    
    def get_webhook_config(self) -> Optional[Dict]:
        """
        获取Webhook配置
        
        Returns:
            配置字典
        """
        webhook_url = self.get_config('webhook_url')
        webhook_secret = self.get_config('webhook_secret')
        
        if not all([webhook_url, webhook_secret]):
            return None
        
        return {
            'url': webhook_url,
            'secret': webhook_secret
        }


def main():
    """主函数 - 配置向导"""
    print("="*80)
    print("OKX 监控系统 - 配置向导")
    print("="*80)
    
    # 数据库配置（这个需要手动配置）
    print("\n首先，请输入MySQL数据库连接信息:\n")

    db_host = input("数据库地址 (默认: localhost): ").strip() or 'localhost'
    db_port = input("数据库端口 (默认: 3306): ").strip() or '3306'
    db_user = input("数据库用户名 (默认: root): ").strip() or 'root'
    db_password = input("数据库密码: ").strip()
    db_name = input("数据库名 (默认: okx_monitor): ").strip() or 'okx_monitor'

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

    # 创建配置管理器
    config_manager = ConfigManager(db_config)

    # 保存数据库配置
    print("\n正在保存数据库配置...")
    config_manager.set_config('db_host', db_host, 'database', 'MySQL数据库地址')
    config_manager.set_config('db_port', str(db_port), 'database', 'MySQL数据库端口')
    config_manager.set_config('db_user', db_user, 'database', 'MySQL数据库用户名')
    config_manager.set_config('db_password', db_password, 'database', 'MySQL数据库密码', True)
    config_manager.set_config('db_name', db_name, 'database', 'MySQL数据库名')
    print("✓ 数据库配置已保存")
    
    # 配置OKX API
    if not config_manager.setup_okx_config_interactive():
        return
    
    # 配置Webhook
    if not config_manager.setup_webhook_config_interactive():
        return
    
    print("\n" + "="*80)
    print("✓ 所有配置已完成!")
    print("="*80)
    print("\n现在可以运行监控程序:")
    print("  python3 okx_webhook_monitor.py")
    print("\n或者重新配置:")
    print("  python3 config_manager.py")
    print("="*80)


if __name__ == "__main__":
    main()


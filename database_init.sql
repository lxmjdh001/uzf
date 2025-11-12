-- ============================================
-- OKX 支付监控系统 - 数据库初始化脚本
-- ============================================

-- 使用数据库（根据实际情况修改）
-- USE your_database_name;

-- ============================================
-- 1. 配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `okx_config` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
  `config_value` TEXT NOT NULL COMMENT '配置值',
  `config_type` VARCHAR(50) NOT NULL COMMENT '配置类型(database/okx/webhook/system)',
  `description` VARCHAR(255) DEFAULT NULL COMMENT '配置描述',
  `is_encrypted` TINYINT(1) DEFAULT 0 COMMENT '是否加密(0=否,1=是)',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_config_type` (`config_type`),
  INDEX `idx_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- ============================================
-- 2. 支付订单表
-- ============================================
CREATE TABLE IF NOT EXISTS `payment_orders` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `order_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '订单号（B服务器提供）',
  `amount` DECIMAL(20, 8) NOT NULL COMMENT '订单金额',
  `currency` VARCHAR(20) NOT NULL DEFAULT 'USDT' COMMENT '币种',
  `create_time` DATETIME NOT NULL COMMENT '订单创建时间（B服务器提供）',
  `expire_time` DATETIME NOT NULL COMMENT '订单过期时间（创建时间+60分钟）',
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '订单状态: pending=待支付, matched=已匹配, expired=已过期, cancelled=已取消',
  `matched_bill_id` VARCHAR(100) DEFAULT NULL COMMENT '匹配的OKX账单ID',
  `matched_time` DATETIME DEFAULT NULL COMMENT '匹配时间',
  `callback_url` VARCHAR(500) DEFAULT NULL COMMENT 'B服务器回调地址',
  `callback_status` TINYINT(1) DEFAULT 0 COMMENT '回调状态: 0=未回调, 1=成功, 2=失败',
  `callback_response` TEXT DEFAULT NULL COMMENT '回调响应内容',
  `callback_time` DATETIME DEFAULT NULL COMMENT '回调时间',
  `remark` VARCHAR(500) DEFAULT NULL COMMENT '备注',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
  INDEX `idx_order_id` (`order_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_create_time` (`create_time`),
  INDEX `idx_expire_time` (`expire_time`),
  INDEX `idx_amount` (`amount`),
  INDEX `idx_matched_bill_id` (`matched_bill_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付订单表';

-- ============================================
-- 3. OKX转账记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `okx_transfers` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `bill_id` VARCHAR(100) NOT NULL UNIQUE COMMENT 'OKX账单ID',
  `amount` DECIMAL(20, 8) NOT NULL COMMENT '转账金额',
  `currency` VARCHAR(20) NOT NULL COMMENT '币种',
  `balance` DECIMAL(20, 8) NOT NULL COMMENT '当前余额',
  `transfer_type` VARCHAR(50) NOT NULL COMMENT '转账类型',
  `bill_timestamp` BIGINT NOT NULL COMMENT 'OKX账单时间戳(毫秒)',
  `bill_time` DATETIME NOT NULL COMMENT 'OKX账单时间',
  `matched_order_id` VARCHAR(100) DEFAULT NULL COMMENT '匹配的订单号',
  `matched_time` DATETIME DEFAULT NULL COMMENT '匹配时间',
  `is_matched` TINYINT(1) DEFAULT 0 COMMENT '是否已匹配: 0=未匹配, 1=已匹配',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  INDEX `idx_bill_id` (`bill_id`),
  INDEX `idx_bill_time` (`bill_time`),
  INDEX `idx_amount` (`amount`),
  INDEX `idx_currency` (`currency`),
  INDEX `idx_is_matched` (`is_matched`),
  INDEX `idx_matched_order_id` (`matched_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OKX转账记录表';

-- ============================================
-- 4. 系统日志表（可选）
-- ============================================
CREATE TABLE IF NOT EXISTS `system_logs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
  `log_type` VARCHAR(50) NOT NULL COMMENT '日志类型: order/transfer/callback/system',
  `log_level` VARCHAR(20) NOT NULL DEFAULT 'info' COMMENT '日志级别: debug/info/warning/error',
  `order_id` VARCHAR(100) DEFAULT NULL COMMENT '关联订单号',
  `bill_id` VARCHAR(100) DEFAULT NULL COMMENT '关联账单ID',
  `message` TEXT NOT NULL COMMENT '日志内容',
  `extra_data` JSON DEFAULT NULL COMMENT '额外数据（JSON格式）',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  INDEX `idx_log_type` (`log_type`),
  INDEX `idx_log_level` (`log_level`),
  INDEX `idx_order_id` (`order_id`),
  INDEX `idx_bill_id` (`bill_id`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- ============================================
-- 显示创建结果
-- ============================================
SHOW TABLES;


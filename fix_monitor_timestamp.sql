-- ============================================
-- 修复 okx_transfers 表 - 添加 monitor_timestamp 和 monitor_time 字段
-- ============================================
-- 说明：
-- - bill_timestamp/bill_time: OKX账单本身的时间（转账实际发生时间）
-- - monitor_timestamp/monitor_time: 监控系统发现这条记录的时间（系统轮询时间）
-- ============================================

-- 1. 添加 monitor_timestamp 字段（BIGINT，毫秒时间戳）
ALTER TABLE `okx_transfers` 
ADD COLUMN `monitor_timestamp` BIGINT NOT NULL COMMENT '监控发现时间戳(毫秒)' 
AFTER `bill_time`;

-- 2. 添加 monitor_time 字段（DATETIME，便于查询）
ALTER TABLE `okx_transfers` 
ADD COLUMN `monitor_time` DATETIME NOT NULL COMMENT '监控发现时间' 
AFTER `monitor_timestamp`;

-- 3. 为已存在的记录填充默认值（使用 created_at 作为监控时间）
UPDATE `okx_transfers` 
SET 
    `monitor_timestamp` = UNIX_TIMESTAMP(`created_at`) * 1000,
    `monitor_time` = `created_at`
WHERE `monitor_timestamp` = 0 OR `monitor_time` IS NULL;

-- 4. 验证字段是否添加成功
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM 
    INFORMATION_SCHEMA.COLUMNS
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'okx_transfers'
    AND COLUMN_NAME IN ('monitor_timestamp', 'monitor_time')
ORDER BY ORDINAL_POSITION;


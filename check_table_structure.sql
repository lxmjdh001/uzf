-- ============================================
-- 检查 okx_transfers 表结构
-- 在 phpMyAdmin 中执行此 SQL 来查看表结构
-- ============================================

-- 1. 查看表结构（详细）
DESCRIBE okx_transfers;

-- 2. 查看表结构（SQL 格式）
SHOW CREATE TABLE okx_transfers;

-- 3. 查看 monitor_timestamp 字段的详细信息
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    COLUMN_KEY,
    EXTRA,
    COLUMN_COMMENT
FROM 
    INFORMATION_SCHEMA.COLUMNS
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'okx_transfers'
    AND COLUMN_NAME = 'monitor_timestamp';

-- 4. 查看所有字段（包括 monitor_timestamp）
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT,
    EXTRA,
    COLUMN_COMMENT
FROM 
    INFORMATION_SCHEMA.COLUMNS
WHERE 
    TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'okx_transfers'
ORDER BY ORDINAL_POSITION;


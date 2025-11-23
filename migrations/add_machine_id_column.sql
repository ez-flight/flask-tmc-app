-- Простая миграция: добавление колонки machine_id в таблицу pc_hard_drives
-- Выполнить: mysql -u root -p webuseorg3 < migrations/add_machine_id_column.sql

-- Проверяем и добавляем колонку machine_id
SET @dbname = DATABASE();
SET @tablename = 'pc_hard_drives';
SET @columnname = 'machine_id';

-- Добавляем колонку, если её нет
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
  ) > 0,
  'SELECT "Column already exists" AS result',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' INT NULL COMMENT ''Связь с машиной'' AFTER `created_at`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Добавляем индекс, если его нет
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = 'idx_machine_id')
  ) > 0,
  'SELECT "Index already exists" AS result',
  CONCAT('ALTER TABLE ', @tablename, ' ADD INDEX `idx_machine_id` (`', @columnname, '`)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SELECT 'Migration completed: machine_id column added to pc_hard_drives' AS result;


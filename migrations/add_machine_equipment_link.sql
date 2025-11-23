-- Миграция: добавление связи машины с ТМЦ
-- Выполнить: mysql -u root -p webuseorg3 < migrations/add_machine_equipment_link.sql

-- Проверяем и добавляем колонку equipment_id
SET @dbname = DATABASE();
SET @tablename = 'machines';
SET @columnname = 'equipment_id';

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
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' INT NULL COMMENT ''Связь с ТМЦ'' AFTER `updated_at`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Добавляем внешний ключ, если его нет
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (CONSTRAINT_NAME = 'machines_ibfk_equipment')
  ) > 0,
  'SELECT "Foreign key already exists" AS result',
  CONCAT('ALTER TABLE ', @tablename, ' ADD CONSTRAINT `machines_ibfk_equipment` FOREIGN KEY (`', @columnname, '`) REFERENCES `equipment`(`id`) ON DELETE SET NULL')
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
      AND (INDEX_NAME = 'idx_equipment_id')
  ) > 0,
  'SELECT "Index already exists" AS result',
  CONCAT('ALTER TABLE ', @tablename, ' ADD INDEX `idx_equipment_id` (`', @columnname, '`)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SELECT 'Migration completed: equipment_id column added to machines' AS result;


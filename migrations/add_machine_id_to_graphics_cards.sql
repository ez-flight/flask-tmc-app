-- Миграция: добавление связи видеокарт с машинами
-- Выполнить: mysql -u root -p webuseorg3 < migrations/add_machine_id_to_graphics_cards.sql

-- Проверяем и добавляем колонку machine_id
SET @dbname = DATABASE();
SET @tablename = 'pc_graphics_cards';
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

-- Добавляем внешний ключ, если его нет
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (CONSTRAINT_NAME = 'pc_graphics_cards_ibfk_machine')
  ) > 0,
  'SELECT "Foreign key already exists" AS result',
  CONCAT('ALTER TABLE ', @tablename, ' ADD CONSTRAINT `pc_graphics_cards_ibfk_machine` FOREIGN KEY (`', @columnname, '`) REFERENCES `machines`(`id`) ON DELETE SET NULL')
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

SELECT 'Migration completed: machine_id column added to pc_graphics_cards' AS result;


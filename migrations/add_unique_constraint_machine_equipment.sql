-- Миграция: добавление уникального ограничения на связь машины с ТМЦ (один к одному)
-- Выполнить: mysql -u root -p webuseorg3 < migrations/add_unique_constraint_machine_equipment.sql

-- Проверяем и добавляем уникальный индекс на equipment_id
SET @dbname = DATABASE();
SET @tablename = 'machines';
SET @columnname = 'equipment_id';

-- Проверяем, существует ли уникальный индекс
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
      AND (NON_UNIQUE = 0)
  ) > 0,
  'SELECT "Unique index already exists" AS result',
  CONCAT('ALTER TABLE ', @tablename, ' ADD UNIQUE INDEX `idx_equipment_id_unique` (`', @columnname, '`)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SELECT 'Migration completed: unique constraint added to machines.equipment_id' AS result;


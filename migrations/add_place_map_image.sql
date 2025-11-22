-- Миграция: Добавление поля map_image в таблицу places
-- Дата: 2025
-- Описание: Добавляет поле для хранения пути к схеме помещения

-- Проверяем, существует ли поле, и добавляем его, если нет
-- В MySQL нет IF NOT EXISTS для ADD COLUMN, поэтому используем процедуру

SET @dbname = DATABASE();
SET @tablename = 'places';
SET @columnname = 'map_image';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(255) NULL DEFAULT "" COMMENT "Путь к схеме помещения (PNG, JPG, SVG)" AFTER opgroup')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Альтернативный вариант (если процедура не работает):
-- Раскомментируйте следующую строку и закомментируйте блок выше:
-- ALTER TABLE `places` ADD COLUMN `map_image` VARCHAR(255) NULL DEFAULT '' COMMENT 'Путь к схеме помещения (PNG, JPG, SVG)' AFTER `opgroup`;


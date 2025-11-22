-- Миграция: Обновление таблицы pc_graphics_cards
-- Дата: 2025-11-22
-- Описание: Изменение структуры таблицы видеокарт для использования vendor_id вместо manufacturer

-- Удаляем старую колонку manufacturer
ALTER TABLE `pc_graphics_cards` DROP COLUMN `manufacturer`;

-- Добавляем колонку vendor_id
ALTER TABLE `pc_graphics_cards` 
ADD COLUMN `vendor_id` INT NOT NULL COMMENT 'Производитель из справочника' AFTER `id`;

-- Добавляем внешний ключ для vendor_id
ALTER TABLE `pc_graphics_cards` 
ADD CONSTRAINT `pc_graphics_cards_ibfk_1` FOREIGN KEY (`vendor_id`) REFERENCES `vendor`(`id`) ON DELETE RESTRICT;

-- Добавляем индекс для vendor_id
CREATE INDEX `idx_vendor` ON `pc_graphics_cards` (`vendor_id`);


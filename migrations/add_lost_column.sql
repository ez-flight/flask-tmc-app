-- Миграция: Добавление поля lost (статус "Потерян") в таблицу equipment
-- Выполните этот SQL в MySQL

ALTER TABLE `equipment` 
ADD COLUMN `lost` TINYINT(1) NOT NULL DEFAULT 0 
COMMENT 'Статус: Потерян (0=False, 1=True)' 
AFTER `repair`;


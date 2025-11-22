-- Миграция: Обновление таблицы pc_hard_drives
-- Дата: 2025-11-22
-- Описание: Изменение структуры таблицы жестких дисков для использования vendor_id вместо manufacturer

-- Удаляем старую колонку manufacturer
ALTER TABLE `pc_hard_drives` DROP COLUMN `manufacturer`;

-- Добавляем колонку vendor_id
ALTER TABLE `pc_hard_drives` 
ADD COLUMN `vendor_id` INT NOT NULL COMMENT 'Марка (производитель) - ОБЯЗАТЕЛЬНО' AFTER `id`;

-- Изменяем drive_type на NOT NULL
ALTER TABLE `pc_hard_drives` 
MODIFY COLUMN `drive_type` VARCHAR(50) NOT NULL COMMENT 'Тип (HDD, SSD, NVMe) - ОБЯЗАТЕЛЬНО';

-- Изменяем capacity_gb на NOT NULL
ALTER TABLE `pc_hard_drives` 
MODIFY COLUMN `capacity_gb` INT NOT NULL COMMENT 'Объем в ГБ - ОБЯЗАТЕЛЬНО';

-- Изменяем serial_number на NOT NULL
ALTER TABLE `pc_hard_drives` 
MODIFY COLUMN `serial_number` VARCHAR(100) NOT NULL COMMENT 'Серийный номер - ОБЯЗАТЕЛЬНО';

-- Добавляем новые поля для учета здоровья дисков
ALTER TABLE `pc_hard_drives` 
ADD COLUMN `health_check_date` DATE NULL COMMENT 'Дата проверки здоровья' AFTER `serial_number`,
ADD COLUMN `power_on_count` INT NULL COMMENT 'Число включений' AFTER `health_check_date`,
ADD COLUMN `power_on_hours` INT NULL COMMENT 'Наработка (часы работы)' AFTER `power_on_count`,
ADD COLUMN `health_status` VARCHAR(50) NULL COMMENT 'Здоровье (Здоров, Тревога, Неработает)' AFTER `power_on_hours`;

-- Добавляем внешний ключ для vendor_id
ALTER TABLE `pc_hard_drives` 
ADD CONSTRAINT `pc_hard_drives_ibfk_1` FOREIGN KEY (`vendor_id`) REFERENCES `vendor`(`id`) ON DELETE RESTRICT;

-- Добавляем индекс для vendor_id
CREATE INDEX `idx_vendor` ON `pc_hard_drives` (`vendor_id`);

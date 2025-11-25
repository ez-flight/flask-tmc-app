-- Миграция для расширения таблицы истории жестких дисков
-- Добавляет все поля диска для полного отслеживания изменений

ALTER TABLE `pc_hard_drive_history`
    ADD COLUMN `drive_type` VARCHAR(50) NULL AFTER `check_date`,
    ADD COLUMN `vendor_id` INT NULL AFTER `drive_type`,
    ADD COLUMN `model` VARCHAR(200) NULL AFTER `vendor_id`,
    ADD COLUMN `capacity_gb` INT NULL AFTER `model`,
    ADD COLUMN `serial_number` VARCHAR(100) NULL AFTER `capacity_gb`,
    ADD COLUMN `interface` VARCHAR(50) NULL AFTER `serial_number`,
    ADD COLUMN `purchase_date` DATE NULL AFTER `health_status`,
    ADD COLUMN `purchase_cost` DECIMAL(12, 2) NULL AFTER `purchase_date`,
    ADD COLUMN `machine_id` INT NULL AFTER `purchase_cost`,
    ADD COLUMN `active` BOOLEAN NULL AFTER `machine_id`,
    ADD INDEX `idx_vendor_id` (`vendor_id`),
    ADD INDEX `idx_machine_id` (`machine_id`),
    ADD CONSTRAINT `fk_history_vendor` FOREIGN KEY (`vendor_id`) REFERENCES `vendor` (`id`) ON DELETE SET NULL,
    ADD CONSTRAINT `fk_history_machine` FOREIGN KEY (`machine_id`) REFERENCES `machines` (`id`) ON DELETE SET NULL;


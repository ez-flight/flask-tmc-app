-- Миграция: Создание таблицы истории состояний жестких дисков
-- Дата: 2025-11-22
-- Описание: Таблица для учета изменений состояния жестких дисков во времени

CREATE TABLE IF NOT EXISTS `pc_hard_drive_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `hard_drive_id` INT NOT NULL COMMENT 'ID жесткого диска',
    `check_date` DATE NOT NULL COMMENT 'Дата проверки состояния',
    `power_on_hours` INT NULL COMMENT 'Наработка (часы работы) на момент проверки',
    `power_on_count` INT NULL COMMENT 'Количество включений на момент проверки',
    `health_status` VARCHAR(50) NULL COMMENT 'Здоровье (Здоров, Тревога, Неработает)',
    `comment` TEXT NULL COMMENT 'Комментарий к записи',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи',
    FOREIGN KEY (`hard_drive_id`) REFERENCES `pc_hard_drives`(`id`) ON DELETE CASCADE,
    INDEX `idx_hard_drive_id` (`hard_drive_id`),
    INDEX `idx_check_date` (`check_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='История состояний жестких дисков';


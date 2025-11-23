-- Миграция: Создание таблицы для учета модулей оперативной памяти (ОЗУ)
-- Дата: 2025
-- Описание: Создает таблицу для модулей ОЗУ с детальной информацией

-- Таблица модулей оперативной памяти
CREATE TABLE IF NOT EXISTS `pc_memory_modules` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `capacity_gb` INT NOT NULL COMMENT 'Объем модуля в ГБ',
    `memory_type` VARCHAR(50) NULL COMMENT 'Тип памяти (DDR, DDR2, DDR3, DDR4, DDR5)',
    `speed_mhz` INT NULL COMMENT 'Частота в МГц',
    `manufacturer` VARCHAR(200) NULL COMMENT 'Производитель',
    `part_number` VARCHAR(200) NULL COMMENT 'Номер партии/модель',
    `serial_number` VARCHAR(100) NULL COMMENT 'Серийный номер',
    `location` VARCHAR(100) NULL COMMENT 'Расположение слота (BankLabel или DeviceLocator)',
    `comment` TEXT NULL COMMENT 'Комментарий',
    `active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Активен ли модуль',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    `machine_id` INT NULL COMMENT 'Связь с машиной',
    FOREIGN KEY (`machine_id`) REFERENCES `machines`(`id`) ON DELETE SET NULL,
    INDEX `idx_machine` (`machine_id`),
    INDEX `idx_serial_number` (`serial_number`),
    INDEX `idx_location` (`location`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Модули оперативной памяти - комплектующие ПК';


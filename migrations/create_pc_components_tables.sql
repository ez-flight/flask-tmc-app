-- Миграция: Создание таблиц для учета комплектующих ПК (аппаратное обеспечение)
-- Дата: 2025
-- Описание: Создает таблицы для видеокарт, жестких дисков и их связи с ПК

-- Таблица видеокарт
CREATE TABLE IF NOT EXISTS `pc_graphics_cards` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `vendor_id` INT NOT NULL COMMENT 'Производитель из справочника',
    `model` VARCHAR(200) NOT NULL COMMENT 'Модель видеокарты',
    `memory_size` INT NULL COMMENT 'Объем памяти в МБ',
    `memory_type` VARCHAR(50) NULL COMMENT 'Тип памяти (GDDR5, GDDR6, etc.)',
    `serial_number` VARCHAR(100) NULL COMMENT 'Серийный номер',
    `purchase_date` DATE NULL COMMENT 'Дата приобретения',
    `purchase_cost` DECIMAL(12, 2) NULL COMMENT 'Стоимость приобретения',
    `comment` TEXT NULL COMMENT 'Комментарий',
    `active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Активна ли видеокарта',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    FOREIGN KEY (`vendor_id`) REFERENCES `vendor`(`id`) ON DELETE RESTRICT,
    INDEX `idx_vendor` (`vendor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Видеокарты - комплектующие ПК';

-- Таблица жестких дисков
CREATE TABLE IF NOT EXISTS `pc_hard_drives` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    -- Обязательные поля
    `drive_type` VARCHAR(50) NOT NULL COMMENT 'Тип (HDD, SSD, NVMe) - ОБЯЗАТЕЛЬНО',
    `vendor_id` INT NOT NULL COMMENT 'Марка (производитель) - ОБЯЗАТЕЛЬНО',
    `model` VARCHAR(200) NOT NULL COMMENT 'Модель - ОБЯЗАТЕЛЬНО',
    `capacity_gb` INT NOT NULL COMMENT 'Объем в ГБ - ОБЯЗАТЕЛЬНО',
    `serial_number` VARCHAR(100) NOT NULL COMMENT 'Серийный номер - ОБЯЗАТЕЛЬНО',
    -- Необязательные поля
    `health_check_date` DATE NULL COMMENT 'Дата проверки здоровья',
    `power_on_count` INT NULL COMMENT 'Число включений',
    `power_on_hours` INT NULL COMMENT 'Наработка (часы работы)',
    `health_status` VARCHAR(50) NULL COMMENT 'Здоровье (Здоров, Тревога, Неработает)',
    `comment` TEXT NULL COMMENT 'Комментарий',
    -- Дополнительные поля
    `interface` VARCHAR(50) NULL COMMENT 'Интерфейс (SATA, NVMe, etc.)',
    `purchase_date` DATE NULL COMMENT 'Дата приобретения',
    `purchase_cost` DECIMAL(12, 2) NULL COMMENT 'Стоимость приобретения',
    `active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Активен ли диск',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    FOREIGN KEY (`vendor_id`) REFERENCES `vendor`(`id`) ON DELETE RESTRICT,
    INDEX `idx_vendor` (`vendor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Жесткие диски - комплектующие ПК';

-- Таблица связи комплектующих с ПК
CREATE TABLE IF NOT EXISTS `pc_component_links` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `equipment_id` INT NOT NULL COMMENT 'ID ПК (основного средства)',
    `graphics_card_id` INT NULL COMMENT 'ID видеокарты',
    `hard_drive_id` INT NULL COMMENT 'ID жесткого диска',
    `installed_date` DATE NULL COMMENT 'Дата установки',
    `removed_date` DATE NULL COMMENT 'Дата извлечения',
    `comment` TEXT NULL COMMENT 'Комментарий',
    `active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Активна ли связь',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    FOREIGN KEY (`equipment_id`) REFERENCES `equipment`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`graphics_card_id`) REFERENCES `pc_graphics_cards`(`id`) ON DELETE SET NULL,
    FOREIGN KEY (`hard_drive_id`) REFERENCES `pc_hard_drives`(`id`) ON DELETE SET NULL,
    INDEX `idx_equipment` (`equipment_id`),
    INDEX `idx_graphics_card` (`graphics_card_id`),
    INDEX `idx_hard_drive` (`hard_drive_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Связь комплектующих ПК с основными средствами';


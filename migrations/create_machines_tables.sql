-- Миграция: Создание таблиц для машин/компьютеров
-- Дата: 2025-11-23
-- Описание: Таблицы для хранения информации о компьютерах и истории их изменений

-- Таблица машин
CREATE TABLE IF NOT EXISTS `machines` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `hostname` VARCHAR(255) NOT NULL UNIQUE COMMENT 'Имя компьютера (уникальный идентификатор)',
    `ip_address` VARCHAR(45) NULL COMMENT 'IP-адрес (IPv4 или IPv6)',
    `mac_address` VARCHAR(17) NULL COMMENT 'MAC-адрес основного сетевого адаптера',
    -- Операционная система
    `os_name` VARCHAR(50) NULL COMMENT 'Название ОС (Windows, Linux, macOS)',
    `os_version` VARCHAR(50) NULL COMMENT 'Версия ОС (10, 11, etc.)',
    `os_build` VARCHAR(50) NULL COMMENT 'Номер сборки ОС',
    `os_edition` VARCHAR(50) NULL COMMENT 'Издание ОС (Pro, Home, Enterprise)',
    `os_architecture` VARCHAR(10) NULL COMMENT 'Архитектура (x64, x86, ARM64)',
    -- Аппаратное обеспечение
    `processor` VARCHAR(255) NULL COMMENT 'Модель процессора',
    `memory_gb` INT NULL COMMENT 'Объем оперативной памяти в ГБ',
    `motherboard` VARCHAR(255) NULL COMMENT 'Модель материнской платы',
    `bios_version` VARCHAR(255) NULL COMMENT 'Версия BIOS/UEFI',
    -- Сетевая информация
    `domain` VARCHAR(255) NULL COMMENT 'Домен или рабочая группа',
    `computer_role` VARCHAR(50) NULL COMMENT 'Роль компьютера (WORKSTATION, SERVER, DOMAIN_CONTROLLER)',
    `dns_suffix` VARCHAR(255) NULL COMMENT 'DNS суффикс',
    -- Временные метки
    `first_seen` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Первое обнаружение',
    `last_seen` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Последнее обнаружение',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата обновления',
    INDEX `idx_hostname` (`hostname`),
    INDEX `idx_last_seen` (`last_seen`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Машины/компьютеры - информация о ПК';

-- Таблица истории изменений машин
CREATE TABLE IF NOT EXISTS `machine_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `machine_id` INT NOT NULL COMMENT 'ID машины',
    `changed_field` VARCHAR(50) NULL COMMENT 'Измененное поле',
    `old_value` TEXT NULL COMMENT 'Старое значение',
    `new_value` TEXT NULL COMMENT 'Новое значение',
    `changed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Время изменения',
    `comment` TEXT NULL COMMENT 'Комментарий к изменению',
    FOREIGN KEY (`machine_id`) REFERENCES `machines`(`id`) ON DELETE CASCADE,
    INDEX `idx_machine_id` (`machine_id`),
    INDEX `idx_changed_at` (`changed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='История изменений машин';

-- Добавление поля machine_id в таблицу pc_hard_drives
-- Проверяем, существует ли колонка, и добавляем только если её нет
SET @dbname = DATABASE();
SET @tablename = 'pc_hard_drives';
SET @columnname = 'machine_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' INT NULL COMMENT ''Связь с машиной'' AFTER `created_at`')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Добавление индекса для machine_id (если не существует)
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = 'idx_machine_id')
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD INDEX `idx_machine_id` (`', @columnname, '`)')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Добавление внешнего ключа для machine_id (если не существует)
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (CONSTRAINT_NAME = 'pc_hard_drives_ibfk_machine')
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD CONSTRAINT `pc_hard_drives_ibfk_machine` FOREIGN KEY (`', @columnname, '`) REFERENCES `machines`(`id`) ON DELETE SET NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;


-- Миграция: Добавление уникального индекса на MAC-адрес в таблице machines
-- Дата: 2025
-- Описание: MAC-адрес становится обязательным уникальным идентификатором для машин в API v2

-- Сначала обрабатываем существующие записи с NULL или пустыми MAC-адресами
-- Устанавливаем временные уникальные MAC-адреса для записей без MAC
UPDATE `machines` 
SET `mac_address` = CONCAT('TEMP-', LPAD(id, 12, '0'))
WHERE `mac_address` IS NULL OR `mac_address` = '';

-- Удаляем дублирующиеся MAC-адреса (оставляем только первую запись)
-- Создаем временную таблицу для идентификации дубликатов
CREATE TEMPORARY TABLE IF NOT EXISTS `temp_duplicate_macs` AS
SELECT `mac_address`, MIN(`id`) as `keep_id`
FROM `machines`
WHERE `mac_address` IS NOT NULL AND `mac_address` != ''
GROUP BY `mac_address`
HAVING COUNT(*) > 1;

-- Обновляем дубликаты, устанавливая временные уникальные MAC-адреса
UPDATE `machines` m
INNER JOIN `temp_duplicate_macs` t ON m.`mac_address` = t.`mac_address` AND m.`id` != t.`keep_id`
SET m.`mac_address` = CONCAT('DUP-', LPAD(m.id, 12, '0'));

-- Удаляем временную таблицу
DROP TEMPORARY TABLE IF EXISTS `temp_duplicate_macs`;

-- Теперь добавляем уникальный индекс и делаем поле обязательным
-- Сначала добавляем уникальный индекс
ALTER TABLE `machines`
ADD UNIQUE INDEX `idx_unique_mac_address` (`mac_address`);

-- Делаем поле обязательным (NOT NULL)
ALTER TABLE `machines`
MODIFY COLUMN `mac_address` VARCHAR(17) NOT NULL COMMENT 'MAC-адрес основного сетевого адаптера (уникальный идентификатор для API v2)';


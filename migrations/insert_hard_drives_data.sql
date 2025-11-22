-- Миграция: Добавление данных о жестких дисках
-- Дата: 2025-11-22
-- Описание: Вставка данных о жестких дисках из предоставленного списка

-- Получаем ID существующих производителей
SET @wd_id = (SELECT id FROM vendor WHERE name = 'Western Digital' LIMIT 1);
SET @hp_id = (SELECT id FROM vendor WHERE name = 'HP' LIMIT 1);
SET @toshiba_id = (SELECT id FROM vendor WHERE name = 'Toshiba' LIMIT 1);
SET @seagate_id = (SELECT id FROM vendor WHERE name = 'Seagate' LIMIT 1);

-- Вставляем данные о жестких дисках
-- Формат: drive_type, vendor_id, model, capacity_gb, serial_number, health_check_date, power_on_count, power_on_hours, health_status, comment

INSERT INTO pc_hard_drives (drive_type, vendor_id, model, capacity_gb, serial_number, health_check_date, power_on_count, power_on_hours, health_status, comment, active, created_at)
VALUES 
('HDD', @wd_id, 'WD1005FBYZ', 1000, 'WCC6M1HNK54U', NULL, NULL, NULL, NULL, '', 1, NOW()),

('HDD', @wd_id, 'WD5003ABYX', 500, 'WMAYP3205431', '2025-11-09', 3059, 37554, NULL, 'Пришел со вторым сервоком', 1, NOW()),

('HDD', @wd_id, 'WD5003ABYX', 500, 'WMAYP3213644', '2025-11-09', 3056, 37555, NULL, 'Пришел со вторым сервоком', 1, NOW()),

('HDD', @wd_id, 'WD5003ABYX', 500, 'WMAYP3246820', '2025-11-09', 2918, 37553, NULL, 'Пришел со вторым сервоком', 1, NOW()),

('HDD', @wd_id, 'WD5003ABYX', 500, 'WMAYP3206580', '2025-11-11', 140, 58942, NULL, 'Пришел со первым сервоком', 1, NOW()),

('HDD', @wd_id, 'WD5003ABYX', 500, 'WMAYP3214689', '2025-11-11', 137, 64798, NULL, '', 1, NOW()),

('HDD', @wd_id, 'WD5003AZEX', 500, 'WMC1S0371311', '2025-11-09', 1887, 7406, NULL, 'У меня', 1, NOW()),

('SAS', @hp_id, 'EF0300FATFD', 300, 'J0W9HR3S', '2025-11-13', 3003, 37685, NULL, 'Пришел со вторым сервоком', 1, NOW()),

('HDD', @toshiba_id, 'DT01ACA200', 2000, '55CA6JNAS', NULL, NULL, NULL, NULL, 'Конарев', 1, NOW()),

('HDD', @wd_id, 'WD5003ABYX', 500, 'WMAYP3214738', '2025-11-09', 3264, 37553, 'Тревога', 'Тревога! Пришел со вторым сервоком болен', 1, NOW()),

('HDD', @hp_id, 'MB0500EBZQA', 500, 'Z1M0FTQB', NULL, NULL, NULL, NULL, '', 1, NOW()),

('HDD', @seagate_id, 'ST3750525AS', 750, '9VPBREPY', '2025-10-31', 4660, 19824, 'Тревога', '', 1, NOW()),

('HDD', @seagate_id, 'ST3750525AS', 750, '9VPBESMY', '2025-10-31', 4894, 17797, 'Тревога', '', 1, NOW()),

('HDD', @seagate_id, 'ST3160811AS', 160, '5PT0GPRM', '2025-11-21', NULL, NULL, 'Здоров', 'Суворов', 1, NOW()),

('HDD', @seagate_id, 'ST3120811AS', 120, '5PT0FEMF', '2025-11-21', 1427, 9873, 'Здоров', '', 1, NOW());


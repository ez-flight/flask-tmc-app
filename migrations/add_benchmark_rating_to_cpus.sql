-- Миграция для добавления поля рейтинга производительности процессоров
-- Добавляет поле benchmark_rating для хранения рейтинга с cpubenchmark.net

ALTER TABLE `pc_cpus`
    ADD COLUMN `benchmark_rating` INT NULL AFTER `max_memory_gb`
    COMMENT 'Рейтинг производительности с cpubenchmark.net';


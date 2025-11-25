-- Миграция для добавления расширенных полей процессоров из cpubenchmark.net
-- Добавляет поля для кэша, графики, памяти, PCI Express и других характеристик

ALTER TABLE `pc_cpus`
    ADD COLUMN `memory_channels` INT NULL AFTER `max_memory_gb`,
    ADD COLUMN `memory_frequency_mhz` VARCHAR(50) NULL AFTER `memory_channels`,
    ADD COLUMN `cache_l1_kb` INT NULL AFTER `benchmark_rating`,
    ADD COLUMN `cache_l2_kb` INT NULL AFTER `cache_l1_kb`,
    ADD COLUMN `cache_l3_kb` INT NULL AFTER `cache_l2_kb`,
    ADD COLUMN `integrated_graphics` BOOLEAN NULL AFTER `cache_l3_kb`,
    ADD COLUMN `graphics_name` VARCHAR(100) NULL AFTER `integrated_graphics`,
    ADD COLUMN `graphics_frequency_mhz` INT NULL AFTER `graphics_name`,
    ADD COLUMN `pcie_version` VARCHAR(20) NULL AFTER `graphics_frequency_mhz`,
    ADD COLUMN `pcie_lanes` INT NULL AFTER `pcie_version`,
    ADD COLUMN `unlocked_multiplier` BOOLEAN NULL AFTER `pcie_lanes`,
    ADD COLUMN `ecc_support` BOOLEAN NULL AFTER `unlocked_multiplier`;


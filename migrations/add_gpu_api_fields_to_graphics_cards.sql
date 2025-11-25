-- Миграция: Добавление полей для данных из GPU API в таблицу pc_graphics_cards
-- Дата создания: 2025-11-25

ALTER TABLE pc_graphics_cards
ADD COLUMN launch_date DATE NULL COMMENT 'Дата выпуска видеокарты',
ADD COLUMN code_name VARCHAR(100) NULL COMMENT 'Кодовое имя (например, NV1, NV3)',
ADD COLUMN core_clock_mhz INT NULL COMMENT 'Частота ядра в МГц',
ADD COLUMN memory_clock_mhz INT NULL COMMENT 'Частота памяти в МГц',
ADD COLUMN memory_bandwidth_gbps FLOAT NULL COMMENT 'Пропускная способность памяти в ГБ/с',
ADD COLUMN memory_bus_width_bits INT NULL COMMENT 'Ширина шины памяти в битах',
ADD COLUMN tdp_watts INT NULL COMMENT 'Энергопотребление (TDP) в ваттах',
ADD COLUMN bus_interface VARCHAR(50) NULL COMMENT 'Интерфейс шины (PCI, PCIe, AGP и т.д.)',
ADD COLUMN direct3d_version VARCHAR(20) NULL COMMENT 'Поддержка Direct3D',
ADD COLUMN opengl_version VARCHAR(20) NULL COMMENT 'Поддержка OpenGL',
ADD COLUMN api_data_updated_at DATETIME NULL COMMENT 'Дата последнего обновления данных из API';


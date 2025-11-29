-- Добавление расширенных полей для видеокарт из API gpu-info-api
-- Выполняется только если поля еще не существуют

-- Boost clock
ALTER TABLE pc_graphics_cards 
ADD COLUMN boost_clock_mhz INT NULL COMMENT 'Частота ядра с Boost в МГц';

-- Техпроцесс
ALTER TABLE pc_graphics_cards 
ADD COLUMN fab_nm FLOAT NULL COMMENT 'Техпроцесс в нм';

-- Размер кристалла
ALTER TABLE pc_graphics_cards 
ADD COLUMN die_size_mm2 FLOAT NULL COMMENT 'Размер кристалла в мм²';

-- Конфигурация ядер
ALTER TABLE pc_graphics_cards 
ADD COLUMN core_config VARCHAR(200) NULL COMMENT 'Конфигурация ядер';

-- Пиксельная производительность
ALTER TABLE pc_graphics_cards 
ADD COLUMN fillrate_pixel_gps FLOAT NULL COMMENT 'Пиксельная производительность в GP/s';

-- Текстурная производительность
ALTER TABLE pc_graphics_cards 
ADD COLUMN fillrate_texture_gts FLOAT NULL COMMENT 'Текстурная производительность в GT/s';

-- Цена выпуска
ALTER TABLE pc_graphics_cards 
ADD COLUMN release_price_usd FLOAT NULL COMMENT 'Цена выпуска в USD';

-- Количество SM
ALTER TABLE pc_graphics_cards 
ADD COLUMN sm_count VARCHAR(50) NULL COMMENT 'Количество SM (Streaming Multiprocessors)';

-- Техпроцесс (Process)
ALTER TABLE pc_graphics_cards 
ADD COLUMN process VARCHAR(100) NULL COMMENT 'Техпроцесс (например, TSMC N4)';

-- Количество транзисторов
ALTER TABLE pc_graphics_cards 
ADD COLUMN transistors_billion FLOAT NULL COMMENT 'Количество транзисторов в миллиардах';

-- Кэш L
ALTER TABLE pc_graphics_cards 
ADD COLUMN l_cache_mb FLOAT NULL COMMENT 'Кэш L в МБ';

-- Single-precision TFLOPS
ALTER TABLE pc_graphics_cards 
ADD COLUMN single_precision_tflops VARCHAR(50) NULL COMMENT 'Single-precision TFLOPS';

-- Double-precision TFLOPS
ALTER TABLE pc_graphics_cards 
ADD COLUMN double_precision_tflops VARCHAR(50) NULL COMMENT 'Double-precision TFLOPS';

-- Half-precision TFLOPS
ALTER TABLE pc_graphics_cards 
ADD COLUMN half_precision_tflops VARCHAR(50) NULL COMMENT 'Half-precision TFLOPS';

-- Количество пиксельных шейдеров
ALTER TABLE pc_graphics_cards 
ADD COLUMN pixel_shader_count FLOAT NULL COMMENT 'Количество пиксельных шейдеров';

-- Тип GPU
ALTER TABLE pc_graphics_cards 
ADD COLUMN gpu_type VARCHAR(50) NULL COMMENT 'Тип GPU (Desktop, Mobile, etc.)';


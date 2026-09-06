-- ==============================================================================
-- SIH26166: Phase 8 - Supabase PostgreSQL Schema Migration
-- Database Architecture for Multi-Sensor Lunar Image Repository (R01 - R10)
-- ==============================================================================

-- Enable PostGIS & UUID extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ------------------------------------------------------------------------------
-- 1. REGIONS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    region_code VARCHAR(50) NOT NULL UNIQUE, -- e.g., 'R01', 'R02', ..., 'R10'
    region_name VARCHAR(255) NOT NULL,
    description TEXT,
    center_latitude DOUBLE PRECISION,
    center_longitude DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_regions_code ON regions(region_code);

-- ------------------------------------------------------------------------------
-- 2. IMAGES
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id VARCHAR(255) NOT NULL UNIQUE,
    region_id UUID NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    sensor VARCHAR(50) NOT NULL,            -- 'OHRC', 'TMC-2', 'IIRS', 'LROC'
    image_type VARCHAR(50) NOT NULL DEFAULT 'orbital', -- 'orbital', 'reference'
    file_name VARCHAR(512) NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,    -- Path inside Supabase Storage bucket
    file_format VARCHAR(50) NOT NULL,       -- 'GeoTIFF', 'TIFF', 'DAT', 'CUB', etc.
    product_id VARCHAR(255) NOT NULL,
    product_level VARCHAR(100),
    file_size_bytes BIGINT NOT NULL,
    sha256 VARCHAR(64) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'UPLOADED', -- 'UPLOADED', 'INGESTED', 'VALIDATED', 'WARNING', 'FAILED', 'ASSIGNED', 'PROCESSING', 'COMPLETED'
    
    -- Multi-user Team Workflow Fields
    assigned_to VARCHAR(100),
    processing_owner VARCHAR(100),
    last_processed_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_images_region_id ON images(region_id);
CREATE INDEX IF NOT EXISTS idx_images_sensor ON images(sensor);
CREATE INDEX IF NOT EXISTS idx_images_image_id ON images(image_id);
CREATE INDEX IF NOT EXISTS idx_images_product_id ON images(product_id);
CREATE INDEX IF NOT EXISTS idx_images_status ON images(status);
CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images(sha256);

-- ------------------------------------------------------------------------------
-- 3. IMAGE_METADATA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    width_px INTEGER,
    height_px INTEGER,
    bit_depth INTEGER,
    band_count INTEGER DEFAULT 1,
    spatial_resolution_m DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    acquisition_date DATE,
    acquisition_time TIME,
    sun_elevation_deg DOUBLE PRECISION,
    sun_azimuth_deg DOUBLE PRECISION,
    incidence_angle_deg DOUBLE PRECISION,
    emission_angle_deg DOUBLE PRECISION,
    phase_angle_deg DOUBLE PRECISION,
    look_angle_deg DOUBLE PRECISION,
    projection VARCHAR(100),
    crs VARCHAR(100),
    footprint TEXT,
    raw_metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_metadata_image_id ON image_metadata(image_id);
CREATE INDEX IF NOT EXISTS idx_image_metadata_acq_date ON image_metadata(acquisition_date);

-- ------------------------------------------------------------------------------
-- 4. IMAGE_QUALITY
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_quality (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    readable BOOLEAN DEFAULT TRUE,
    corrupted BOOLEAN DEFAULT FALSE,
    nodata_percentage DOUBLE PRECISION DEFAULT 0.0,
    valid_pixel_percentage DOUBLE PRECISION DEFAULT 100.0,
    saturation_percentage DOUBLE PRECISION DEFAULT 0.0,
    blank_image BOOLEAN DEFAULT FALSE,
    invalid_pixel_percentage DOUBLE PRECISION DEFAULT 0.0,
    quality_status VARCHAR(50) DEFAULT 'PASS', -- 'PASS', 'WARNING', 'FAIL'
    quality_flags JSONB,
    quality_report_path VARCHAR(1024),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_quality_image_id ON image_quality(image_id);
CREATE INDEX IF NOT EXISTS idx_image_quality_status ON image_quality(quality_status);

-- ------------------------------------------------------------------------------
-- 5. IMAGE_FOOTPRINTS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_footprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    geometry GEOMETRY(Polygon, 4326),
    area DOUBLE PRECISION,
    min_latitude DOUBLE PRECISION,
    max_latitude DOUBLE PRECISION,
    min_longitude DOUBLE PRECISION,
    max_longitude DOUBLE PRECISION,
    footprint_source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_footprints_image_id ON image_footprints(image_id);
CREATE INDEX IF NOT EXISTS idx_image_footprints_geom ON image_footprints USING GIST (geometry);

-- ------------------------------------------------------------------------------
-- 6. IMAGE_PAIRS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference_image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    source_image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    sensor_pair VARCHAR(100) NOT NULL, -- 'OHRC-LROC', 'TMC2-LROC', 'IIRS-LROC'
    region_id UUID NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    geographic_overlap_percentage DOUBLE PRECISION,
    pair_status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_ref_src_pair UNIQUE (reference_image_id, source_image_id)
);

CREATE INDEX IF NOT EXISTS idx_image_pairs_region_id ON image_pairs(region_id);
CREATE INDEX IF NOT EXISTS idx_image_pairs_status ON image_pairs(pair_status);

-- ------------------------------------------------------------------------------
-- 7. EXPERIMENTS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(255) NOT NULL UNIQUE,
    region_id UUID REFERENCES regions(id) ON DELETE SET NULL,
    description TEXT,
    pipeline_version VARCHAR(50) DEFAULT '1.0.0',
    status VARCHAR(50) DEFAULT 'PENDING',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_experiments_region_id ON experiments(region_id);

-- ------------------------------------------------------------------------------
-- 8. PROCESSING_LOGS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID REFERENCES images(id) ON DELETE CASCADE,
    experiment_id UUID REFERENCES experiments(id) ON DELETE SET NULL,
    stage VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_details JSONB
);

CREATE INDEX IF NOT EXISTS idx_processing_logs_image_id ON processing_logs(image_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs(stage, status);

-- ------------------------------------------------------------------------------
-- SEED DATA: Default Regions R01 - R10
-- ------------------------------------------------------------------------------
INSERT INTO regions (region_code, region_name, description, center_latitude, center_longitude)
VALUES
    ('R01', 'South Pole - Shackleton Rim', 'High-priority lunar south pole crater rim with permanent shadow and high illumination', -89.90, 0.00),
    ('R02', 'South Pole - Faustini / Shoemaker', 'Permanently shadowed region with volatile/water ice deposits', -87.10, 84.30),
    ('R03', 'Tycho Crater Central Peak', 'Prominent Copernican-era impact crater with steep slopes and high optical contrast', -43.31, -11.36),
    ('R04', 'Mare Tranquillitatis - Apollo 11 Landing Site', 'Equatorial basaltic lunar mare plain with high titanium regolith', 0.67, 23.47),
    ('R05', 'Oceanus Procellarum - Aristarchus Plateau', 'High-albedo pyroclastic deposits and sinuous rilles', 23.70, -47.40),
    ('R06', 'South Pole-Aitken Basin Interior', 'Deepest and oldest impact basin on the lunar far side', -53.00, 169.00),
    ('R07', 'Mare Imbrium - Archimedes Crater', 'Large impact basin floor with complex wrinkle ridges', 29.70, -4.00),
    ('R08', 'Copernicus Crater Rim and Floor', 'Prominent rayed crater exhibiting terrace walls and impact melt', 9.62, -20.08),
    ('R09', 'Mare Serenitatis - Posidonius Crater', 'Complex crater floor fractured with rilles near mare boundary', 31.80, 29.90),
    ('R10', 'Hertzsprung Basin Far-Side Swath', 'Multi-ringed impact basin on lunar far side with low illumination angles', 1.60, -128.60)
ON CONFLICT (region_code) DO UPDATE
SET
    region_name = EXCLUDED.region_name,
    description = EXCLUDED.description,
    center_latitude = EXCLUDED.center_latitude,
    center_longitude = EXCLUDED.center_longitude;

-- ------------------------------------------------------------------------------
-- SUPABASE ROW LEVEL SECURITY (RLS) POLICIES
-- ------------------------------------------------------------------------------
ALTER TABLE regions ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_quality ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_footprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_pairs ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;

-- Allow public / authenticated read-only access for dataset inspection
CREATE POLICY "Public read-only regions" ON regions FOR SELECT USING (true);
CREATE POLICY "Public read-only images" ON images FOR SELECT USING (true);
CREATE POLICY "Public read-only metadata" ON image_metadata FOR SELECT USING (true);
CREATE POLICY "Public read-only quality" ON image_quality FOR SELECT USING (true);
CREATE POLICY "Public read-only footprints" ON image_footprints FOR SELECT USING (true);
CREATE POLICY "Public read-only pairs" ON image_pairs FOR SELECT USING (true);
CREATE POLICY "Public read-only experiments" ON experiments FOR SELECT USING (true);
CREATE POLICY "Public read-only logs" ON processing_logs FOR SELECT USING (true);

-- Allow full write / modify access to service-role or authenticated users
CREATE POLICY "Service role full access images" ON images FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access metadata" ON image_metadata FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access quality" ON image_quality FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access footprints" ON image_footprints FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access pairs" ON image_pairs FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access experiments" ON experiments FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access logs" ON processing_logs FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

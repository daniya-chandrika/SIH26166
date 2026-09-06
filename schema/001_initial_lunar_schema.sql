-- ==============================================================================
-- SIH26166: Scientific Lunar Image Registration Database Schema
-- Target: PostgreSQL 14+ / Supabase with PostGIS extension
-- ==============================================================================
-- NOTE: Large scientific rasters (GeoTIFF, ENVI, CUB) reside in S3/Supabase Object Storage.
-- Only metadata, quality metrics, geometries, and URIs are stored in PostgreSQL.
-- ==============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ------------------------------------------------------------------------------
-- ENUMS
-- ------------------------------------------------------------------------------
CREATE TYPE sensor_type_enum AS ENUM ('OHRC', 'TMC-2', 'IIRS', 'LROC');
CREATE TYPE product_level_enum AS ENUM ('RAW', 'L0', 'L1', 'L2', 'CALIBRATED', 'MAP_PROJECTED', 'ORTHO', 'DERIVED');
CREATE TYPE quality_status_enum AS ENUM ('PASS', 'WARNING', 'FAIL');
CREATE TYPE file_category_enum AS ENUM ('SCIENTIFIC_IMAGE', 'METADATA', 'BROWSE_IMAGE', 'AUXILIARY');
CREATE TYPE pipeline_stage_enum AS ENUM (
    'INGESTION', 'METADATA', 'QUALITY', 'GEOSPATIAL', 
    'PREPROCESSING', 'FEATURES', 'MATCHING', 'GEOMETRY', 
    'SUBPIXEL', 'REGISTRATION', 'EVALUATION'
);
CREATE TYPE stage_status_enum AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'WARNING', 'FAILED');

-- ------------------------------------------------------------------------------
-- 1. REGIONS (Lunar regions of interest, landing sites, craters)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regions (
    region_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    target_body VARCHAR(50) DEFAULT 'MOON',
    center_latitude DOUBLE PRECISION,
    center_longitude DOUBLE PRECISION,
    boundary_geom GEOMETRY(Polygon, 4326),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_regions_boundary ON regions USING GIST (boundary_geom);

-- ------------------------------------------------------------------------------
-- 2. IMAGES (Core catalog of ingested lunar imagery products)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS images (
    image_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    region_id UUID REFERENCES regions(region_id) ON DELETE SET NULL,
    product_id VARCHAR(255) NOT NULL,
    sensor sensor_type_enum NOT NULL,
    mission VARCHAR(100) NOT NULL,
    original_archive_name VARCHAR(255) NOT NULL,
    archive_sha256 VARCHAR(64) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    storage_uri VARCHAR(1024), -- Object storage bucket URI
    file_format VARCHAR(50) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_category file_category_enum NOT NULL DEFAULT 'SCIENTIFIC_IMAGE',
    is_reference BOOLEAN DEFAULT FALSE, -- e.g., LROC reference product
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_images_sensor_product ON images (sensor, product_id);
CREATE INDEX IF NOT EXISTS idx_images_sha256 ON images (archive_sha256);

-- ------------------------------------------------------------------------------
-- 3. IMAGE_METADATA (Scientific orbital and photometric parameters)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_metadata (
    metadata_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    product_level product_level_enum DEFAULT 'L1',
    width INTEGER,
    height INTEGER,
    bit_depth INTEGER,
    number_of_bands INTEGER DEFAULT 1,
    spatial_resolution_m DOUBLE PRECISION,
    
    -- Temporal
    acquisition_date DATE,
    acquisition_time TIME,
    start_time_utc TIMESTAMPTZ,
    stop_time_utc TIMESTAMPTZ,
    
    -- Coordinates (Center & Bounding Box)
    center_latitude DOUBLE PRECISION,
    center_longitude DOUBLE PRECISION,
    min_latitude DOUBLE PRECISION,
    max_latitude DOUBLE PRECISION,
    min_longitude DOUBLE PRECISION,
    max_longitude DOUBLE PRECISION,
    
    -- Photometric and Solar Geometry Angles (in degrees)
    sun_elevation DOUBLE PRECISION,
    sun_azimuth DOUBLE PRECISION,
    incidence_angle DOUBLE PRECISION,
    emission_angle DOUBLE PRECISION,
    phase_angle DOUBLE PRECISION,
    look_angle DOUBLE PRECISION,
    
    -- Georeferencing
    projection VARCHAR(100),
    crs VARCHAR(100),
    datum VARCHAR(100),
    
    -- Raw Parsed Label/Metadata JSON for full traceability
    raw_metadata_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_metadata_image_id ON image_metadata (image_id);
CREATE INDEX IF NOT EXISTS idx_image_metadata_center_coords ON image_metadata (center_latitude, center_longitude);

-- ------------------------------------------------------------------------------
-- 4. IMAGE_QUALITY (Scientific data quality assurance metrics)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_quality (
    quality_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    quality_status quality_status_enum NOT NULL DEFAULT 'PASS',
    
    -- Metrics
    is_corrupted BOOLEAN DEFAULT FALSE,
    is_readable BOOLEAN DEFAULT TRUE,
    is_blank BOOLEAN DEFAULT FALSE,
    nodata_percentage DOUBLE PRECISION DEFAULT 0.0,
    saturation_percentage DOUBLE PRECISION DEFAULT 0.0,
    mean_dn DOUBLE PRECISION,
    std_dn DOUBLE PRECISION,
    min_dn DOUBLE PRECISION,
    max_dn DOUBLE PRECISION,
    
    -- Missing metadata flags
    missing_spatial_coords BOOLEAN DEFAULT FALSE,
    missing_solar_angles BOOLEAN DEFAULT FALSE,
    missing_resolution BOOLEAN DEFAULT FALSE,
    
    -- Diagnostic notes
    issues JSONB,
    quality_score DOUBLE PRECISION, -- 0.0 to 1.0
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_quality_image_id ON image_quality (image_id);
CREATE INDEX IF NOT EXISTS idx_image_quality_status ON image_quality (quality_status);

-- ------------------------------------------------------------------------------
-- 5. IMAGE_FOOTPRINTS (PostGIS polygons for lunar orbital swath footprints)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_footprints (
    footprint_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    footprint_geom GEOMETRY(Polygon, 4326) NOT NULL,
    footprint_geojson JSONB,
    footprint_wkt TEXT,
    area_km2 DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_footprints_geom ON image_footprints USING GIST (footprint_geom);

-- ------------------------------------------------------------------------------
-- 6. IMAGE_PAIRS (Registration candidate pairs: Source vs Reference)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS image_pairs (
    pair_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_image_id UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    reference_image_id UUID NOT NULL REFERENCES images(image_id) ON DELETE CASCADE,
    overlap_percentage DOUBLE PRECISION,
    intersection_geom GEOMETRY(Polygon, 4326),
    is_valid_pair BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_image_pair UNIQUE (source_image_id, reference_image_id)
);

CREATE INDEX IF NOT EXISTS idx_image_pairs_intersection ON image_pairs USING GIST (intersection_geom);

-- ------------------------------------------------------------------------------
-- 7. EXPERIMENTS (Tracks registration runs, model parameters, ablation tests)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL,
    created_by VARCHAR(100),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ------------------------------------------------------------------------------
-- 8. MATCHES (Keypoint correspondences detected between image pairs)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS matches (
    match_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pair_id UUID NOT NULL REFERENCES image_pairs(pair_id) ON DELETE CASCADE,
    experiment_id UUID REFERENCES experiments(experiment_id) ON DELETE SET NULL,
    detector_name VARCHAR(100), -- e.g., 'SuperPoint', 'LoFTR', 'SIFT'
    matcher_name VARCHAR(100),  -- e.g., 'LightGlue', 'MutualNN'
    total_keypoints_source INTEGER DEFAULT 0,
    total_keypoints_ref INTEGER DEFAULT 0,
    total_raw_matches INTEGER DEFAULT 0,
    filtered_matches INTEGER DEFAULT 0,
    confidence_mean DOUBLE PRECISION,
    keypoints_storage_uri VARCHAR(1024), -- Matrix stored in HDF5/NPZ file in object store
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 9. TRANSFORMATIONS (Estimated geometric transformations)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transformations (
    transformation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    model_type VARCHAR(100) NOT NULL, -- e.g., 'HOMOGRAPHY', 'AFFINE', 'TPS', 'PROJECTIVE'
    matrix DOUBLE PRECISION[][], -- 3x3 or 4x4 matrix
    inliers_count INTEGER,
    inlier_ratio DOUBLE PRECISION,
    estimator_name VARCHAR(100) DEFAULT 'RANSAC', -- 'RANSAC', 'MAGSAC++', etc.
    residual_rmse DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 10. REGISTRATION_RESULTS (Warped raster artifacts and overlap validation)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS registration_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pair_id UUID NOT NULL REFERENCES image_pairs(pair_id) ON DELETE CASCADE,
    transformation_id UUID REFERENCES transformations(transformation_id) ON DELETE SET NULL,
    registered_raster_uri VARCHAR(1024) NOT NULL, -- Path in Object Storage
    difference_raster_uri VARCHAR(1024),
    resampling_method VARCHAR(50) DEFAULT 'BILINEAR',
    subpixel_refined BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 11. EVALUATION_METRICS (Quantitative scientific benchmarks)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluation_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    result_id UUID NOT NULL REFERENCES registration_results(result_id) ON DELETE CASCADE,
    rmse_pixels DOUBLE PRECISION,
    mae_pixels DOUBLE PRECISION,
    ssim DOUBLE PRECISION,
    psnr DOUBLE PRECISION,
    mutual_information DOUBLE PRECISION,
    normalized_cross_correlation DOUBLE PRECISION,
    reprojection_error_m DOUBLE PRECISION,
    evaluation_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 12. PROCESSING_LOGS (Traceable stage audit log)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processing_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stage pipeline_stage_enum NOT NULL,
    status stage_status_enum NOT NULL,
    image_id UUID REFERENCES images(image_id) ON DELETE CASCADE,
    pair_id UUID REFERENCES image_pairs(pair_id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    details JSONB,
    duration_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processing_logs_stage ON processing_logs (stage, status);

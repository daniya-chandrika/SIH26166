-- ==============================================================================
-- SIH26166: Phase 9 - Control Points, Processing Locks & Benchmarks Schema
-- ==============================================================================

-- 1. CONTROL_POINTS (Ground truth, manual check, and algorithmic tie points)
CREATE TABLE IF NOT EXISTS control_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    point_id VARCHAR(100) NOT NULL UNIQUE,
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    source_image_id UUID REFERENCES images(id) ON DELETE SET NULL,
    reference_image_id UUID REFERENCES images(id) ON DELETE SET NULL,
    source_x DOUBLE PRECISION NOT NULL,
    source_y DOUBLE PRECISION NOT NULL,
    reference_x DOUBLE PRECISION NOT NULL,
    reference_y DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    point_type VARCHAR(50) NOT NULL DEFAULT 'ALGORITHMIC_INLIER', -- 'GROUND_TRUTH', 'ALGORITHMIC_INLIER', 'MANUAL_CHECK', 'OTHER'
    verification_status VARCHAR(50) NOT NULL DEFAULT 'UNVERIFIED', -- 'UNVERIFIED', 'VERIFIED', 'REJECTED'
    annotator VARCHAR(100) DEFAULT 'ALGORITHM',
    confidence DOUBLE PRECISION DEFAULT 1.0,
    residual_error_px DOUBLE PRECISION,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_control_points_exp_id ON control_points(experiment_id);
CREATE INDEX IF NOT EXISTS idx_control_points_type ON control_points(point_type);

-- 2. PROCESSING_LOCKS (Concurrency control preventing race conditions)
CREATE TABLE IF NOT EXISTS processing_locks (
    lock_id VARCHAR(255) PRIMARY KEY, -- e.g. 'LOCK_R01_OHRC_LROC'
    resource_id VARCHAR(255) NOT NULL,
    lock_status VARCHAR(50) NOT NULL DEFAULT 'LOCKED', -- 'LOCKED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'
    locked_by VARCHAR(100) NOT NULL,
    locked_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_locks_resource ON processing_locks(resource_id);

-- 3. BENCHMARK_SUITES (Recorded benchmark runs inspired by Lunar-MatchBench)
CREATE TABLE IF NOT EXISTS benchmark_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id VARCHAR(255) NOT NULL UNIQUE,
    suite_name VARCHAR(255) NOT NULL,
    total_cases INTEGER NOT NULL,
    passed_cases INTEGER NOT NULL,
    failed_cases INTEGER NOT NULL,
    success_rate_pct DOUBLE PRECISION NOT NULL,
    mean_rmse_px DOUBLE PRECISION,
    mean_inlier_ratio DOUBLE PRECISION,
    mean_coverage_pct DOUBLE PRECISION,
    mean_ssim DOUBLE PRECISION,
    total_runtime_seconds DOUBLE PRECISION,
    suite_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies
ALTER TABLE control_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_suites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read-only control_points" ON control_points FOR SELECT USING (true);
CREATE POLICY "Public read-only locks" ON processing_locks FOR SELECT USING (true);
CREATE POLICY "Public read-only benchmarks" ON benchmark_suites FOR SELECT USING (true);

CREATE POLICY "Service role full access control_points" ON control_points FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access locks" ON processing_locks FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');
CREATE POLICY "Service role full access benchmarks" ON benchmark_suites FOR ALL USING (auth.role() = 'service_role' OR auth.role() = 'authenticated');

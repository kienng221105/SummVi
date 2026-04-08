CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_user BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    vector_collection_id VARCHAR(255),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embedding_model VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ratings (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL UNIQUE REFERENCES conversations(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_logs (
    id UUID PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    route_name VARCHAR(255),
    method VARCHAR(16) NOT NULL,
    log_level VARCHAR(16) NOT NULL DEFAULT 'INFO',
    status_code INTEGER NOT NULL,
    response_time INTEGER,
    user_id UUID,
    client_ip VARCHAR(64),
    user_agent VARCHAR(512),
    error_type VARCHAR(255),
    error_message TEXT,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_activities (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inference_logs (
    id SERIAL PRIMARY KEY,
    input_length INTEGER NOT NULL,
    summary_length INTEGER NOT NULL,
    input_word_count INTEGER,
    summary_word_count INTEGER,
    length_ratio DOUBLE PRECISION,
    compression_ratio DOUBLE PRECISION NOT NULL,
    latency DOUBLE PRECISION NOT NULL,
    rag_latency DOUBLE PRECISION,
    retrieval_latency DOUBLE PRECISION,
    generation_latency DOUBLE PRECISION,
    chunk_count INTEGER,
    retrieved_chunk_count INTEGER,
    context_char_length INTEGER,
    model_name VARCHAR(255),
    embedding_model_name VARCHAR(255),
    model_device VARCHAR(32),
    generation_backend VARCHAR(64),
    embedding_backend VARCHAR(64),
    used_model_fallback BOOLEAN,
    model_load_error TEXT,
    embedding_load_error TEXT,
    rag_top_k INTEGER,
    chunk_size INTEGER,
    chunk_overlap INTEGER,
    process_id INTEGER,
    cpu_count INTEGER,
    python_version VARCHAR(64),
    platform_name VARCHAR(128),
    cuda_available BOOLEAN,
    gpu_memory_mb DOUBLE PRECISION,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE VIEW bi_inference_metrics_daily AS
SELECT
    DATE(created_at) AS metric_date,
    COUNT(*) AS total_requests,
    ROUND(AVG(input_length)::numeric, 2) AS avg_input_length,
    ROUND(AVG(summary_length)::numeric, 2) AS avg_summary_length,
    ROUND(AVG(input_word_count)::numeric, 2) AS avg_input_word_count,
    ROUND(AVG(summary_word_count)::numeric, 2) AS avg_summary_word_count,
    ROUND(AVG(length_ratio)::numeric, 4) AS avg_length_ratio,
    ROUND(AVG(compression_ratio)::numeric, 4) AS avg_compression_ratio,
    ROUND(AVG(latency)::numeric, 4) AS avg_latency,
    ROUND(AVG(rag_latency)::numeric, 4) AS avg_rag_latency,
    ROUND(AVG(retrieval_latency)::numeric, 4) AS avg_retrieval_latency,
    ROUND(AVG(generation_latency)::numeric, 4) AS avg_generation_latency,
    ROUND(AVG(chunk_count)::numeric, 2) AS avg_chunk_count,
    ROUND(AVG(retrieved_chunk_count)::numeric, 2) AS avg_retrieved_chunk_count,
    SUM(CASE WHEN used_model_fallback IS TRUE THEN 1 ELSE 0 END) AS fallback_requests
FROM inference_logs
GROUP BY DATE(created_at)
ORDER BY metric_date DESC;

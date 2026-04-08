SELECT * FROM inference_logs ORDER BY created_at DESC;

SELECT * FROM bi_inference_metrics_daily ORDER BY metric_date DESC;

SELECT
    model_name,
    embedding_model_name,
    model_device,
    generation_backend,
    embedding_backend,
    used_model_fallback,
    AVG(latency) AS avg_total_latency,
    AVG(rag_latency) AS avg_rag_latency,
    AVG(retrieval_latency) AS avg_retrieval_latency,
    AVG(generation_latency) AS avg_generation_latency,
    AVG(chunk_count) AS avg_chunk_count,
    AVG(retrieved_chunk_count) AS avg_retrieved_chunk_count,
    COUNT(*) AS total_requests
FROM inference_logs
GROUP BY
    model_name,
    embedding_model_name,
    model_device,
    generation_backend,
    embedding_backend,
    used_model_fallback
ORDER BY total_requests DESC, avg_total_latency DESC;

SELECT
    created_at,
    model_name,
    model_device,
    generation_backend,
    embedding_backend,
    used_model_fallback,
    model_load_error,
    embedding_load_error,
    latency,
    rag_latency,
    retrieval_latency,
    generation_latency,
    chunk_count,
    retrieved_chunk_count,
    context_char_length,
    gpu_memory_mb
FROM inference_logs
ORDER BY created_at DESC;

SELECT * FROM system_logs ORDER BY created_at DESC;

SELECT action, COUNT(*) AS total_actions
FROM user_activities
GROUP BY action
ORDER BY total_actions DESC;

SELECT
    endpoint,
    log_level,
    status_code,
    COUNT(*) AS total_requests,
    ROUND(AVG(response_time)::numeric, 2) AS avg_response_time
FROM system_logs
GROUP BY endpoint, log_level, status_code
ORDER BY total_requests DESC, avg_response_time DESC;

SELECT
    request_id,
    endpoint,
    route_name,
    method,
    log_level,
    status_code,
    response_time,
    error_type,
    error_message,
    created_at
FROM system_logs
WHERE log_level <> 'INFO'
ORDER BY created_at DESC;

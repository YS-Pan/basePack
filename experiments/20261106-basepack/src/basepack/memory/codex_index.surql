DEFINE TABLE IF NOT EXISTS codex_thread SCHEMALESS;
DEFINE TABLE IF NOT EXISTS codex_part SCHEMALESS;
DEFINE TABLE IF NOT EXISTS codex_chunk SCHEMALESS;
DEFINE FIELD IF NOT EXISTS embedding ON codex_chunk TYPE array<float>;
DEFINE INDEX IF NOT EXISTS codex_part_thread ON codex_part FIELDS thread_id;
DEFINE INDEX IF NOT EXISTS codex_chunk_thread ON codex_chunk FIELDS thread_id;

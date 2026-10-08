CREATE TABLE IF NOT EXISTS learning_artifacts (
  id TEXT PRIMARY KEY,
  artifact_type TEXT NOT NULL,
  authority TEXT NOT NULL,
  source_repo TEXT NOT NULL,
  source_revision TEXT,
  correlation_id TEXT NOT NULL,
  artifact_sha256 TEXT NOT NULL,
  artifact_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS learning_artifacts_type_idx
  ON learning_artifacts(artifact_type, created_at DESC);
CREATE INDEX IF NOT EXISTS learning_artifacts_source_idx
  ON learning_artifacts(source_repo, created_at DESC);

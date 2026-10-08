ALTER TABLE worker_jobs ADD COLUMN started_at TEXT;
ALTER TABLE worker_jobs ADD COLUMN heartbeat_at TEXT;
ALTER TABLE worker_jobs ADD COLUMN finished_at TEXT;
ALTER TABLE worker_jobs ADD COLUMN deadline_at TEXT;
ALTER TABLE worker_jobs ADD COLUMN estimated_duration_ms INTEGER;
ALTER TABLE worker_jobs ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0;
ALTER TABLE worker_jobs ADD COLUMN last_error TEXT;
CREATE INDEX worker_jobs_heartbeat_idx ON worker_jobs(state, heartbeat_at);

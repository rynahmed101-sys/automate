CREATE TABLE worker_jobs (
  id TEXT PRIMARY KEY NOT NULL,
  request_id TEXT NOT NULL UNIQUE,
  capability_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('queued', 'running', 'awaiting_result', 'succeeded', 'failed', 'cancelled')),
  packet_json TEXT NOT NULL,
  result_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX worker_jobs_capability_idx ON worker_jobs(capability_id);
CREATE INDEX worker_jobs_state_idx ON worker_jobs(state);

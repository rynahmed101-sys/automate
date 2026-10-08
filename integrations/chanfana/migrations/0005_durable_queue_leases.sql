ALTER TABLE worker_jobs ADD COLUMN lease_id TEXT;
ALTER TABLE worker_jobs ADD COLUMN lease_expires_at TEXT;
ALTER TABLE worker_jobs ADD COLUMN dispatch_state TEXT NOT NULL DEFAULT 'pending' CHECK (dispatch_state IN ('pending', 'sent'));
CREATE INDEX worker_jobs_lease_idx ON worker_jobs(state, lease_expires_at);
CREATE INDEX worker_jobs_dispatch_idx ON worker_jobs(dispatch_state, updated_at);

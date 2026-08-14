-- Device Authorization Grant 支持
CREATE TABLE device_codes (
  device_code TEXT PRIMARY KEY,
  user_code   TEXT NOT NULL UNIQUE,
  client_id   TEXT NOT NULL REFERENCES clients(id),
  user_id     INTEGER,
  status      TEXT NOT NULL DEFAULT 'pending', -- pending | approved | denied | expired
  approved_at TIMESTAMPTZ,
  expires_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_device_codes_user ON device_codes(user_id, status);

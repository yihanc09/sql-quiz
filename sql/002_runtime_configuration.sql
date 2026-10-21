-- Stores deployment settings behind an administrator-only schema.
-- No credentials or setting values belong in this migration file.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE SCHEMA IF NOT EXISTS quiz_private;
REVOKE ALL ON SCHEMA quiz_private FROM PUBLIC, anon, authenticated, quiz_reader;

CREATE TABLE IF NOT EXISTS quiz_private.runtime_config (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    settings jsonb NOT NULL CHECK (jsonb_typeof(settings) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE quiz_private.runtime_config ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE quiz_private.runtime_config FROM PUBLIC, anon, authenticated, quiz_reader;

COMMIT;

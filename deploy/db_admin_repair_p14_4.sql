-- P14.4 controlled PostgreSQL admin repair.
-- Run with a PostgreSQL admin account. This script is idempotent and does not
-- drop databases, drop tables, or delete business data.

\set ON_ERROR_STOP on

BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'screenshot_app') THEN
    RAISE EXCEPTION 'Required role screenshot_app does not exist';
  END IF;
END $$;

ALTER TABLE IF EXISTS public.runs
  ADD COLUMN IF NOT EXISTS worker_id TEXT;

ALTER TABLE IF EXISTS public.apps
  ADD COLUMN IF NOT EXISTS created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS public.schema_migrations (
  version TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.schema_migrations (version, description)
VALUES ('p14_4_admin_repair', 'P14.4 worker/app schema ownership and grants repair')
ON CONFLICT (version) DO UPDATE
SET description = EXCLUDED.description;

DO $$
DECLARE
  item RECORD;
BEGIN
  FOR item IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I OWNER TO screenshot_app', item.tablename);
  END LOOP;

  FOR item IN
    SELECT sequencename
    FROM pg_sequences
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER SEQUENCE public.%I OWNER TO screenshot_app', item.sequencename);
  END LOOP;
END $$;

GRANT USAGE ON SCHEMA public TO screenshot_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO screenshot_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO screenshot_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO screenshot_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO screenshot_app;

COMMIT;

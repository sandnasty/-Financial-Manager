BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.events (
    sequence_number bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id uuid NOT NULL UNIQUE,
    occurred_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    actor_id text NOT NULL,
    actor_type text NOT NULL CHECK (actor_type IN ('human', 'service', 'agent')),
    action text NOT NULL,
    target_type text NOT NULL,
    target_id text NOT NULL,
    correlation_id text NOT NULL,
    trace_id text NOT NULL,
    result text NOT NULL,
    source_service text NOT NULL,
    source_version text NOT NULL,
    environment text NOT NULL,
    immutable_refs jsonb NOT NULL DEFAULT '{}'::jsonb,
    event_payload jsonb NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    prior_record_sha256 text,
    record_sha256 text NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_events_correlation
    ON audit.events (correlation_id, sequence_number);
CREATE INDEX IF NOT EXISTS audit_events_recorded_at
    ON audit.events (recorded_at);

CREATE OR REPLACE FUNCTION audit.deny_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit records are immutable';
END;
$$;

DROP TRIGGER IF EXISTS audit_events_immutable ON audit.events;
CREATE TRIGGER audit_events_immutable
BEFORE UPDATE OR DELETE ON audit.events
FOR EACH ROW EXECUTE FUNCTION audit.deny_mutation();

CREATE OR REPLACE FUNCTION audit.append_event(payload jsonb, payload_hash text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = audit, pg_temp
AS $$
DECLARE
    previous_hash text;
    inserted_id uuid;
BEGIN
    IF payload_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'invalid payload hash';
    END IF;
    PERFORM pg_advisory_xact_lock(65166);
    SELECT record_sha256 INTO previous_hash
      FROM audit.events ORDER BY sequence_number DESC LIMIT 1;
    INSERT INTO audit.events (
        event_id, occurred_at, actor_id, actor_type, action,
        target_type, target_id, correlation_id, trace_id, result,
        source_service, source_version, environment, immutable_refs,
        event_payload, payload_sha256, prior_record_sha256, record_sha256
    ) VALUES (
        (payload->>'event_id')::uuid, (payload->>'occurred_at')::timestamptz,
        payload->>'actor_id', payload->>'actor_type', payload->>'action',
        payload->>'target_type', payload->>'target_id',
        payload->>'correlation_id', payload->>'trace_id', payload->>'result',
        payload->>'source_service', payload->>'source_version',
        payload->>'environment', coalesce(payload->'immutable_refs', '{}'::jsonb),
        payload, payload_hash, previous_hash,
        encode(digest(coalesce(previous_hash, '') || payload_hash ||
            (payload->>'event_id'), 'sha256'), 'hex')
    ) RETURNING event_id INTO inserted_id;
    RETURN inserted_id;
END;
$$;

REVOKE ALL ON audit.events FROM PUBLIC;
REVOKE ALL ON FUNCTION audit.append_event(jsonb, text) FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'fm_app') THEN
        GRANT USAGE ON SCHEMA audit TO fm_app;
        GRANT SELECT ON audit.events TO fm_app;
        GRANT EXECUTE ON FUNCTION audit.append_event(jsonb, text) TO fm_app;
        REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON audit.events FROM fm_app;
    END IF;
END;
$$;

COMMIT;

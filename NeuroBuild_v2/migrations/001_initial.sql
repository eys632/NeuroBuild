-- Executed transactionally with a validated, quoted schema search_path.
CREATE TABLE projects (
    project_id uuid PRIMARY KEY,
    name text NOT NULL CHECK (btrim(name) <> ''),
    head_revision_id uuid
);

CREATE TABLE artifacts (
    artifact_id uuid PRIMARY KEY,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes bigint NOT NULL CHECK (size_bytes > 0),
    storage_key text NOT NULL UNIQUE CHECK (storage_key <> '')
);

CREATE TABLE execution_intents (
    execution_id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(project_id),
    base_revision_id uuid,
    proposal_id uuid UNIQUE,
    payload_fingerprint text NOT NULL CHECK (payload_fingerprint ~ '^[0-9a-f]{64}$'),
    artifact_id uuid NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'PREPARED' CHECK (status IN ('PREPARED', 'COMMITTED')),
    result_revision_id uuid UNIQUE,
    CHECK ((base_revision_id IS NULL) = (proposal_id IS NULL)),
    CHECK ((status = 'PREPARED' AND result_revision_id IS NULL)
        OR (status = 'COMMITTED' AND result_revision_id IS NOT NULL))
);

CREATE TABLE revisions (
    revision_id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(project_id),
    number integer NOT NULL CHECK (number >= 0),
    parent_revision_id uuid,
    artifact_id uuid NOT NULL UNIQUE REFERENCES artifacts(artifact_id),
    execution_id uuid NOT NULL UNIQUE REFERENCES execution_intents(execution_id),
    ifc_schema text NOT NULL DEFAULT 'IFC4' CHECK (ifc_schema = 'IFC4'),
    UNIQUE (project_id, revision_id),
    UNIQUE (project_id, number),
    CHECK ((number = 0) = (parent_revision_id IS NULL)),
    CHECK (parent_revision_id IS DISTINCT FROM revision_id),
    FOREIGN KEY (project_id, parent_revision_id)
        REFERENCES revisions(project_id, revision_id)
);

ALTER TABLE projects ADD CONSTRAINT project_head_same_project
    FOREIGN KEY (project_id, head_revision_id)
    REFERENCES revisions(project_id, revision_id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE execution_intents ADD CONSTRAINT execution_base_same_project
    FOREIGN KEY (project_id, base_revision_id)
    REFERENCES revisions(project_id, revision_id);
ALTER TABLE execution_intents ADD CONSTRAINT execution_result_same_project
    FOREIGN KEY (project_id, result_revision_id)
    REFERENCES revisions(project_id, revision_id) DEFERRABLE INITIALLY DEFERRED;

CREATE FUNCTION reject_immutable_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'immutable % cannot be updated or deleted', TG_TABLE_NAME
        USING ERRCODE = '23514';
END;
$$;

CREATE TRIGGER immutable_artifacts BEFORE UPDATE OR DELETE ON artifacts
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER immutable_revisions BEFORE UPDATE OR DELETE ON revisions
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();

CREATE FUNCTION validate_revision_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    parent_number integer;
    intent execution_intents%ROWTYPE;
BEGIN
    IF NEW.parent_revision_id IS NOT NULL THEN
        SELECT number INTO parent_number FROM revisions
            WHERE revision_id = NEW.parent_revision_id AND project_id = NEW.project_id;
        IF parent_number IS NULL OR NEW.number <> parent_number + 1 THEN
            RAISE EXCEPTION 'revision parent/number mismatch' USING ERRCODE = '23514';
        END IF;
    END IF;
    SELECT * INTO intent FROM execution_intents WHERE execution_id = NEW.execution_id;
    IF intent.execution_id IS NULL OR intent.status <> 'PREPARED'
        OR intent.project_id <> NEW.project_id
        OR intent.base_revision_id IS DISTINCT FROM NEW.parent_revision_id
        OR intent.artifact_id <> NEW.artifact_id THEN
        RAISE EXCEPTION 'revision does not match prepared execution' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER revision_lineage BEFORE INSERT ON revisions
    FOR EACH ROW EXECUTE FUNCTION validate_revision_insert();

CREATE FUNCTION validate_intent_change() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    result revisions%ROWTYPE;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'execution intent cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF OLD.status <> 'PREPARED' OR NEW.status <> 'COMMITTED'
        OR ROW(NEW.execution_id, NEW.project_id, NEW.base_revision_id, NEW.proposal_id,
               NEW.payload_fingerprint, NEW.artifact_id)
            IS DISTINCT FROM
           ROW(OLD.execution_id, OLD.project_id, OLD.base_revision_id, OLD.proposal_id,
               OLD.payload_fingerprint, OLD.artifact_id) THEN
        RAISE EXCEPTION 'execution binding is immutable' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO result FROM revisions WHERE revision_id = NEW.result_revision_id;
    IF result.revision_id IS NULL OR result.execution_id <> NEW.execution_id THEN
        RAISE EXCEPTION 'execution result mismatch' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER execution_transition BEFORE UPDATE OR DELETE ON execution_intents
    FOR EACH ROW EXECUTE FUNCTION validate_intent_change();

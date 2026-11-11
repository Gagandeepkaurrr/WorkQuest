"""Protect authoritative immutable history while allowing privacy cascades."""

from alembic import op

revision = "694a01b27d0f"
down_revision = "38e51082aa0b"
branch_labels = None
depends_on = None

GUARDS = {
    "scenario_versions": "OLD.status = 'published' AND (to_jsonb(NEW) - 'created_by') IS DISTINCT FROM (to_jsonb(OLD) - 'created_by')",
    "checkpoints": "to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD)",
    "branch_events": "(to_jsonb(NEW) - 'actor_id') IS DISTINCT FROM (to_jsonb(OLD) - 'actor_id')",
    "scorecards": "(to_jsonb(NEW) - ARRAY['coaching_status','coaching_text']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['coaching_status','coaching_text'])",
    "runs": "(NEW.owner_id, NEW.scenario_version_id, NEW.is_admin_preview, NEW.is_demo, NEW.preview_definition_private_json, NEW.preview_definition_hash) IS DISTINCT FROM (OLD.owner_id, OLD.scenario_version_id, OLD.is_admin_preview, OLD.is_demo, OLD.preview_definition_private_json, OLD.preview_definition_hash)",
    "branches": "(NEW.run_id, NEW.base_snapshot_private_json, NEW.practice_mode, NEW.source_event_seq) IS DISTINCT FROM (OLD.run_id, OLD.base_snapshot_private_json, OLD.practice_mode, OLD.source_event_seq) OR (OLD.status='finalized' AND (NEW.status,NEW.current_state_private_json,NEW.current_state_hash,NEW.state_revision) IS DISTINCT FROM (OLD.status,OLD.current_state_private_json,OLD.current_state_hash,OLD.state_revision))",
    "report_shares": "(to_jsonb(NEW) - ARRAY['revoked_at','expires_at']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['revoked_at','expires_at']) OR NEW.expires_at > OLD.expires_at",
}


def upgrade():
    for table, condition in GUARDS.items():
        op.execute(
            f"CREATE FUNCTION wq_guard_{table}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {condition} THEN RAISE EXCEPTION 'Immutable WorkQuest record' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"
        )
        op.execute(
            f"CREATE TRIGGER wq_immutable_{table} BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION wq_guard_{table}()"
        )


def downgrade():
    for table in reversed(GUARDS):
        op.execute(f"DROP TRIGGER wq_immutable_{table} ON {table}")
        op.execute(f"DROP FUNCTION wq_guard_{table}()")

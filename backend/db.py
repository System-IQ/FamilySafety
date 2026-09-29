"""SQLite storage for development. Production target: PostgreSQL.

Schema is additive. Never drops existing tables or data.
"""
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings

_SCHEMA = """
-- PHASE 2: Devices
CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_updated_at
    ON devices(updated_at DESC);

-- A1: Authentication
CREATE TABLE IF NOT EXISTS users (
    user_id        TEXT PRIMARY KEY,
    email          TEXT UNIQUE NOT NULL,
    display_name   TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    is_active      INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_id    TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    token_hash  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
    ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_revoked
    ON refresh_tokens(revoked);

-- A2: Events
CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    device_id       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    payload_json    TEXT NOT NULL DEFAULT '{}',
    correlation_id  TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_device_ts
    ON events(device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_ts
    ON events(event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_correlation
    ON events(correlation_id);

-- A2: Audit
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id        TEXT PRIMARY KEY,
    actor_user_id   TEXT,
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT,
    result          TEXT NOT NULL,
    reason          TEXT,
    ip_address      TEXT,
    user_agent      TEXT,
    timestamp       TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (actor_user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_audit_actor_ts
    ON audit_events(actor_user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action_ts
    ON audit_events(action, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_resource
    ON audit_events(resource_type, resource_id);

-- A3: Safe Zones
CREATE TABLE IF NOT EXISTS safe_zones (
    zone_id         TEXT PRIMARY KEY,
    device_id       TEXT NOT NULL,
    name            TEXT NOT NULL,
    center_lat      REAL NOT NULL,
    center_lon      REAL NOT NULL,
    radius_meters   REAL NOT NULL,
    enabled         INTEGER NOT NULL DEFAULT 1,
    schedule_json   TEXT,
    created_by      TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_safe_zones_device
    ON safe_zones(device_id);
CREATE INDEX IF NOT EXISTS idx_safe_zones_enabled
    ON safe_zones(enabled);

CREATE TABLE IF NOT EXISTS zone_states (
    zone_id             TEXT PRIMARY KEY,
    device_id           TEXT NOT NULL,
    was_inside          INTEGER NOT NULL DEFAULT 0,
    last_evaluated_at   TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (zone_id) REFERENCES safe_zones(zone_id)
);
CREATE INDEX IF NOT EXISTS idx_zone_states_device
    ON zone_states(device_id);
"""


def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

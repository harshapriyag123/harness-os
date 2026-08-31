from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_PATH = Path(os.getenv("FIXTURE_DB", Path(__file__).resolve().parents[1] / "customer_fixture.db"))
SCHEMA = """
CREATE TABLE IF NOT EXISTS refunds(
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    idempotency_key TEXT,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_refund_key
ON refunds(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE TABLE IF NOT EXISTS trace(
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    refund_id TEXT,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        db.executescript(SCHEMA)
        yield db
        db.commit()
    finally:
        db.close()


def record(event: str, *, refund_id: str | None = None, detail: str = "") -> None:
    with connection() as db:
        db.execute(
            "INSERT INTO trace(event,refund_id,detail,created_at) VALUES(?,?,?,?)",
            (event, refund_id, detail, now()),
        )


def reset() -> None:
    with connection() as db:
        db.execute("DELETE FROM refunds")
        db.execute("DELETE FROM trace")
        db.execute("DELETE FROM sqlite_sequence WHERE name='trace'")


def create_refund(order_id: str, amount_cents: int, idempotency_key: str | None = None):
    with connection() as db:
        if idempotency_key:
            existing = db.execute(
                "SELECT * FROM refunds WHERE idempotency_key=?", (idempotency_key,)
            ).fetchone()
            if existing:
                existing_dict = dict(existing)
                db.execute(
                    "INSERT INTO trace(event,refund_id,detail,created_at) VALUES(?,?,?,?)",
                    (
                        "refund.idempotent_replay",
                        existing_dict["id"],
                        f"{order_id}:{amount_cents}:{idempotency_key}",
                        now(),
                    ),
                )
                return existing_dict
        rid = f"rf_{uuid.uuid4().hex[:10]}"
        created = now()
        db.execute(
            "INSERT INTO refunds VALUES(?,?,?,?,?)",
            (rid, order_id, amount_cents, idempotency_key, created),
        )
        db.execute(
            "INSERT INTO trace(event,refund_id,detail,created_at) VALUES(?,?,?,?)",
            ("refund.created", rid, f"{order_id}:{amount_cents}", created),
        )
        return {
            "id": rid,
            "order_id": order_id,
            "amount_cents": amount_cents,
            "idempotency_key": idempotency_key,
            "created_at": created,
        }


def list_refunds() -> list[dict]:
    with connection() as db:
        return [dict(x) for x in db.execute("SELECT * FROM refunds ORDER BY created_at, id")]


def traces() -> list[dict]:
    with connection() as db:
        return [dict(x) for x in db.execute("SELECT * FROM trace ORDER BY sequence")]


def summary() -> dict:
    refunds = list_refunds()
    return {
        "refund_count": len(refunds),
        "total_refunded_cents": sum(int(x["amount_cents"]) for x in refunds),
        "refunds": refunds,
    }


class RefundRequest(BaseModel):
    order_id: str = Field(min_length=1)
    amount_cents: int = Field(gt=0)
    idempotency_key: str | None = None


app = FastAPI(title="Harness OS Customer Fixture")


@app.get("/health")
def health():
    return {"status": "ok", "fixture": "customer-support-agent", "db": str(DB_PATH)}


@app.post("/refunds", status_code=201)
def post_refund(body: RefundRequest):
    return create_refund(body.order_id, body.amount_cents, body.idempotency_key)


@app.get("/refunds")
def get_refunds():
    record("refund.list_read", detail="list refunds")
    return summary()


@app.get("/refunds/by-idempotency/{idempotency_key}")
def get_by_idempotency_key(idempotency_key: str):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM refunds WHERE idempotency_key=?", (idempotency_key,)
        ).fetchone()
    record("refund.state_verified", refund_id=row["id"] if row else None, detail=idempotency_key)
    return dict(row) if row else None


@app.get("/refunds/{refund_id}")
def get_refund(refund_id: str):
    item = next((x for x in list_refunds() if x["id"] == refund_id), None)
    record("refund.state_verified", refund_id=refund_id, detail="lookup by refund id")
    if not item:
        raise HTTPException(status_code=404, detail="refund not found")
    return item


@app.get("/trace")
def get_trace():
    return {"events": traces()}


@app.get("/evidence")
def get_evidence():
    return {**summary(), "trace": traces()}


@app.post("/reset")
def post_reset():
    reset()
    return {"reset": True, **summary()}

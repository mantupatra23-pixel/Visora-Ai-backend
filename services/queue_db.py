# services/queue_db.py
from sqlalchemy import Table, Column, String, Integer, Float, JSON, Boolean, DateTime
from sqlalchemy import select, insert, update, and_, func, text
from sqlalchemy.exc import DBAPIError
from services.db import engine, SessionLocal, metadata
import datetime, uuid, time

tasks = Table("farm_tasks", metadata,
    Column("task_id", String, primary_key=True),
    Column("job_id", String, index=True),
    Column("frame", Integer),
    Column("status", String, index=True),
    Column("attempts", Integer, default=0),
    Column("priority", Integer, default=5),
    Column("payload", JSON),
    Column("created_at", DateTime, default=func.now()),
    Column("locked_until", DateTime, nullable=True),
)

def init_db():
    metadata.create_all(bind=engine)

def enqueue_task(job_id, frame, payload, priority=5):
    tid = "task_"+uuid.uuid4().hex[:10]
    with SessionLocal() as s:
        s.execute(insert(tasks).values(task_id=tid, job_id=job_id, frame=frame, status="queued", attempts=0, priority=priority, payload=payload))
        s.commit()
    return tid

def claim_next_task(lock_secs=120):
    now = datetime.datetime.utcnow()
    locked_until = now + datetime.timedelta(seconds=lock_secs)
    with SessionLocal() as s:
        # atomic claim: select for update SKIP LOCKED pattern (Postgres)
        q = text("""
            UPDATE farm_tasks SET status='running', locked_until = :lu, attempts = attempts + 1
            WHERE task_id = (
              SELECT task_id FROM farm_tasks
              WHERE status='queued' AND (locked_until IS NULL OR locked_until < :now)
              ORDER BY priority DESC, attempts ASC, created_at ASC
              LIMIT 1
              FOR UPDATE SKIP LOCKED
            )
            RETURNING *
        """)
        res = s.execute(q, {"lu": locked_until, "now": now})
        row = res.fetchone()
        s.commit()
        return dict(row) if row else None

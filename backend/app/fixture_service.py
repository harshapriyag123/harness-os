from __future__ import annotations
import os,sqlite3,uuid
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel,Field

DB_PATH=Path(os.getenv('FIXTURE_DB',Path(__file__).resolve().parents[1]/'customer_fixture.db'))
SCHEMA='''CREATE TABLE IF NOT EXISTS refunds(id TEXT PRIMARY KEY,order_id TEXT NOT NULL,amount_cents INTEGER NOT NULL,idempotency_key TEXT,created_at TEXT NOT NULL); CREATE UNIQUE INDEX IF NOT EXISTS idx_refund_key ON refunds(idempotency_key) WHERE idempotency_key IS NOT NULL; CREATE TABLE IF NOT EXISTS trace(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,refund_id TEXT,detail TEXT NOT NULL,created_at TEXT NOT NULL);'''
def now():return datetime.now(timezone.utc).isoformat()
@contextmanager
def connection():
 db=sqlite3.connect(DB_PATH);db.row_factory=sqlite3.Row
 try:db.executescript(SCHEMA);yield db;db.commit()
 finally:db.close()
def reset():
 with connection() as db:db.execute('DELETE FROM refunds');db.execute('DELETE FROM trace')
def create_refund(order_id:str,amount_cents:int,idempotency_key:str|None=None):
 with connection() as db:
  if idempotency_key:
   existing=db.execute('SELECT * FROM refunds WHERE idempotency_key=?',(idempotency_key,)).fetchone()
   if existing:return dict(existing)
  rid=f'rf_{uuid.uuid4().hex[:10]}';created=now();db.execute('INSERT INTO refunds VALUES(?,?,?,?,?)',(rid,order_id,amount_cents,idempotency_key,created));db.execute('INSERT INTO trace(event,refund_id,detail,created_at) VALUES(?,?,?,?)',('refund.created',rid,f'{order_id}:{amount_cents}',created));return {'id':rid,'order_id':order_id,'amount_cents':amount_cents,'idempotency_key':idempotency_key,'created_at':created}
def list_refunds():
 with connection() as db:return [dict(x) for x in db.execute('SELECT * FROM refunds ORDER BY created_at')]
def traces():
 with connection() as db:return [dict(x) for x in db.execute('SELECT * FROM trace ORDER BY sequence')]
def timeout_after_success(order_id:str,amount_cents:int):
 refund=create_refund(order_id,amount_cents);raise TimeoutError(f'response suppressed after remote success:{refund["id"]}')
class RefundRequest(BaseModel):order_id:str=Field(min_length=1);amount_cents:int=Field(gt=0);idempotency_key:str|None=None
app=FastAPI(title='Harness OS Customer Fixture')
@app.get('/health')
def health():return {'status':'ok','fixture':'customer-support-agent'}
@app.post('/refunds',status_code=201)
def post_refund(body:RefundRequest):return create_refund(body.order_id,body.amount_cents,body.idempotency_key)
@app.get('/refunds')
def get_refunds():return {'refund_count':len(list_refunds()),'refunds':list_refunds()}
@app.get('/refunds/{refund_id}')
def get_refund(refund_id:str):return next((x for x in list_refunds() if x['id']==refund_id),None)
@app.get('/trace')
def get_trace():return traces()
@app.post('/reset')
def post_reset():reset();return {'reset':True}

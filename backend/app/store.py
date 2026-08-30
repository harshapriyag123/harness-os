from __future__ import annotations
import json, os, sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DB_PATH=Path(os.getenv('HARNESS_OS_DB',Path(__file__).resolve().parents[1]/'harness_os.db'))
SCHEMA='''CREATE TABLE IF NOT EXISTS records(kind TEXT NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(kind,id)); CREATE INDEX IF NOT EXISTS idx_records_kind ON records(kind); CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,campaign_id TEXT NOT NULL,data TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP); CREATE INDEX IF NOT EXISTS idx_events_campaign ON events(campaign_id,sequence);'''

@contextmanager
def connection()->Iterator[sqlite3.Connection]:
 db=sqlite3.connect(DB_PATH,timeout=10,check_same_thread=False);db.row_factory=sqlite3.Row
 try: db.executescript(SCHEMA);yield db;db.commit()
 finally: db.close()

def put(kind:str,record:dict[str,Any])->dict[str,Any]:
 with connection() as db: db.execute('INSERT INTO records(kind,id,data) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP',(kind,record['id'],json.dumps(record,separators=(',',':'))))
 return record
def get(kind:str,record_id:str)->dict[str,Any]|None:
 with connection() as db: row=db.execute('SELECT data FROM records WHERE kind=? AND id=?',(kind,record_id)).fetchone()
 return json.loads(row['data']) if row else None
def list_records(kind:str)->list[dict[str,Any]]:
 with connection() as db: rows=db.execute('SELECT data FROM records WHERE kind=? ORDER BY updated_at DESC',(kind,)).fetchall()
 return [json.loads(r['data']) for r in rows]
def delete(kind:str,record_id:str)->bool:
 with connection() as db: cursor=db.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,record_id))
 return cursor.rowcount>0
def append_event(campaign_id:str,event:dict[str,Any])->dict[str,Any]:
 with connection() as db:
  cursor=db.execute('INSERT INTO events(campaign_id,data) VALUES(?,?)',(campaign_id,json.dumps(event)));event['sequence']=cursor.lastrowid;db.execute('UPDATE events SET data=? WHERE sequence=?',(json.dumps(event),cursor.lastrowid))
 return event
def events(campaign_id:str,after:int=0)->list[dict[str,Any]]:
 with connection() as db: rows=db.execute('SELECT data FROM events WHERE campaign_id=? AND sequence>? ORDER BY sequence',(campaign_id,after)).fetchall()
 return [json.loads(r['data']) for r in rows]

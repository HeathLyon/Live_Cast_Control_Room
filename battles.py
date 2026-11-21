"""Audited, single-active head-to-head battle engine. UTC event-time scoring.

Battle totals are derived from the donation ledger, not a separate mutable counter.
Pausing the battle pauses both its timer and its eligible scoring window.
A finalized result is a frozen snapshot; corrections require reopening to revise it.
"""
from __future__ import annotations
import json
import re
import sqlite3
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import store


def utcnow():
    return datetime.now(timezone.utc)

def iso():
    return utcnow().isoformat(timespec='microseconds')

def initialize():
    with store.LOCK,store.connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS battles (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, cast_a TEXT NOT NULL, cast_b TEXT NOT NULL,
          duration_seconds INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
          created_at TEXT NOT NULL, created_by TEXT NOT NULL,
          started_at TEXT, ended_at TEXT, finalized_at TEXT,
          final_json TEXT, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS battle_segments (
          id INTEGER PRIMARY KEY AUTOINCREMENT, battle_id TEXT NOT NULL,
          started_at TEXT NOT NULL, ended_at TEXT,
          FOREIGN KEY(battle_id) REFERENCES battles(id)
        );
        CREATE INDEX IF NOT EXISTS idx_battle_segments ON battle_segments(battle_id,started_at);
        ''')

def _stamp(value):
    return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc)

def _seconds(db,battle_id):
    total=0.0
    for x in db.execute('SELECT started_at,ended_at FROM battle_segments WHERE battle_id=?',(battle_id,)):
        end=_stamp(x['ended_at']) if x['ended_at'] else utcnow()
        total+=max(0,(end-_stamp(x['started_at'])).total_seconds())
    return total

def _score(db,row):
    output={row['cast_a']:0,row['cast_b']:0}
    # Each segment represents a real scoring window; no elapsed time during a pause.
    sql='''SELECT d.cast_id,COALESCE(SUM(d.points_milli),0) AS points
           FROM donations d WHERE d.status='assigned' AND d.currency='USD'
             AND d.cast_id IN (?,?) AND EXISTS (
                 SELECT 1 FROM battle_segments s WHERE s.battle_id=?
                   AND d.published_at>=s.started_at
                   AND d.published_at<=COALESCE(s.ended_at,?)
             )'''
    if store.LIVE_MODE:sql+=" AND d.source IN ('youtube','manual')"
    sql+=' GROUP BY d.cast_id'
    for item in db.execute(sql,(row['cast_a'],row['cast_b'],row['id'],iso())):
        output[item['cast_id']]=int(item['points'])
    return output

def _view(db,row):
    scores=_score(db,row)
    snapshots=json.loads(row['final_json']) if row['status']=='final' and row['final_json'] else None
    values=snapshots or scores
    a,b=row['cast_a'],row['cast_b']
    left,right=values[a],values[b]
    elapsed=_seconds(db,row['id'])
    roster={m['id']:m['name'] for m in store._cast(db)}
    total=left+right
    return {'id':row['id'],'title':row['title'],'status':row['status'],
            'cast_a':a,'cast_b':b,'name_a':roster.get(a,a),'name_b':roster.get(b,b),
            'points_a':store.format_points(left),'points_b':store.format_points(right),
            'percent_a':round(left*100/total,2) if total else 50,
            'percent_b':round(right*100/total,2) if total else 50,
            'duration_seconds':row['duration_seconds'],'elapsed_seconds':int(elapsed),
            'remaining_seconds':max(0,int(row['duration_seconds']-elapsed)),
            'started_at':row['started_at'],'ended_at':row['ended_at'],
            'finalized_at':row['finalized_at'],
            'winner':a if left>right else b if right>left else None,
            'final_result_needs_review':bool(snapshots and scores!=snapshots)}

def list_battles(limit=60):
    with store.LOCK,store.connect() as db:
        return [_view(db,r) for r in db.execute('SELECT * FROM battles ORDER BY created_at DESC LIMIT ?', (max(1,min(int(limit),100)),))]

def current():
    with store.LOCK,store.connect() as db:
        row=db.execute("SELECT * FROM battles WHERE status IN ('active','paused') ORDER BY started_at DESC LIMIT 1").fetchone()
        if not row:
            row=db.execute("SELECT * FROM battles WHERE status IN ('provisional','final') ORDER BY COALESCE(ended_at,updated_at) DESC LIMIT 1").fetchone()
        return _view(db,row) if row else None

def _audit(db,action,target,actor,reason='',details=None):
    db.execute('INSERT INTO audits(action,target,details,at) VALUES (?,?,?,?)',
             (action,target,json.dumps({'actor':actor,'reason':reason,'details':details or {}}),iso()))

def create(title,cast_a,cast_b,duration_seconds,actor='operator'):
    title=title.strip()
    if not 3<=len(title)<=100:raise ValueError('Battle title must be 3–100 characters')
    if cast_a==cast_b:raise ValueError('Choose two different cast members')
    if not 60<=int(duration_seconds)<=21600:raise ValueError('Duration must be 60–21600 seconds')
    with store.LOCK,store.connect() as db:
        roster={m['id'] for m in store._cast(db) if m['active']}
        if cast_a not in roster or cast_b not in roster:raise ValueError('Both participants must be active cast members')
        import uuid
        identifier='battle-'+uuid.uuid4().hex[:16]
        db.execute('INSERT INTO battles(id,title,cast_a,cast_b,duration_seconds,status,created_at,created_by,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
                   (identifier,title,cast_a,cast_b,int(duration_seconds),'draft',iso(),actor,iso()))
        _audit(db,'battle_create',identifier,actor,details={'cast_a':cast_a,'cast_b':cast_b})
        store._touch(db)
        return _view(db,db.execute('SELECT * FROM battles WHERE id=?',(identifier,)).fetchone())

def control(battle_id,action,actor='operator',reason=''):
    if action not in ('start','pause','resume','end','finalize','reopen','cancel'):
        raise ValueError('Invalid battle action')
    with store.LOCK,store.connect() as db:
        row=db.execute('SELECT * FROM battles WHERE id=?',(battle_id,)).fetchone()
        if not row:raise ValueError('Battle not found')
        current_status=row['status']
        legal={'start':('draft',),'pause':('active',),'resume':('paused',),
               'end':('active','paused'),'finalize':('provisional',),
               'reopen':('final',),'cancel':('draft',)}
        if current_status not in legal[action]:raise ValueError('Battle is not in a valid state for '+action)
        if action=='start' and db.execute("SELECT 1 FROM battles WHERE status IN ('active','paused') LIMIT 1").fetchone():
            raise ValueError('Another battle is already running')
        if action in ('reopen','finalize','cancel') and len(reason.strip())<8:
            raise ValueError('Enter a reason of at least 8 characters')
        stamp=iso()
        if action=='start':
            db.execute("UPDATE battles SET status='active',started_at=?,updated_at=? WHERE id=?",(stamp,stamp,battle_id))
            db.execute('INSERT INTO battle_segments(battle_id,started_at) VALUES (?,?)',(battle_id,stamp))
        elif action=='resume':
            db.execute("UPDATE battles SET status='active',updated_at=? WHERE id=?",(stamp,battle_id))
            db.execute('INSERT INTO battle_segments(battle_id,started_at) VALUES (?,?)',(battle_id,stamp))
        elif action in ('pause','end'):
            db.execute('UPDATE battle_segments SET ended_at=? WHERE battle_id=? AND ended_at IS NULL',(stamp,battle_id))
            db.execute('UPDATE battles SET status=?,ended_at=?,updated_at=? WHERE id=?',
                       ('paused' if action=='pause' else 'provisional',None if action=='pause' else stamp,stamp,battle_id))
        elif action=='finalize':
            totals=_score(db,row)
            db.execute("UPDATE battles SET status='final',final_json=?,finalized_at=?,updated_at=? WHERE id=?",
                       (json.dumps(totals),stamp,stamp,battle_id))
        elif action=='reopen':
            db.execute("UPDATE battles SET status='provisional',final_json=NULL,finalized_at=NULL,updated_at=? WHERE id=?",(stamp,battle_id))
        elif action=='cancel':
            db.execute("UPDATE battles SET status='cancelled',updated_at=? WHERE id=?",(stamp,battle_id))
        _audit(db,'battle_'+action,battle_id,actor,reason)
        store._touch(db)
        return _view(db,db.execute('SELECT * FROM battles WHERE id=?',(battle_id,)).fetchone())

def advance():
    with store.LOCK,store.connect() as db:
        rows=db.execute("SELECT * FROM battles WHERE status='active'").fetchall()
        for row in rows:
            if _seconds(db,row['id'])>=row['duration_seconds']:
                stamp=iso()
                db.execute('UPDATE battle_segments SET ended_at=? WHERE battle_id=? AND ended_at IS NULL',(stamp,row['id']))
                db.execute("UPDATE battles SET status='provisional',ended_at=?,updated_at=? WHERE id=?",(stamp,stamp,row['id']))
                _audit(db,'battle_timer_finished',row['id'],'system')
                store._touch(db)


def visible():
    with store.LOCK,store.connect() as db:
        return store._setting(db,'battles_visible')=='1'

def set_visibility(enabled:bool,actor='operator'):
    with store.LOCK,store.connect() as db:
        store._put_setting(db,'battles_visible','1' if enabled else '0')
        _audit(db,'battle_visibility','broadcast',actor,details={'visible':bool(enabled)})
        store._touch(db)
    return {'visible':bool(enabled)}

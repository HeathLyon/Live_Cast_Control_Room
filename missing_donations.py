"""Missing-payment reports and audited manual verification.

A report is NOT a payment. A producer approval creates a separately attributed,
verified-manual donation; original YouTube records remain immutable. Potential
late duplicate matches enter reconciliation instead of being counted twice.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime,timezone
from decimal import Decimal,ROUND_HALF_UP
import store
from core import parse_amount_to_micros


def stamp(): return store.now()

def parse_time(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None:raise ValueError('Missing timezone')
        return dt.astimezone(timezone.utc).isoformat(timespec='microseconds')
    except (TypeError,AttributeError,ValueError):
        raise ValueError('Donation time must be valid ISO-8601 with timezone')

def initialize():
    with store.LOCK,store.connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS missing_reports (
          id TEXT PRIMARY KEY, donor TEXT NOT NULL, amount_micros INTEGER NOT NULL,
          currency TEXT NOT NULL DEFAULT 'USD', message TEXT NOT NULL,
          cast_id TEXT NOT NULL, published_at TEXT NOT NULL,
          evidence TEXT NOT NULL, external_event_id TEXT,
          status TEXT NOT NULL DEFAULT 'pending',
          created_by TEXT NOT NULL, approved_by TEXT, donation_id TEXT,
          decision_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_missing_report_external ON missing_reports(external_event_id);
        ''')

def candidates(db,donor,amount_micros,when,external_id=None):
    if external_id:
        exact=db.execute('SELECT id,source,status,donor,amount_micros,published_at FROM donations WHERE id=?',(external_id,)).fetchall()
        if exact:return [dict(x) for x in exact]
    # Flag likely duplicates, but do not assume two identical contributions are one payment.
    rows=db.execute('''SELECT id,source,status,donor,amount_micros,published_at
       FROM donations WHERE ABS(julianday(published_at)-julianday(?))*86400 <= 120
         AND COALESCE(adjusted_amount_micros,amount_micros)=? LIMIT 40''',(when,amount_micros)).fetchall()
    return [dict(x) for x in rows if str(x['donor']).casefold().strip()==donor.casefold().strip()]

def create(donor,amount,cast_id,published_at,evidence,message='',external_event_id='',actor='operator'):
    donor=donor.strip(); evidence=evidence.strip()
    if not 2<=len(donor)<=100:raise ValueError('Donor must be 2–100 characters')
    if not 12<=len(evidence)<=1000:raise ValueError('Evidence must be a verifiable reference or description (12–1000 characters)')
    amount_micros=parse_amount_to_micros(amount)
    if amount_micros<=0:raise ValueError('Amount must be greater than zero')
    when=parse_time(published_at)
    external_id=external_event_id.strip().removeprefix('yt:')
    if len(external_id)>150:raise ValueError('Event ID too long')
    external_key='yt:'+external_id if external_id else None
    with store.LOCK,store.connect() as db:
        cast={m['id'] for m in store._cast(db) if m['active']}
        if cast_id not in cast:raise ValueError('Choose an active cast member')
        identifier='claim-'+uuid.uuid4().hex[:20]
        db.execute('''INSERT INTO missing_reports
          (id,donor,amount_micros,message,cast_id,published_at,evidence,external_event_id,
           status,created_by,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
           (identifier,donor,amount_micros,message.strip()[:500],cast_id,when,evidence,external_key,
            'pending',actor,stamp(),stamp()))
        db.execute('INSERT INTO audits(action,target,details,at) VALUES (?,?,?,?)',
                  ('missing_report_created',identifier,json.dumps({'actor':actor,'amount_micros':amount_micros,'cast_id':cast_id,'evidence':evidence}),stamp()))
        return {'id':identifier,'status':'pending','potential_duplicates':candidates(db,donor,amount_micros,when,external_key)}

def list_reports(status='all'):
    if status not in ('all','pending','approved','rejected'):raise ValueError('Invalid report status')
    with store.LOCK,store.connect() as db:
        sql='SELECT * FROM missing_reports'
        params=[]
        if status!='all':sql+=' WHERE status=?';params.append(status)
        sql+=' ORDER BY created_at DESC LIMIT 200'
        rows=[dict(r) for r in db.execute(sql,params)]
        for item in rows:
            item['potential_duplicates']=candidates(db,item['donor'],item['amount_micros'],item['published_at'],item['external_event_id']) if item['status']=='pending' else []
        return {'items':rows}

def decide(report_id,action,reason,acknowledge_duplicates=False,actor='operator'):
    if action not in ('approve','reject'):raise ValueError('Invalid approval action')
    if not 8<=len(reason.strip())<=500:raise ValueError('Decision reason must be 8–500 characters')
    with store.LOCK,store.connect() as db:
        row=db.execute('SELECT * FROM missing_reports WHERE id=?',(report_id,)).fetchone()
        if not row:raise ValueError('Missing report not found')
        if row['status']!='pending':raise ValueError('Report already decided')
        duplicates=candidates(db,row['donor'],row['amount_micros'],row['published_at'],row['external_event_id'])
        if action=='approve' and row['external_event_id'] and any(d['id']==row['external_event_id'] for d in duplicates):
            raise ValueError('This exact YouTube event is already recorded; correct its assignment instead of creating a second payment')
        if action=='approve' and duplicates and not acknowledge_duplicates:
            raise ValueError('Potential duplicate exists. Review it and explicitly acknowledge before approval')
        donation_id=None
        if action=='approve':
            donation_id='manual:'+row['id']
            ratio=Decimal(store._setting(db,'points_per_usd') or '1')
            points=int((Decimal(row['amount_micros'])/Decimal(1000)*ratio).to_integral_value(rounding=ROUND_HALF_UP))
            db.execute('''INSERT INTO donations
              (id,kind,donor,message,amount_micros,currency,amount_display,cast_id,status,points_milli,
               published_at,received_at,source,original_points_milli)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (donation_id,'manualVerified',row['donor'],row['message'],row['amount_micros'],'USD',
               '$'+format(row['amount_micros']/1_000_000,'.2f'),row['cast_id'],'assigned',points,
               row['published_at'],stamp(),'manual',points))
            # A late verified correction affects scores immediately but does not interrupt air with a stale alert.
            store._touch(db)
        db.execute('UPDATE missing_reports SET status=?,approved_by=?,donation_id=?,decision_reason=?,updated_at=? WHERE id=?',
                   ('approved' if action=='approve' else 'rejected',actor,donation_id,reason.strip(),stamp(),report_id))
        db.execute('INSERT INTO audits(action,target,details,at) VALUES (?,?,?,?)',
                   ('missing_report_'+action,report_id,json.dumps({'actor':actor,'reason':reason,'donation_id':donation_id,'potential_duplicates':len(duplicates)}),stamp()))
        return {'id':report_id,'status':'approved' if action=='approve' else 'rejected','donation_id':donation_id}

def find_matching_manual(db,record):
    rows=db.execute('''SELECT d.id,d.cast_id,d.donor,d.amount_micros,d.published_at,r.external_event_id
       FROM donations d LEFT JOIN missing_reports r ON r.donation_id=d.id
       WHERE d.source='manual' AND d.status='assigned' AND d.amount_micros=?
         AND ABS(julianday(d.published_at)-julianday(?))*86400 <= 120 LIMIT 40''',
       (record['amount_micros'],record['published_at'])).fetchall()
    return [dict(r) for r in rows if
            (r['external_event_id'] and r['external_event_id']==record['id']) or
            (str(r['donor']).casefold().strip()==str(record['donor']).casefold().strip())]

def reconcile(youtube_id,manual_id,keep,reason,actor='operator'):
    if keep not in ('youtube','manual'):raise ValueError('Choose which record to retain')
    if not 8<=len(reason.strip())<=500:raise ValueError('Reason must be 8–500 characters')
    with store.LOCK,store.connect() as db:
        yt=db.execute("SELECT * FROM donations WHERE id=? AND source='youtube' AND status='possible_duplicate'",(youtube_id,)).fetchone()
        manual=db.execute("SELECT * FROM donations WHERE id=? AND source='manual' AND status='assigned'",(manual_id,)).fetchone()
        if not yt or not manual:raise ValueError('Selected transaction is not a pending YouTube/manual pair')
        if manual_id not in [r['id'] for r in find_matching_manual(db,dict(yt))]:raise ValueError('Records do not match reconciliation criteria')
        if keep=='youtube':
            db.execute("UPDATE donations SET status='superseded',cast_id=NULL,points_milli=0 WHERE id=?",(manual_id,))
            db.execute("UPDATE donations SET status='assigned',cast_id=? WHERE id=?",(manual['cast_id'],youtube_id))
        else:
            db.execute("UPDATE donations SET status='superseded',cast_id=NULL,points_milli=0 WHERE id=?",(youtube_id,))
        db.execute('INSERT INTO audits(action,target,details,at) VALUES (?,?,?,?)',
          ('donation_duplicate_reconciled',youtube_id,json.dumps({'actor':actor,'reason':reason,'manual_id':manual_id,'keep':keep}),stamp()))
        store._touch(db)
        return {'youtube_id':youtube_id,'manual_id':manual_id,'kept':keep}

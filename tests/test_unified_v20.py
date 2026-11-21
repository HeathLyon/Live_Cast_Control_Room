"""Acceptance tests for fresh battle starts, timestamps, manual claim workflow and dedupe."""
from datetime import datetime,timezone,timedelta
import store,battles,missing_donations
import pytest


def evt(i,donor='Viewer',amount=10,stamp=None,tag='#Marcus'):
    return {'id':i,'snippet':{'type':'superChatEvent',
      'publishedAt':(stamp or datetime.now(timezone.utc)).isoformat(),
      'superChatDetails':{'amountMicros':str(int(amount*1000000)),'currency':'USD',
                          'amountDisplayString':f'${amount}','userComment':tag}},
      'authorDetails':{'displayName':donor}}

@pytest.fixture
def db(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB_PATH',tmp_path/'unified.sqlite3')
    monkeypatch.setattr(store,'LIVE_MODE',True)
    monkeypatch.setattr(store,'QUEUE_MODE',True)
    store.initialize();battles.initialize();missing_donations.initialize()


def test_new_battle_starts_at_zero_updates_overall_then_freezes(db):
    store.ingest(evt('yt:before',amount=500),source='youtube')
    b=battles.create('Round one','marcus','avery',600,actor='producer-one')
    assert b['points_a']=='0.00' and b['status']=='draft'
    b=battles.control(b['id'],'start',actor='producer-one')
    assert b['points_a']=='0.00'
    store.ingest(evt('yt:during',amount=25),source='youtube')
    b=battles.current()
    assert b['points_a']=='25.00' and b['points_b']=='0.00'
    assert store.state()['ranking'][0]['points']=='525.00'
    b=battles.control(b['id'],'end',actor='producer-one')
    assert b['status']=='provisional'
    b=battles.control(b['id'],'finalize',reason='Producer verified all events',actor='producer-one')
    assert b['status']=='final'
    # Correct a payment already within the finalized scoring window.
    store.correct_transaction('yt:during','marcus','30.00','Confirmed receipt discrepancy',actor='producer-one')
    b=battles.current()
    assert b['points_a']=='25.00' and b['final_result_needs_review']
    b=battles.control(b['id'],'reopen',reason='New validated evidence',actor='producer-one')
    assert b['points_a']=='30.00' and b['status']=='provisional'


def test_paused_battle_does_not_count_payment(db):
    b=battles.create('Battle two','marcus','avery',600)
    battles.control(b['id'],'start')
    b=battles.control(b['id'],'pause')
    store.ingest(evt('yt:paused',amount=20),source='youtube')
    assert battles.current()['points_a']=='0.00'
    battles.control(b['id'],'resume')
    store.ingest(evt('yt:resume',amount=8),source='youtube')
    assert battles.current()['points_a']=='8.00'


def test_manual_report_approval_separate_from_test_scores_and_battle(db):
    b=battles.create('Round three','marcus','avery',900)
    battles.control(b['id'],'start')
    when=datetime.now(timezone.utc).isoformat()
    report=missing_donations.create('Real Viewer','20.00','marcus',when,
          evidence='Producer checked official channel receipt',message='message #Marcus',actor='producer-alpha')
    assert store.state()['ranking'][0]['points']=='0.00'
    assert report['status']=='pending'
    decided=missing_donations.decide(report['id'],'approve','Verified the original transaction',actor='producer-alpha')
    assert decided['donation_id'].startswith('manual:')
    assert store.state()['ranking'][0]['points']=='20.00'
    assert battles.current()['points_a']=='20.00'
    row=store.transaction_detail(decided['donation_id'])['item']
    assert row['source']=='manual'
    assert row['status']=='assigned'
    # Fake payments never join the official production score.
    store.ingest(evt('sim:fake',amount=1000),source='simulation')
    assert store.state()['ranking'][0]['points']=='20.00'


def test_delayed_youtube_payment_does_not_double_manual_funding(db):
    when=datetime.now(timezone.utc)
    report=missing_donations.create('Matching Viewer','45.00','marcus',when.isoformat(),
      evidence='Screenshot and verified official receipts',actor='producer')
    approved=missing_donations.decide(report['id'],'approve','Verified proof from original receipts',actor='producer')
    manual_id=approved['donation_id']
    assert store.state()['gross_usd']=='45.00'
    incoming=store.ingest(evt('yt:late',donor='Matching Viewer',amount=45,stamp=when),source='youtube')
    assert incoming['status']=='possible_duplicate'
    assert store.state()['gross_usd']=='45.00'
    assert store.state()['ranking'][0]['points']=='45.00'
    with pytest.raises(ValueError,match='reconcile'):
        store.correct_transaction('yt:late','marcus','45.00','I should merge this',actor='producer')
    out=missing_donations.reconcile('yt:late',manual_id,'youtube','Verified same receipt ID',actor='producer')
    assert out['kept']=='youtube'
    assert store.state()['gross_usd']=='45.00'
    assert store.state()['ranking'][0]['points']=='45.00'
    assert store.transaction_detail(manual_id)['item']['status']=='superseded'
    assert store.transaction_detail('yt:late')['item']['status']=='assigned'


def test_exact_duplicate_cannot_be_approved_even_if_ignored_warning(db):
    at=datetime.now(timezone.utc)
    store.ingest(evt('yt:exact-123',amount=12,stamp=at,donor='Exact User'),source='youtube')
    claim=missing_donations.create('Exact User','12','marcus',at.isoformat(),
      evidence='Verified original Super Chat receipt 123',external_event_id='exact-123')
    with pytest.raises(ValueError,match='already recorded'):
        missing_donations.decide(claim['id'],'approve','Reviewed official ledger',True)


def test_battle_visibility_and_single_battle_invariant(db):
    b=battles.create('Round four','marcus','avery',60)
    c=battles.create('Round five','marcus','jordan',60)
    assert not battles.visible()
    battles.set_visibility(True,actor='producer')
    assert battles.visible()
    battles.control(b['id'],'start')
    with pytest.raises(ValueError,match='already running'):
        battles.control(c['id'],'start')
    assert len(battles.list_battles())==2

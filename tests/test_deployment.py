"""Exercise production startup from a fresh interpreter and a disposable database."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'test-only-password-1234'
STARTUP = """
from app import app
from fastapi.testclient import TestClient

with TestClient(app) as client:
    assert client.get('/health').json()['ok']
"""


@pytest.fixture
def production_env():
    # Linux /tmp is intentionally rejected by production preflight.
    with tempfile.TemporaryDirectory(prefix='livecast-deploy-test-', dir=ROOT) as directory:
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('LIVECAST_', 'RENDER', 'YOUTUBE_'))
               and key not in ('OPERATOR_PASSWORD', 'VIEW_TOKEN')}
        salt = bytes(range(16))
        digest = hashlib.scrypt(PASSWORD.encode(), salt=salt, n=16384, r=8, p=1).hex()
        password_hash = f'scrypt$16384$8$1${salt.hex()}${digest}'
        env.update(
            LIVECAST_ENV='production',
            LIVECAST_REMOTE_TEST='1',
            LIVECAST_DB=str(Path(directory) / 'livecast.sqlite3'),
            LIVECAST_PERSISTENT_ROOT=directory,
            LIVECAST_REQUIRE_MOUNT='0',
            LIVECAST_SERVER_QUEUE='1',
            PUBLIC_OVERLAYS='1',
            PAGES_ORIGIN='https://heathlyon.github.io',
            RENDER_EXTERNAL_URL='https://livecast-test.example.org',
            VIEW_TOKEN='test-only-view-token-value-123456789',
            LIVECAST_USERS_JSON=json.dumps({
                name: {'role': name, 'password_hash': password_hash}
                for name in ('admin', 'producer', 'viewer')
            }),
        )
        yield env


def run_python(env, code):
    return subprocess.run(
        [sys.executable, '-c', code], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize(('setting', 'value', 'diagnostic'), [
    ('LIVECAST_USERS_JSON', None, 'LIVECAST_USERS_JSON'),
    ('LIVECAST_USERS_JSON', 'invalid-private-json', 'LIVECAST_USERS_JSON'),
    ('LIVECAST_USERS_JSON', '{"admin":{"role":"admin","password_hash":"scrypt$16384$8$1$bad$bad"}}',
     'LIVECAST_USERS_JSON'),
    ('VIEW_TOKEN', None, 'VIEW_TOKEN'),
    ('VIEW_TOKEN', 'too-short', 'VIEW_TOKEN'),
    ('LIVECAST_DB', None, 'LIVECAST_DB'),
    ('LIVECAST_REQUIRE_MOUNT', '1', 'not a mounted volume'),
    ('LIVECAST_ALERT_SECONDS', 'private-invalid-setting', 'LIVECAST_ALERT_SECONDS'),
    ('YOUTUBE_MIN_POLL_SECONDS', 'nan', 'YOUTUBE_MIN_POLL_SECONDS'),
])
def test_invalid_production_settings_fail_before_database_creation(production_env, setting, value, diagnostic):
    database = Path(production_env['LIVECAST_DB'])
    if value is None:
        production_env.pop(setting)
    else:
        production_env[setting] = value
    result = run_python(production_env, STARTUP)
    assert result.returncode != 0
    assert diagnostic in result.stderr
    if value and len(value) > 2:
        assert value not in result.stderr
    assert not database.exists()


def test_production_startup_and_restart(production_env):
    first = run_python(production_env, STARTUP + f"""
    assert client.get('/health').json() == {{
        'ok': True, 'mode': 'production', 'profile': 'production',
        'storage': 'persistent-single-node-sqlite', 'version': '2.0.0-rc1',
        'youtube_connected': False, 'public_overlays_enabled': True,
    }}
    admin = ('admin', {PASSWORD!r})
    assert client.get('/api/state').status_code == 401
    assert client.get('/api/state', auth=('admin', 'wrong-password')).status_code == 401
    assert client.get('/api/state', auth=('viewer', {PASSWORD!r})).status_code == 200
    for role in ('viewer', 'producer'):
        assert client.post('/api/simulate', auth=(role, {PASSWORD!r}), json={{}}).status_code == 403
    assert client.post('/api/simulate', auth=admin, json={{
        'event_id': 'isolated-test', 'message': '#Marcus', 'amount': '20.00',
    }}).status_code == 200
    origin = 'https://heathlyon.github.io'
    for path in ('state', 'alerts', 'playback', 'goals', 'battle', 'graphics/top3'):
        response = client.get('/public/' + path, headers={{'Origin': origin}})
        assert response.status_code == 200, (path, response.text)
        assert response.headers['Access-Control-Allow-Origin'] == origin
    assert client.get('/public/state').json()['ranking'][0]['points'] == '0.00'
    import store
    event = {{
        'id': 'fixture-paid-donation',
        'snippet': {{
            'type': 'superChatEvent',
            'superChatDetails': {{'amountMicros': '10000000', 'currency': 'USD', 'userComment': '#Marcus'}},
        }},
        'authorDetails': {{'displayName': 'Local fixture'}},
    }}
    assert store.ingest(event, source='youtube')['result'] == 'created'
""")
    assert first.returncode == 0, first.stderr
    second = run_python(production_env, STARTUP + f"""
    state = client.get('/api/state', auth=('admin', {PASSWORD!r})).json()
    assert state['event_count'] == 1
    assert state['simulated_event_count'] == 1
    assert state['ranking'][0]['points'] == '10.00'

    import store
    store.DB_PATH = store.DB_PATH.with_name('missing.sqlite3')
    assert client.get('/health').status_code == 503
    assert not store.DB_PATH.exists()
""")
    assert second.returncode == 0, second.stderr

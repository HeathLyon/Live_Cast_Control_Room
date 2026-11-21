"""Central deployment settings and strict single-node production preflight."""
from __future__ import annotations
import os
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

PROFILE = os.getenv('LIVECAST_ENV','staging').lower()
PUBLIC_BASE = (os.getenv('LIVECAST_PUBLIC_URL') or os.getenv('RENDER_EXTERNAL_URL') or 'https://live-cast-scoreboard-demo.onrender.com').rstrip('/')
PAGES_BASE = os.getenv('LIVECAST_PAGES_URL',
                       'https://heathlyon.github.io/Live_Cast_Scoreboard_v0.2_Haiti/').rstrip('/')+'/'

SCRYPT_HASH = re.compile(r'scrypt\$16384\$8\$1\$[0-9a-fA-F]{32}\$[0-9a-f]{128}')


def numeric_env(name, default, convert):
    try:
        value = convert(os.getenv(name, default))
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError
        return value
    except ValueError:
        raise RuntimeError(f'{name} must be a finite {convert.__name__}') from None


def check_production_config():
    if PROFILE not in ('production','staging'):
        raise RuntimeError('LIVECAST_ENV must be staging or production')
    if PROFILE != 'production':
        if os.getenv('LIVECAST_REQUIRE_MOUNT') == '1':
            raise RuntimeError('LIVECAST_REQUIRE_MOUNT=1 requires LIVECAST_ENV=production')
        return
    raw_db=os.getenv('LIVECAST_DB','')
    raw_root=os.getenv('LIVECAST_PERSISTENT_ROOT','')
    if not raw_db or not raw_root:
        raise RuntimeError('Production requires LIVECAST_DB and LIVECAST_PERSISTENT_ROOT')
    db=Path(raw_db).resolve()
    root=Path(raw_root).resolve()
    if (not Path(raw_db).is_absolute() or not Path(raw_root).is_absolute()
            or db == root or not db.is_relative_to(root)
            or not root.is_dir() or not os.access(root,os.W_OK)):
        raise RuntimeError('Production DB must be inside an existing writable persistent root')
    if any(root.is_relative_to(Path(path).resolve())
           for path in ('/tmp', '/app', '/opt/render/project')):
        raise RuntimeError('Production storage root looks ephemeral')
    if os.getenv('RENDER') == 'true' and root != Path('/var/data'):
        raise RuntimeError('Render production requires LIVECAST_PERSISTENT_ROOT=/var/data')
    if (os.getenv('RENDER') == 'true' or os.getenv('LIVECAST_REQUIRE_MOUNT') == '1') and not os.path.ismount(root):
        raise RuntimeError('LIVECAST_PERSISTENT_ROOT is not a mounted volume')
    try:
        users=json.loads(os.getenv('LIVECAST_USERS_JSON',''))
        if not isinstance(users,dict) or not any(isinstance(x,dict) and x.get('role')=='admin' for x in users.values()):
            raise ValueError('At least one admin required')
        for username, item in users.items():
            if (not username.strip() or ':' in username
                    or not isinstance(item, dict) or item.get('role') not in ('admin', 'producer', 'viewer')
                    or not SCRYPT_HASH.fullmatch(str(item.get('password_hash', '')))):
                raise ValueError('Invalid user credential')
    except (ValueError,TypeError):
        raise RuntimeError('LIVECAST_USERS_JSON must contain valid named scrypt accounts including an admin') from None
    token = os.getenv('VIEW_TOKEN', '')
    if len(token) < 32 or not token.isascii() or not token.isprintable() or ' ' in token:
        raise RuntimeError('VIEW_TOKEN must contain at least 32 non-space printable ASCII characters')
    if os.getenv('LIVECAST_REMOTE_TEST','0')!='1':
        raise RuntimeError('Production requires LIVECAST_REMOTE_TEST=1 to authenticate operator routes')
    if not (os.getenv('LIVECAST_PUBLIC_URL') or os.getenv('RENDER_EXTERNAL_URL')):
        raise RuntimeError('Production requires LIVECAST_PUBLIC_URL or Render RENDER_EXTERNAL_URL')
    if os.getenv('LIVECAST_SERVER_QUEUE','1')!='1':
        raise RuntimeError('Production requires server-backed broadcast queue')
    for name,url in [('LIVECAST_PUBLIC_URL',PUBLIC_BASE),('LIVECAST_PAGES_URL',PAGES_BASE)]:
        try:
            parsed = urlparse(url)
            if parsed.scheme == 'https' and parsed.hostname and parsed.username is None:
                continue
        except ValueError:
            pass
        raise RuntimeError(name+' must be an HTTPS URL') from None

def graphic_links():
    base=PAGES_BASE+'pages-overlay.html?graphic='
    return {'combined':base+'top3-alert', 'top3':base+'top3',
            'top3_on_donation':base+'top3&show=on-donation',
            'alert':base+'alert', 'goals':base+'goals',
            'full':base+'full', 'battle':base+'battle', 'producer':PAGES_BASE+'pages-producer.html',
            'setup':PAGES_BASE+'pages-setup.html'}

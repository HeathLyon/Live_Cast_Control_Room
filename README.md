# LIVE CAST Control Room — Unified Project v2.0 RC1

**One repository, one private production server, and GitHub Pages broadcast overlays for vMix.**

This is a deployable **release candidate**, not yet a certified 21-day production service. It consolidates the previous v0.5/v1.1 projects and adds head-to-head battles and an evidence-based missing-donation workflow. **71 automated tests pass** locally. Real YouTube purchases, the actual vMix browser engine, production authentication, and paid-server restart/backup recovery have **not** been verified on your account.

## At a glance

| Area | What it does |
|---|---|
| Private Control Room `/` | Stats, system health, cast roster, hashtags, goals, donation data, debug, queue controls and graphics studio |
| Donation ledger | Keeps original event ID, donor, amount, message, UTC event time, source, attribution and audited corrections |
| Production accounts | Named admin / producer / viewer accounts with scrypt-hashed passwords; private HTTP Basic over HTTPS |
| Missed donations | Report → evidence → producer approve/reject → duplicate review → audited manual credit; late YouTube matches do not double count |
| Head-to-head | Two cast members, zero initial battle points, live progress bars, timer, pause/resume, provisional and finalized results |
| Alert queue | Server-controlled alert timing, grouping, pause/resume/skip; scores are independent of animation playback |
| Test lane | Synthetic Super Chats and burst events isolated from production scoring, removable by administrators |
| YouTube | Public live-chat listener for real paid Super Chat/Sticker events; ordinary text chat is never a donation |
| GitHub Pages | Transparent graphics: Top 3, donation alert, synchronized Top 3+alert, goals, head-to-head, full rankings |
| Render | Paid single-server Python service with mounted persistent SQLite DB and no automatic redeploys |

**Scoring contract:** Real YouTube and approved manual records count in production. Synthetic events do not. An unassigned genuine payment is kept for review. Battle and overall points both update for eligible contributions during each battle's active UTC scoring windows; pausing suspends battle scoring, not overall scoring. Finalized battle results are frozen until producers reopen them.

**Donation selection:** Hashtags are OPTIONAL. Automatic cast matching via tags works when configured; donations without an unambiguous selection go to a producer review queue. Integration with any third-party cast-selection/voting platform must be implemented after its actual API is confirmed.

## Start here

1. **[Deploy to Render and GitHub Pages](docs/DEPLOY_RENDER.md)** — step-by-step setup, accounts, deployment and URLs.
2. **[Test the actual YouTube stream](docs/YOUTUBE_TEST.md)** — regular chat, a simulated event, and a real authorized paid event.
3. **[Operate and recover](docs/OPERATIONS.md)** — cast, battles, reconciliation, backups, permissions and alerts.
4. **[Production acceptance checklist](docs/GO_LIVE_CHECKLIST.md)** — requirements before December 6.
5. **[Technical architecture](docs/ARCHITECTURE.md)** and **[Project details](docs/PROJECT_CASE_STUDY.md)**.
6. **[Codex instructions](docs/CODEX_UPLOAD.md)** — when creating a new GitHub repository from this ZIP.

## Repository contents

```text
app.py                  Private API + operator website and public read-only feeds
store.py                SQLite donation, goals, cast, graphics, queue, audit and YouTube checkpoints
battles.py              Head-to-head battle lifecycle and time-window scoring
missing_donations.py    Missing-payment reports and late-event duplicate reconciliation
youtube_monitor.py      YouTube live-chat polling listener
core.py                 Paid-event classification, hashtag recognition and scoring
ops.py                  Production configuration and GitHub Pages URL generation
index.html              Private operator control room
css/                    Interface and transparent Haitian-blue/red overlays
js/                     Operator, data, graphics, system, battles and public overlay code
pages-overlay.html      GitHub Pages/vMix transparent graphics entry point
pages-setup.html        GitHub Pages URL generator
pages-producer.html     Read-only Haitian producer view
render.yaml             NEW paid production service + persistent disk
render.staging.yaml     Optional separate disposable Free staging service
scripts/                Credential-hash generator and smoke/verification utilities
tests/                  Pytest suite
```

## Local development

Python 3.11 recommended. On Windows, extract the ZIP and run `setup_windows.bat`, then `start_windows.bat`. Or:

```bash
python -m venv .venv
# Activate the venv in your shell
pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Local default mode is staging. The operator page is `http://127.0.0.1:8000/`; try `/overlay/battle?preview=1`. The live production server requires the credentials and durable disk detailed in the Render guide.

## Explicit limitations and required real-world verification

- **Not yet signed off for official donations.** Current YouTube collector uses `liveChatMessages.list` at a configurable polling interval (default 50 seconds). Google now recommends `streamList` for lower-latency delivery and recovery; implement and test it if the show requires second-by-second freshness.
- A persistent SQLite disk is **not an off-server backup**. Establish automated independent backups and complete a restoration rehearsal before launch.
- Named HTTP Basic credentials over HTTPS are implemented. MFA/OIDC, sign-in rate limiting, and account revocation workflows still require hardening.
- No guarantee of recovering every paid event following an extended YouTube outage. Plan official account-side reconciliation and a staffing procedure.
- Only USD is automatically scored. Other currencies are held for producer review until a conversion policy is defined.
- The graphics studio produces configured variants of the existing templates; it is not an arbitrary drag-and-drop designer.
- A completely different platform-specific cast-selection API is not yet integrated.
- Browser automation in this build environment could not navigate localhost (`ERR_BLOCKED_BY_ADMINISTRATOR`); actual Chrome/Edge/vMix visual checks remain on the checklist.

## Privacy and deployment safety

**Never commit passwords, credential hashes, API keys, token values, or `.sqlite3` files.** All private operations are served by Render and protected by authentication. GitHub Pages serves **only public, read-only score and graphic data** and must not receive raw donation histories or personal records.

MIT-style licensing is not automatically asserted here. Add the license you want if publishing the source publicly.

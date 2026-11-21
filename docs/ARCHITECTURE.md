# System architecture — single-node live scoreboard

`YouTube Live Chat API` → `YouTubeMonitor` → `store.ingest()` → **persistent SQLite donation ledger** → cast rankings/goal metrics/battle time-window queries. A separate database-backed `broadcast_queue` is ticked by the application worker and serves one public active item to all vMix browser sources. Unmatched paid donations are retained for producer review rather than guessed. An independent `missing_reports` table accepts producer evidence and approval; late payment duplicates are reconciled with audit records.

Private operators open the **Render web service** (`index.html`, FastAPI). Named HTTP Basic accounts authenticate server-side as admins/producers/viewers. Github Pages hosts public static overlay scripts; it reads only the allow-listed `/public/` broadcast endpoints (rankings, current goal, current battle, published graphic config, and alert playback). It must never receive transaction details, passwords or Google credentials.

**Battle accounting** is computed from eligible donation event times inside an ordered set of running segments. Paused intervals are excluded. An official finalized result is an immutable snapshot until a producer reopens the result; after-audit corrections flag the result for review.

**Durability model** is one Uvicorn worker and one SQLite WAL database on Render's attached disk. This is a deliberate minimal-cost option, not a horizontally scalable, highly available database cluster. Scaling across workers or running two collectors requires a shared transactional datastore (e.g. managed Postgres), a single ingestion leader, and migration tests.

**Known gaps:** YouTube `streamList`, continuous offsite backups, OAuth/MFA and rate limiting, independent YouTube-side donor reconciliation, exact downstream cast-selection API, full visual browser/vMix acceptance. A durable disk does not cover region or provider loss. These are go-live decisions, not decorative backlog items.

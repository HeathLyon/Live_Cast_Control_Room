# Live Cast Scoreboard — Project Details

## Project goal

Develop a configurable real-time competition scoreboard for a Haitian reality show's December 2026 live production. Broadcast directors needed transparent vMix graphics, fast donation tracking, a private production interface, and the ability to correct missed or misattributed contributions without repeatedly changing code during the event.

## Evolution

The early versions established FastAPI scoring, cast/hashtag recognition, YouTube-themed simulated messages, and Top Three and alert graphics. A GitHub Pages bridge separated public graphics from the private scoring server. Subsequent versions added goal counters, countdowns, editing, YouTube live-chat ingestion, server health diagnostics, donor review and graphics presets. The unified v2.0 release candidate consolidates those components and adds an audited manual missing-payment workflow plus zero-start head-to-head battles with time-window scoring, live progress bars, and provisional/final results.

## Stack and architecture

Python 3 / FastAPI and SQLite WAL; browser JavaScript/CSS/HTML; GitHub repository and Pages; Render paid single-instance hosting with a persistent disk; and vMix Web Browser graphic sources. Public overlay endpoints expose only safe scoring/graphics data. Production operator controls use server-side authorization. Donation records are separate from queue playback, so heavy animation volume does not delay accounting.

## Design decisions

- A new battle uses only contributions within that battle's active scoring intervals while also updating the season-long ranking.
- A missing donation report has no scoring effect until verification and producer approval.
- Original YouTube values are immutable; changes are tracked with before/after data and audit reasons.
- Test events are explicitly isolated from production scoring.
- The exact cast-selection mechanism remains configurable: hashtags are optional until the channel's native or third-party selection system is identified.
- Real money accounting requires persistent storage and independent backup rather than an ephemeral demo database.

## Demonstrated versus pending

**Implemented and tested locally:** accounting, goal and cast configuration, filtered donation history, audit corrections, synthetic event isolation, backend queue behavior, battle lifecycle, manual reports and duplicate reconciliation. The Python test suite passed **71 tests** as of the creation of this release candidate.

**Not yet verified:** A real Super Chat on the actual production account, current production vMix browser rendering, unattended long-duration ingestion, guaranteed recovery from YouTube outages, automated offsite backup and restoration, and named-user MFA. The current collector uses polling and should be upgraded or accepted with an explicitly rehearsed reconciliation procedure before official competition use.

## Outcome / next phase

The release candidate offers a single web control room and stable GitHub Pages URLs. The next phase is paid Render provisioning, secure producer onboarding, a real channel integration test, a full broadcast rehearsal, and formal producer sign-off for the December 6–26 run. This case study describes the software work completed to date and does not claim the event has already been held.

# Production operations handbook

## Before every segment

Verify the correct cast roster, YouTube video ID, database integrity, production profile, graphics enabled, active goals, queue paused/resumed state, and scheduled backups. Run a dry-run graphics preview that **does not change live scores**. Confirm producer access from a separate device. Keep a verified copy of the live service hostname and a static emergency graphic in vMix.

## Correcting a payment

Control Room → Donation Data → search by donor/ID → View/Correct → adjust cast or credited amount → mandatory reason → confirmation. The original YouTube event ID and amount remain in the ledger. Corrections to an already issued animation cancel its pending stale alert and update rankings directly.

For a genuinely absent paid event, use Missing Donations → report original donor, amount, selected cast, original payment time and independent evidence. The producer approves/rejects; the app checks for possible duplicate contributions. A newly approved record is **verified manual**, never represented as an API-verified YouTube transaction. If an arriving YouTube event resembles it, hold that event until the two can be reconciled; do not award points twice.

## Head-to-head battles

Create a battle with two distinct contestants and duration. It starts at 0–0 regardless of their overall ranking. Click Start; turn **Show battle ON AIR** on when appropriate. Donations during the running windows count both in that battle and overall. Pause stops the battle's countdown **and its scoring window**; the overall leaderboard continues counting. End marks the result provisional. Producer finalization freezes the result; late corrections show a discrepancy warning until reopened and re-finalized. Only one active or paused battle is permitted.

## Graphics

Each URL is a stable GitHub Pages HTML page with `?graphic=<id>`. The backend is configured centrally in `js/site-config.js`. Use the Graphics Studio to clone an existing template, save its draft, preview, publish and copy the generated URL. For a new *structurally different* layout, source development is still required.

## Alert queue

Donation scoring does not depend on animated output. A single server timeline drives alert playback, so browser reloads don't independently replay the queue. Pause, resume, skip, or optionally enable burst grouping from System & Links. Grouping aggregates on-screen acknowledgements **only**; the underlying donation records remain individual. Do not group if producers promised a personalized on-air message to each donor.

## Test and debug

Only admins can create or clear simulated records. Simulations never affect production ranking, goals, or battle totals. Individual synthetic IDs can be removed. Use preview overlays to visually test graphics in production without awarding scores.

## Incident response

If YouTube connection degrades, keep the current scoreboard visible but stop claiming it is current, flag connection health in production, notify staff, reconcile against official authorized source records, and avoid finalizing battles until disputed events are resolved. If Render goes down, use a prepared static standby graphic; do not run competing collectors and databases until a recovery leader confirms which is authoritative. Download/offload database backups at least daily and rehearse the restore procedure. **A downloadable backup button alone is insufficient for 21-day unattended reliability.**

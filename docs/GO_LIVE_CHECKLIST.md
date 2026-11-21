# December 6–26, 2026 — production go/no-go checklist

**Release:** v2.0.0-rc1; **status:** software release candidate. The tests below are not all complete.

- [ ] Full project imported to NEW GitHub repository; no leaked credentials or database files.
- [ ] GitHub Pages publishes transparent graphic links and actual vMix browser inputs render them.
- [ ] New Render Starter web service is paid and remains awake, disk is mounted at `/var/data`, single worker active.
- [ ] Live service `/health` shows `mode=production`, `version=2.0.0-rc1`, persistent storage.
- [ ] Unique named producer accounts with appropriate permissions; MFA/proxy and rate limiting agreed.
- [ ] Off-server **automatic** backups configured and a backup successfully restored to staging.
- [ ] Official cast roster loaded, all test placeholders inactive/removed, attribution rules approved.
- [ ] Real channel access and exact cast-selection workflow confirmed. Hashtags optional, direct-selection API if supported.
- [ ] Real public live-chat connection tested, ordinary chat observed but **not counted**.
- [ ] At least one authorized real paid Super Chat/Sticker event imported **once**, correctly scored and shown in vMix.
- [ ] Polling latency measured; `streamList` migration or producer-approved latency/reconciliation contingency completed.
- [ ] Simulated donations do not affect production rankings, goals, battle totals or on-air queue.
- [ ] Missing-donation evidence/approval tested; late same-payment YouTube event does not double count.
- [ ] Ambiguous tags and non-USD donations held for review rather than guessing a cast member.
- [ ] Head-to-head battle: start 0–0, parallel overall scoring, pause and timer end, provisional/final correction handling tested.
- [ ] 100+ burst records and queue group/skip recovery handled without losing donations.
- [ ] Restart/redeploy persistence and queue recovery tested off-air.
- [ ] Static emergency vMix scoreboard available; on-call escalation and staff assignments documented.
- [ ] Freeze deploys for active show segments; no automatic redeploys.
- [ ] Producer and administrator sign-off completed before accepting official scoring.

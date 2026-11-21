# Real YouTube stream acceptance test

## Required access

An authorized public YouTube livestream with live chat enabled; YouTube Data API v3; and the server-side API key stored only in Render. YouTube Super Chat must be enabled for the channel to test a *real* payment. Merely typing `$25 #Marcus` as an ordinary chat message is **not** a paid Super Chat.

## Procedure

1. Verify Render `/health` returns production mode and persistent storage; check `/public/state` shows only rankings.
2. Add two cast members in Control Room → Scoring & Cast. Optionally configure their unique hashtags; leave them blank if the production's actual cast-selection method is not settled.
3. Open the `graphic=top3` permanent overlay as a connection test. Then open `graphic=top3-alert`, `graphic=goals` and `graphic=battle`. Configure a goal and an on-air battle if desired.
4. Start a public test livestream; connect its URL in the Control Room YouTube tab. Confirm status `listening` *before* viewers make donations.
5. Post a regular YouTube chat message. The **regular text seen** counter should rise after polling; it must not be added to the ledger or ranking.
6. Send a simulated $25 Super Chat via Debug. In **production**, it must appear only in test history, never the public rank/goal/battle or broadcast alert queue.
7. If authorized and eligible, make one small actual Super Chat. Confirm exactly one `yt:` event, original timestamp, USD amount, rank/goal change, and alert queue entry. Record measured YouTube→Render and Render→vMix delays.
8. Test a payment with no recognized tag; it should stay unassigned. Assign it from the private review queue; inspect the audit record and battle eligibility.
9. Create a missing-payment *report* with independent evidence. Verify that a report alone changes nothing; after approval the new **verified manual** payment changes official scores and eligible battle results.
10. Simulate a late YouTube arrival matching an approved manual payment **in staging**, verify the second event is held as a possible duplicate, then reconcile.
11. Generate 100 and 500 test events (multiple runs if necessary) to test load and duplicate prevention. Confirm the server-side alert queue can be paused/continued/grouped without changing scores.
12. Reconnect, restart, download a backup, restore to a nonproduction instance, and compare ledger totals, audit records and battle results.

## YouTube collector limitation

Current code uses `liveChatMessages.list`, respecting YouTube's `pollingIntervalMillis` and a minimum polling interval set in `YOUTUBE_MIN_POLL_SECONDS` (default 50 seconds). Google recommends `streamList` for faster push delivery and resume tokens. Saved polling continuation tokens help but do not guarantee recovery of all events after extended downtime. Make this an explicit launch approval item if the battles need fast score changes.

References: <https://developers.google.com/youtube/data/live/reference/rest/v3/liveChatMessages/list> and <https://developers.google.com/youtube/data/live/reference/rest/v3/liveChatMessages/streamList>.

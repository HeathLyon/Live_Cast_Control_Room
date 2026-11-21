# Import the project with Codex

Create a **new GitHub repository** `Live_Cast_Control_Room`; retain the old v0.5 demo repository intact. Supply the full ZIP to Codex or extract all files into the local repository directory.

**Codex prompt:**

> Import the supplied `Live_Cast_Control_Room_Unified_v2_Full.zip` into the root of my new GitHub repository `Live_Cast_Control_Room`, preserving its directories. Do not reuse the old scoreboard repo or mix it with v0.5. Confirm app.py, render.yaml, pages-overlay.html, js/site-config.js, battles.py, missing_donations.py, and all tests are present. Run `pip install -r requirements-dev.txt`, `python -m pytest -q`, and `node --check` on all js files. Fix any issues, run a local HTTP smoke check, and open a PR to main. Do not commit credentials, passwords, API keys, or *.sqlite3 files. Do not deploy the paid service or modify Render billing until I authorize that action.

Once approved and merged: activate GitHub Pages on `main` root. Then follow `docs/DEPLOY_RENDER.md` to provision the new paid Render server. Edit only the public Render hostname in `js/site-config.js` after Render assigns the URL; no secret should ever be stored there.

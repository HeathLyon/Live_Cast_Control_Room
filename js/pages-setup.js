"use strict";
const form = document.getElementById('link-form');
const output = document.getElementById('generated-links');
const configured=window.LIVECAST_SITE?.backendUrl||'';
if(configured)document.getElementById('backend-url').value=configured;
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const input = document.getElementById('backend-url').value.trim().replace(/\/+$/, '');
  let backend;
  try { backend = new URL(input); }
  catch { output.textContent = 'Enter the full HTTPS Render URL.'; return; }
  if (backend.protocol !== 'https:' || backend.pathname !== '/' || backend.search || backend.hash) {
    output.textContent = 'Use only the HTTPS service origin, for example https://example.onrender.com'; return;
  }
  output.replaceChildren();
  const note=document.createElement('p');note.className='muted small';
  note.textContent='Stable URLs use js/site-config.js. Current backend: '+(configured||'NOT SET')+(backend.origin!==configured?' — Your entered URL is different; update site-config.js before using stable URLs.':'');output.append(note);
  const title = document.createElement('h3'); title.textContent = 'Ready-to-paste links'; output.append(title);
  const endpoints = [
    ['Top 3 leaderboard', 'pages-overlay.html', 'top3'],
    ['Donation alert', 'pages-overlay.html', 'alert'],
    ['Full standings', 'pages-overlay.html', 'full'],
    ['Head-to-head battle', 'pages-overlay.html', 'battle'],
    ['Goals progress bar (toggle in operator)', 'pages-overlay.html', 'goals'],
    ['Producer scoreboard', 'pages-producer.html', null],
  ];
  for (const [name, page, graphic] of endpoints) {
    const url = new URL(page, location.href);
    // Stable URL: site-config.js supplies the server hostname.
    if (graphic) url.searchParams.set('graphic', graphic);
    if (graphic === 'top3' && document.getElementById('donation-only-top3').checked) {
      url.searchParams.set('show', 'on-donation');
    }
    const row = document.createElement('div'); row.className = 'panel';
    const label = document.createElement('strong'); label.textContent = name;
    const link = document.createElement('a'); link.textContent = url.href; link.href = url.href;
    link.target = '_blank'; link.rel = 'noopener noreferrer';
    const copy = document.createElement('button'); copy.type='button'; copy.className='btn ghost small'; copy.textContent='Copy URL';
    copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(url.href); copy.textContent='Copied'; } catch { copy.textContent='Select and copy the URL above'; }});
    row.append(label, link, copy); output.append(row);
  }
});

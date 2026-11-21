// Public hostname only. Update this ONE file when moving to a new server.
// Do not add a password, VIEW_TOKEN or API key here.
window.LIVECAST_SITE = Object.freeze({
  backendUrl: 'https://live-cast-scoreboard-production.onrender.com/',
  pagesUrl: new URL('./', location.href).href
});

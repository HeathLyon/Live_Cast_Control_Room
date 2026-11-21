'use strict';
// v1.0: keep a single transparent browser layer in vMix. Never display donor messages.
const root=document.getElementById('overlay-root');
const watermark=document.getElementById('overlay-watermark');
const params=new URLSearchParams(location.search);
const graphicId=params.get('graphic') || decodeURIComponent(location.pathname.split('/').pop());
const backend=(params.get('backend') || window.LIVECAST_SITE?.backendUrl || '').trim().replace(/\/+$/,'');
const hosted=Boolean(backend);
const preview=params.get('preview')==='1';
const combined=graphicId==='top3-alert';
const donationTop3=graphicId==='top3' && params.get('show')==='on-donation';
const token=params.get('view_token')||'';
if(hosted && !/^https:\/\/[a-z0-9.-]+(?::\d+)?$/i.test(backend))throw Error('Invalid backend origin');
const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const number=v=>Number(v).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const goalNumber=v=>Number(v).toLocaleString('en-US',{maximumFractionDigits:2});
const api=async path=>{
  const url=hosted ? backend+path.replace(/^\/api\/(overlay\/)?/,'/public/') : path;
  const r=await fetch(url,{cache:'no-store',headers:hosted?{}:token?{'X-View-Token':token}:{}});
  if(!r.ok)throw Error('Scoreboard '+r.status+' '+path);
  return r.json();
};
let graphic=null, alertConfig=null, state=null, lastRevision=-1;
let alertCursor=null, pending=[], running=false, activeServerId=null;
let goalVisibleId='', goalSignature='', goalTrigger=null, goalShowUntil=0;
function updateWatermark(){
  if(!watermark)return;
  watermark.style.display=(root.querySelector('.graphic-card,.goal-panel') && !state?.live_mode)?'':'none';
}
new MutationObserver(updateWatermark).observe(root,{childList:true});updateWatermark();
function card(config,content,kind){
  const pos=config.position||'left',scale=config.scale||'normal';
  return `<section class="graphic-card ${safe(kind)} pos-${safe(pos)} size-${safe(scale)}" style="--accent:${safe(config.accent||'#d21034')}">${content}</section>`;
}
function rankLine(m){return `<div class="graphic-row"><span class="grank">${Number(m.rank)}</span><span class="gname">${safe(m.name).toUpperCase()}</span><span class="gscore">${number(m.points)} <small>PWEN</small></span></div>`}
function ranksHTML(){
  if(!graphic?.enabled || !state)return '';
  const entries=graphic.kind==='full' ? state.ranking : state.top3;
  return card(graphic,`<p class="overlay-kicker">KLASMAN AN DIRÈK</p><h2><em>${safe(graphic.title_ht||'3 PREMYE YO')}</em></h2>${entries.map(rankLine).join('')||'<p>Pa gen done</p>'}`,graphic.kind);
}
function alertHTML(a){
  if(!alertConfig?.enabled)return '';
  if(a.kind==='summary'){
    const total=number(a.total_points||0);
    return card(alertConfig,`<p class="overlay-kicker">NOUVO SUPER CHATS</p><div class="donor-plus">${Number(a.count)} DONATIONS</div><h2>+${total} PWEN</h2><p>Multiple donations received. Updated standings appear alongside this summary.</p>`,'alert alert-entry');
  }
  const inner=`<p class="overlay-kicker">${safe(alertConfig.title_ht||'NOUVO SUPER CHAT')}</p><div class="donor-plus">+${number(a.delta_points)} PWEN</div><h2>${safe(a.cast_name).toUpperCase()}</h2><div class="alert-stats"><div><div class="alert-stat-label">NOUVO TOTAL</div><div class="alert-stat-value">${number(a.new_total)}</div></div><div><div class="alert-stat-label">POZISYON AKTYÈL</div><div class="alert-stat-value rank">#${Number(a.rank)}</div></div></div>`;
  return card(alertConfig,inner,'alert alert-entry');
}
function showDonation(a){
  root.innerHTML=((combined || donationTop3)?ranksHTML():'')+(donationTop3?'':alertHTML(a));
  updateWatermark();
}
function renderStatic(){root.innerHTML=ranksHTML();updateWatermark()}
function durationMs(){return Math.max(2000,Number(alertConfig?.duration||6)*1000)}
function playLocalQueue(){
  if(running||!pending.length||!alertConfig?.enabled)return;
  running=true;
  const alert=pending.shift();showDonation(alert);
  setTimeout(()=>{root.innerHTML='';running=false;playLocalQueue()},durationMs());
}
async function pollLocalAlerts(latest){
  if(alertCursor===null){alertCursor=latest;return;}
  if(latest<alertCursor){alertCursor=latest;pending=[];root.innerHTML='';return;}
  let n=0;
  while(latest>alertCursor && n<10){ // At most 10 pages per poll, then resume next cycle.
    const r=await api('/api/alerts?after='+alertCursor+'&limit=200');
    if(!r.alerts.length){alertCursor=latest;break;}
    for(const a of r.alerts){if(a.seq>alertCursor){alertCursor=a.seq;pending.push(a)}}
    if(r.alerts.length<200)break;
    n++;
  }
  playLocalQueue();
}
function remaining(value){
  if(!value)return '';
  const seconds=Math.max(0,Math.ceil((new Date(value).getTime()-Date.now())/1000));
  if(!Number.isFinite(seconds))return '';
  const days=Math.floor(seconds/86400),h=Math.floor(seconds%86400/3600),m=Math.floor(seconds%3600/60),s=seconds%60;
  return (days?days+'d ':'')+[h,m,s].map(v=>String(v).padStart(2,'0')).join(':');
}
function drawGoal(g){
  const labels={manual:'MANUAL GOAL',youtube_usd:'REAL YOUTUBE GOAL',donations_usd:'DONATION GOAL',cast_points:'CAST SCORE GOAL',assigned_points:'CAST POINTS GOAL'};
  const unit=['youtube_usd','donations_usd'].includes(g.metric)?'$':'';
  root.innerHTML=`<section class="goal-panel"><div class="goal-top"><div><div class="goal-subtitle">${labels[g.metric]||'GOAL'}</div><div class="goal-title">${safe(g.title)}</div></div><div class="goal-count">${unit}${goalNumber(g.current)} <small>/ ${unit}${goalNumber(g.target)}</small></div></div><div class="goal-track"><div class="goal-bar" style="width:${Math.min(100,Math.max(0,Number(g.percent)))}%"></div></div><div class="goal-footer"><span class="goal-ticker">${safe(g.ticker||'MÈSI POU SIPÒ NOU • LIVE CAST')}</span><span class="goal-clock" id="goal-clock"></span><span>${Math.round(Number(g.percent))}%</span></div></section>`;
}
async function tickGoals(){
  const g=await api('/api/overlay/goals');state={live_mode:Boolean(g.live_mode)};
  const eligible=g.visible?(g.goals||[]).filter(x=>x.enabled):[];
  const id=params.get('goal');
  const selected=id ? eligible.find(x=>x.id===id) : eligible[Math.floor(Date.now()/8000)%eligible.length];
  if(params.get('show')==='on-donation'){
    const [s,conf]=await Promise.all([api('/api/state'),api('/api/graphics/alert')]);
    if(goalTrigger!==null && s.last_alert_id>goalTrigger && conf.enabled)goalShowUntil=Date.now()+Math.max(2000,Number(conf.duration||6)*1000);
    goalTrigger=s.last_alert_id;
    if(Date.now()>=goalShowUntil){root.innerHTML='';goalSignature='';updateWatermark();return;}
  }
  if(!selected){root.innerHTML='';goalSignature='';goalVisibleId='';updateWatermark();return;}
  const signature=JSON.stringify(selected);
  if(signature!==goalSignature || selected.id!==goalVisibleId){drawGoal(selected);goalSignature=signature;goalVisibleId=selected.id}
  const timer=document.getElementById('goal-clock');
  if(timer)timer.textContent=selected.ends_at?'RETE: '+remaining(selected.ends_at):'';
  updateWatermark();
}

let battleSignature='';
async function tickBattle(config){
  const result=await api('/api/battle');
  state={live_mode:result.live_mode};
  let b=result.battle;
  if(preview&&!b){b={title:'EXAMPLE HEAD TO HEAD',status:'active',name_a:'MARCUS',name_b:'AVERY',points_a:'1250',points_b:'980',percent_a:56.05,remaining_seconds:314};}
  if(!b || config?.enabled===false || b.status==='draft' || b.status==='cancelled'){
    root.innerHTML='';battleSignature='';updateWatermark();return;
  }
  const signature=JSON.stringify(b)+JSON.stringify(config);
  if(signature===battleSignature)return;
  battleSignature=signature;
  const sec=Number(b.remaining_seconds)||0;
  const clock=String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0');
  const heading=safe(config?.title_ht||'BATAY AN DIRÈK');
  root.innerHTML=`<section class="battle-panel">
    <div class="battle-header"><span>${heading}</span><span>${safe(b.title)}</span><span>${b.status==='active'?'LIVE':b.status==='paused'?'POZ':'FINAL / REVIZYON'}</span></div>
    <div class="battle-names"><div class="battle-side"><div class="battle-name">${safe(b.name_a)}</div><div class="battle-score">${number(b.points_a)}</div><small>PWEN</small></div><div class="battle-versus">VS</div><div class="battle-side right"><div class="battle-name">${safe(b.name_b)}</div><div class="battle-score">${number(b.points_b)}</div><small>PWEN</small></div></div>
    <div class="battle-progress"><div class="battle-progress-left" style="width:${Math.max(0,Math.min(100,Number(b.percent_a)))}%"></div></div>
    <div class="battle-footer"><span>${Number(b.percent_a).toFixed(0)}%</span><span>${b.status==='active' || b.status==='paused' ? clock + ' RETE' : b.status==='final'?'REZILTA FINAL':'REZILTA PWOVIZWA'}</span><span>${Number(b.percent_b).toFixed(0)}%</span></div>
  </section>`;
  updateWatermark();
}

async function tick(){
  try{
    if(graphicId==='goals'){await tickGoals();return;}
    if(graphicId==='battle'){const cfg=await api('/api/graphics/battle');await tickBattle(cfg);return;}
    const fetchId=combined?'top3':graphicId;
    const [s,g,extra]=await Promise.all([
      api('/api/state'),
      api('/api/graphics/'+encodeURIComponent(fetchId)+(preview?'?preview=true':'')),
      (combined || donationTop3) && !preview ? api('/api/graphics/alert') : null
    ]);
    state=s;graphic=g;alertConfig=extra || g;
    if(g.kind==='battle'){await tickBattle(g);return;}
    if(preview){
      if(graphicId==='alert')showDonation({cast_name:'EXAMPLE CAST',delta_points:'25.00',new_total:'1250.00',rank:4});
      else renderStatic();
      return;
    }
    if(!combined && !donationTop3 && graphic.kind!=='alert'){
      if(s.revision!==lastRevision)renderStatic();
    }else if(hosted && s.broadcast_queue_enabled){
      // The backend is the sole playback clock; all vMix browsers see the same active item.
      const q=await api('/api/playback');
      const active=q.paused?null:q.active;
      if(active && alertConfig.enabled){
        if(activeServerId!==active.id || s.revision!==lastRevision){activeServerId=active.id;showDonation(active)}
      } else if(activeServerId!==null || root.innerHTML){activeServerId=null;root.innerHTML=''}
    }else if(!alertConfig.enabled || (donationTop3 && !graphic.enabled)){
      pending=[];root.innerHTML='';alertCursor=s.last_alert_id;
    }else{
      await pollLocalAlerts(s.last_alert_id);
    }
    lastRevision=s.revision;updateWatermark();
  }catch(err){
    // Stale graphics must not be misrepresented as current production results.
    if(graphicId==='battle'||graphicId==='goals'||graphicId==='top3-alert'||graphicId==='alert'||donationTop3){root.innerHTML='';updateWatermark()}
    else if(root.innerHTML && !root.innerHTML.includes('DEKONEKTE'))root.innerHTML+='<div class="draft-watermark">DEKONEKTE — DONE YO KA PA AJOU</div>';
  }
}
async function loop(){await tick();setTimeout(loop,1200)}
loop();

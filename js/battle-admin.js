'use strict';
// Live Cast unified producer functions. No passwords or API keys are embedded here.
(()=>{
  const $=id=>document.getElementById(id);
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const notice=(s,bad=false)=>typeof window.toast==='function'?window.toast(s,bad):alert(s);
  const http=async(path,body)=>{
    const r=await fetch(path,{method:body?'POST':'GET',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
    if(!r.ok){const e=await r.json().catch(()=>({}));throw Error(e.detail||'Request failed: HTTP '+r.status)}
    return r.json();
  };
  let currentBattle=null,remoteBattleURL='';
  const url=()=>{
    if(remoteBattleURL)return remoteBattleURL;
    const base=window.LIVECAST_SITE?.pagesUrl||'https://heathlyon.github.io/Live_Cast_Scoreboard_v0.2_Haiti/';
    return base.replace(/\/+$/,'')+'/pages-overlay.html?graphic=battle';
  };
  const opts=(select,items)=>{
    const value=select.value;select.innerHTML=items.map(m=>`<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
    if(items.some(x=>x.id===value))select.value=value;
  };
  async function refreshRoster(){
    const {cast}=await http('/api/state');
    const choices=cast.filter(m=>m.active);
    ['battle-a','battle-b','missing-cast'].forEach(id=>opts($(id),choices));
    if(choices.length>1&&$('battle-b').value===$('battle-a').value)$('battle-b').value=choices[1].id;
  }
  function buttons(b){
    const possible={draft:['start','cancel'],active:['pause','end'],paused:['resume','end'],provisional:['finalize'],final:['reopen']};
    return (possible[b.status]||[]).map(action=>`<button class="btn ${action==='start'?'primary':'ghost'} small" data-battle-action="${action}" data-battle-id="${esc(b.id)}">${action.toUpperCase()}</button>`).join('');
  }
  function present(b){
    const title=`${esc(b.name_a)} VS ${esc(b.name_b)}`;
    return `<div><strong>${esc(b.title)}</strong> · <small>${esc(b.status).toUpperCase()}</small></div>
    <p>${title}</p><div class="battle-admin-bar"><div style="width:${Math.max(0,Math.min(100,b.percent_a))}%"></div></div>
    <p><strong>${esc(b.points_a)} to ${esc(b.points_b)}</strong> · ${b.remaining_seconds}s remaining</p>
    ${b.final_result_needs_review?'<p class="danger-note">Ledger corrections differ from finalized snapshot. Reopen to revise official results.</p>':''}
    <div class="battle-action-row">${buttons(b)}</div>`;
  }
  async function loadBattles(){
    try{
      await refreshRoster();
      const [x,sys]=await Promise.all([http('/api/battles'),http('/api/system/status')]);
      remoteBattleURL=sys.graphics?.battle||'';
      currentBattle=x.current;$('battle-visible').checked=Boolean(x.visible);
      $('battle-current').innerHTML=x.current?present(x.current):'<p class="muted">No battle has started yet. Create one below.</p>';
      $('battle-history').innerHTML=x.battles.map(b=>`<div class="battle-item">${present(b)}</div>`).join('')||'<p class="muted">No battles created yet.</p>';
      $('battle-air-link').href=url();
      document.querySelectorAll('[data-battle-action]').forEach(el=>el.addEventListener('click',async()=>{
        const action=el.dataset.battleAction,id=el.dataset.battleId;
        let reason='';if(['finalize','reopen','cancel'].includes(action)){
          reason=prompt('Reason for '+action+' (minimum 8 characters):','Producer approved '+action)??'';
          if(reason.length<8)return;
        }
        if(!confirm('Confirm '+action.toUpperCase()+' for this battle?'))return;
        try{await http('/api/battles/'+encodeURIComponent(id)+'/action',{action,reason});notice('Battle '+action+' recorded.');await loadBattles()}
        catch(err){notice(err.message,true)}
      }));
    }catch(err){$('battle-current').textContent='Battle service unavailable: '+err.message;notice(err.message,true)}
  }
  window.loadBattles=loadBattles;
  $('battle-visible').addEventListener('change',async e=>{
    try{
      const r=await fetch('/api/battles/visibility',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({visible:e.target.checked})});
      if(!r.ok)throw Error('Visibility change rejected');notice(e.target.checked?'Battle graphic enabled on air.':'Battle graphic hidden on air.');
    }catch(err){notice(err.message,true);await loadBattles()}
  });
  $('battle-refresh').addEventListener('click',loadBattles);
  $('battle-copy-url').addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(url());notice('Battle URL copied for vMix.')}catch{prompt('Copy URL:',url())}
  });
  $('battle-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const title=$('battle-title').value.trim(),cast_a=$('battle-a').value,cast_b=$('battle-b').value;
    const duration_seconds=Number($('battle-duration').value)*60;
    if(cast_a===cast_b){notice('Select two different cast members',true);return}
    try{await http('/api/battles',{title,cast_a,cast_b,duration_seconds});notice('Battle draft created. Start it when ready.');await loadBattles()}
    catch(err){notice(err.message,true)}
  });
  const shortMoney=v=>'$'+(Number(v)/1e6).toFixed(2);
  async function loadMissingReports(){
    try{
      await refreshRoster();
      const [r,h]=await Promise.all([http('/api/missing-reports?status=all'),http('/api/data/history?status=pending&source=youtube&limit=100')]);
      $('missing-list').innerHTML=r.items.map(x=>{
        const dup=x.potential_duplicates||[];
        return `<div class="missing-item"><strong>${esc(x.donor)}</strong> ${shortMoney(x.amount_micros)} → ${esc(x.cast_id)} · ${esc(x.status)}<br>
          <small>${esc(x.published_at)} · Reported by ${esc(x.created_by)} · <code>${esc(x.id)}</code></small>
          <p><strong>Evidence:</strong> ${esc(x.evidence)}</p>
          ${dup.length?'<p class="danger-note">Possible duplicate(s): '+dup.map(y=>'<code>'+esc(y.id)+'</code>').join(', ')+'</p>':''}
          ${x.status==='pending'?`<div class="button-row"><button class="btn primary small" data-report-decision="approve" data-report-id="${esc(x.id)}">Approve verified</button><button class="btn danger small" data-report-decision="reject" data-report-id="${esc(x.id)}">Reject</button></div>`:''}</div>`;
      }).join('')||'<p class="muted small">No missing donation reports.</p>';
      $('duplicates-list').innerHTML=h.items.filter(x=>x.status==='possible_duplicate').map(x=>`<div class="missing-item"><b>${esc(x.donor)}</b> ${shortMoney(x.amount_micros)} · <code>${esc(x.id)}</code><br><small>Use the matching approved manual donation ID from the donation history.</small><div class="button-row"><button class="btn ghost small" data-reconcile-id="${esc(x.id)}">Reconcile</button></div></div>`).join('')||'<p class="muted small">No potential double-counted arrivals in the latest 100 unassigned YouTube records.</p>';
      document.querySelectorAll('[data-report-decision]').forEach(el=>el.addEventListener('click',async()=>{
        const action=el.dataset.reportDecision,report=el.dataset.reportId;
        const reason=prompt('Audit reason for '+action+':','Verified against original receipt and account records')||'';
        if(reason.length<8)return;
        const acknowledge_duplicates=action==='approve'&&confirm('Have you reviewed possible duplicate events? OK acknowledges the duplicate check.');
        if(!confirm('Apply '+action+' to '+report+'?'))return;
        try{await http('/api/missing-reports/'+encodeURIComponent(report)+'/decision',{action,reason,acknowledge_duplicates});notice('Missing-donation report '+action+'d.');await loadMissingReports()}
        catch(err){notice(err.message,true)}
      }));
      document.querySelectorAll('[data-reconcile-id]').forEach(el=>el.addEventListener('click',async()=>{
        const manual_id=prompt('Matching manual donation ID (manual:claim-...):')||'';
        if(!manual_id)return;
        const keep=prompt('Which is the authoritative record? Type youtube or manual:','youtube')||'';
        if(!['youtube','manual'].includes(keep))return;
        const reason=prompt('Reconciliation reason:','Compared receipt, event ID and timestamps')||'';
        if(reason.length<8)return;
        try{await http('/api/reconciliation/'+encodeURIComponent(el.dataset.reconcileId),{manual_id,keep,reason});notice('Duplicate pair reconciled.');await loadMissingReports()}
        catch(err){notice(err.message,true)}
      }));
    }catch(err){$('missing-list').textContent='Missing donation service unavailable: '+err.message}
  }
  window.loadMissingReports=loadMissingReports;
  $('missing-refresh').addEventListener('click',loadMissingReports);
  $('missing-form').addEventListener('submit',async e=>{
    e.preventDefault();
    let published_at;
    try{published_at=new Date($('missing-time').value).toISOString()}
    catch{notice('Select the original payment time',true);return}
    const record={donor:$('missing-donor').value,amount:$('missing-amount').value,
        cast_id:$('missing-cast').value,published_at,evidence:$('missing-evidence').value,
        message:$('missing-message').value,external_event_id:$('missing-event-id').value};
    try{const r=await http('/api/missing-reports',record);notice('Report '+r.id+' saved for verification'+(r.potential_duplicates.length?' — possible duplicates detected':''));$('missing-form').reset();await loadMissingReports()}
    catch(err){notice(err.message,true)}
  });
})();

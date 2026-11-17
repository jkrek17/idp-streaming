"""Renders player_values.html: a self-contained ranking board (data embedded as JSON).
Mode slider, horizon, position/flex filters and VORP are computed live in the browser."""
from __future__ import annotations
import json

TEMPLATE = r"""<title>IBL Player Board</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one sticky control rail over a dense ranking sheet; detail opens inline under a row. */
:root{
  --bg:#f5f7f3; --panel:#ffffff; --fg:#16211b; --muted:#5d6b62; --line:#dbe2da; --soft:#eef2ec;
  --turf:#1d6b47; --turf-soft:#d8eadf; --gold:#b8770f; --gold-soft:#f5e6c8; --bad:#b4442f; --bad-soft:#f6dcd5;
  --display:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;
  --body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f1512; --panel:#151d18; --fg:#e4ebe6; --muted:#93a198; --line:#28332c; --soft:#1b241f;
  --turf:#5cc28f; --turf-soft:#1d3a2b; --gold:#e3a645; --gold-soft:#3a2d15; --bad:#e2775f; --bad-soft:#3d211b; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f1512; --panel:#151d18; --fg:#e4ebe6; --muted:#93a198; --line:#28332c; --soft:#1b241f;
  --turf:#5cc28f; --turf-soft:#1d3a2b; --gold:#e3a645; --gold-soft:#3a2d15; --bad:#e2775f; --bad-soft:#3d211b; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:14px;line-height:1.45}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
.wrap{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 48px;max-width:1280px;margin:0 auto}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:8px 24px;margin-bottom:14px}
h1{font-family:var(--display);font-weight:700;font-size:34px;letter-spacing:.01em;margin:0;line-height:1;text-wrap:balance}
h1 span{color:var(--turf)}
.sub{color:var(--muted);font-size:13px}
.rail{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding-block:10px;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:10px}
.row{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--panel)}
.seg button{font:500 13px var(--body);color:var(--muted);background:none;border:0;padding:6px 12px;cursor:pointer;border-right:1px solid var(--line)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}
.seg button:focus-visible,.chip:focus-visible,input:focus-visible,th button:focus-visible,select:focus-visible{outline:2px solid var(--turf);outline-offset:2px}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600}
.mode{display:flex;align-items:center;gap:10px;flex:1 1 300px;min-width:0}
.mode input{flex:1;min-width:120px;accent-color:var(--turf)}
.mode .end{font-size:12px;font-weight:600;white-space:nowrap}
.mode .end.c{color:var(--turf)} .mode .end.g{color:var(--gold)}
#modeName{font-family:var(--mono);font-size:12px;min-width:12ch;color:var(--fg)}
input[type=search],select{font:13px var(--body);color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
input[type=search]{width:180px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font:600 12px var(--body);padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--muted);cursor:pointer}
.chip[aria-pressed="true"]{border-color:var(--turf);color:var(--turf);background:var(--turf-soft)}
.note{font-size:12px;color:var(--muted);margin:10px 0 0;max-width:80ch}
.tablewrap{overflow-x:auto;margin-top:6px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
table{border-collapse:collapse;width:100%;min-width:900px;font-variant-numeric:tabular-nums}
th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap;position:sticky;top:0;background:var(--panel)}
th.l,td.l{text-align:left}
th button{all:unset;cursor:pointer}
th button[data-active="true"]{color:var(--fg)}
td{padding:7px 8px;border-bottom:1px solid var(--soft);text-align:right;white-space:nowrap;vertical-align:middle}
tr.p{cursor:pointer} tr.p:hover td{background:var(--soft)}
tr.mine td:first-child{box-shadow:inset 3px 0 0 var(--turf)}
tr.tier td{padding:3px 10px;font:600 10px var(--body);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);background:var(--bg);text-align:left}
.rk{font-family:var(--mono);color:var(--muted);width:3ch}
.nm{font-weight:600}
.tm{font-family:var(--mono);font-size:11px;color:var(--muted);margin-left:6px}
.pill{display:inline-block;font-size:10px;font-weight:600;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:1px}
.own{background:var(--soft);color:var(--muted)} .fa{background:var(--turf-soft);color:var(--turf)} .me{background:var(--turf);color:var(--panel)}
.inj{background:var(--bad-soft);color:var(--bad)}
.num{font-family:var(--mono)}
.big{font-family:var(--mono);font-weight:500;font-size:14px}
.pos{font-family:var(--mono);font-size:12px;color:var(--muted)}
.vorp.pos-v{color:var(--turf)} .vorp.neg{color:var(--bad)}
.range{width:124px}
.range svg{display:block;width:120px;height:18px}
.prob{display:inline-flex;align-items:center;gap:6px;justify-content:flex-end}
.prob i{display:inline-block;height:6px;border-radius:3px;background:var(--turf)}
.prob.b i{background:var(--gold)}
.use{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
.up{color:var(--turf)} .dn{color:var(--bad)}
.spark svg{display:block;width:80px;height:22px}
.detail td{background:var(--soft);white-space:normal;text-align:left;padding:12px 16px}
.dgrid{position:sticky;left:16px;max-width:min(1100px,calc(100vw - 72px));display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px 24px}
.dgrid h4{margin:0 0 4px;font:600 11px var(--body);text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.dgrid dl{display:grid;grid-template-columns:auto auto;gap:2px 12px;margin:0;font-size:13px}
.dgrid dd{margin:0;font-family:var(--mono);text-align:right}
details.method{margin-top:22px;border-top:1px solid var(--line);padding-top:12px}
details.method summary{cursor:pointer;font-family:var(--display);font-size:20px;font-weight:600}
details.method p,details.method li{max-width:78ch;color:var(--fg)}
details.method pre{font:11px/1.4 var(--mono);overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;color:var(--fg)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:12px;color:var(--muted);margin-top:8px}
.legend svg{vertical-align:middle}
@media (max-width:640px){h1{font-size:28px} input[type=search]{width:100%}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="wrap">
<header>
  <div>
    <h1>IBL <span>Player Board</span></h1>
    <div class="sub" id="sub"></div>
  </div>
  <div class="sub" id="gen"></div>
</header>
<div class="rail">
  <div class="row">
    <div class="seg" role="group" aria-label="Player pool" id="pool">
      <button id="pool-offense" data-v="offense" aria-pressed="true">Offense</button>
      <button id="pool-idp" data-v="idp" aria-pressed="false">IDP</button>
    </div>
    <div class="seg" role="group" aria-label="Time horizon" id="hz">
      <button id="hz-w" data-v="w" aria-pressed="false">This week</button>
      <button id="hz-ros" data-v="ros" aria-pressed="true">Rest of season</button>
      <button id="hz-po" data-v="po" aria-pressed="false">Playoffs</button>
    </div>
    <div class="chips" id="pos" role="group" aria-label="Position"></div>
  </div>
  <div class="row">
    <div class="mode">
      <span class="end c">Consistency</span>
      <input type="range" id="lam" min="-1" max="1" step="0.25" value="0" aria-label="Consistency to ceiling">
      <span class="end g">Ceiling</span>
      <span id="modeName"></span>
    </div>
    <select id="own" aria-label="Ownership filter">
      <option value="all">All players</option>
      <option value="fa">Free agents</option>
      <option value="mine">My team</option>
      <option value="owned">Rostered</option>
    </select>
    <input type="search" id="q" placeholder="Find a player" aria-label="Find a player">
  </div>
</div>
<p class="note" id="explain"></p>
<div class="legend">
  <span><svg width="60" height="12"><rect x="4" y="4" width="52" height="4" rx="2" fill="var(--line)"></rect><rect x="16" y="3" width="28" height="6" rx="3" fill="var(--turf-soft)" stroke="var(--turf)"></rect><rect x="29" y="1" width="2" height="10" fill="var(--fg)"></rect></svg> 10th to 90th percentile, box 25th to 75th, tick = projection</span>
  <span>Value = mode score above the best free agents at the position</span>
  <span>Usage arrows compare the last ~3 weeks with the longer trend</span>
</div>
<div class="tablewrap"><table>
  <thead><tr id="thead"></tr></thead>
  <tbody id="tb"></tbody>
</table></div>
<details class="method">
  <summary>How the model works</summary>
  <ul>
    <li><b>Data.</b> Every NFL player-game from 2018 to now (nflverse), scored with this league's settings. 2018 only feeds priors; training starts in 2019.</li>
    <li><b>Usage first.</b> Snap share, target share, carry share, red-zone shares, air-yards share and pass-attempt share on offense; snap share, tackles per opponent play, and sack, QB-hit, TFL and pass-defended rates for IDP. Each is a recency-weighted rate (8-week and 3-week half-lives; last season counts about a third) pulled toward the position average by empirical Bayes. The pull is sized from how much players truly differ, so a two-game spike moves a player less than a ten-game trend.</li>
    <li><b>Consistency.</b> Over each player's last 16 games: spread of weekly points, 20th and 80th percentile games, and shrunk rates of start-worthy, boom and bust weeks.</li>
    <li><b>Context.</b> Vegas implied team total, spread, home, rest, dome and what the opponent allows to the position. Weeks without odds use team scoring strength.</li>
    <li><b>Models.</b> Gradient-boosted trees (LightGBM), one set for offense and one for IDP: a mean projection, five quantiles (10/25/50/75/90) and two classifiers for P(start-worthy week) and P(boom week), calibrated with isotonic regression on a held-out season. Injury and roster status mix in a chance of zero.</li>
    <li><b>Modes.</b> Consistency blends the projection toward the 25th percentile; Ceiling blends it toward the 90th. Value is that score minus the average of the three best free agents at the position, from the league rosters.</li>
    <li><b>Start / boom lines.</b> QB 17 / 25, RB 10 / 20, WR 10 / 20, TE 7 / 15, K 8 / 13, DL 5 / 10, LB 7 / 12, DB 6 / 11 points.</li>
  </ul>
  <pre id="bt"></pre>
</details>
</div>
<script>
const DATA = __DATA__;
const POS = {offense:["QB","RB","WR","TE","K"], idp:["DL","LB","DB"]};
const FLEX = {offense:{label:"W/R/T", pos:["RB","WR","TE"]}, idp:{label:"D slot", pos:["DL","LB","DB"]}};
const S = {pool:"offense", hz:"ros", pos:"ALL", lam:0, own:"all", q:"", sort:null, open:null};
try{const s=JSON.parse(localStorage.getItem("iblboard")||"{}"); Object.assign(S, s, {open:null});}catch(e){}
const $=id=>document.getElementById(id);
const fmt=(v,d=1)=>v==null||isNaN(v)?"–":v.toFixed(d);
const pct=v=>v==null?"–":Math.round(v*100)+"%";
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function hzVals(p){
  if(S.hz==="w") return p.w_mean==null?null:{mean:p.w_mean,q10:p.w_q10,q25:p.w_q25,q50:p.w_q50,q75:p.w_q75,q90:p.w_q90,ps:p.w_p_start,pb:p.w_p_boom,g:1};
  const k=S.hz; const g=p[k+"_games"]||0; if(!g) return null;
  // ROS / playoff: totals; range bar shows per-game average 25th..90th
  return {mean:p[k+"_mean"],q25:p[k+"_q25"],q90:p[k+"_q90"],ps:p.ros_p_start,pb:p.ros_p_boom,g};
}
function score(v,lam){ if(!v) return null; return lam<0? v.mean+(-lam)*0.5*(v.q25-v.mean) : v.mean+lam*0.5*(v.q90-v.mean); }
function modeName(l){ if(l<=-0.99) return "full floor"; if(l<0) return "lean floor"; if(l===0) return "balanced"; if(l<0.99) return "lean ceiling"; return "full ceiling"; }

function compute(){
  const pool=DATA.players.filter(p=>p.pool===S.pool);
  const rows=[];
  for(const p of pool){ const v=hzVals(p); const sc=score(v,S.lam); rows.push({p,v,sc}); }
  // replacement = avg of 3 best unrostered at the position (fallback: 13th-15th by score)
  const haveOwners=pool.some(p=>p.owner);
  const repl={};
  for(const pos of POS[S.pool]){
    const c=rows.filter(r=>r.p.pos===pos && r.sc!=null && (!haveOwners || !r.p.owner)).map(r=>r.sc).sort((a,b)=>b-a);
    const pick=haveOwners? c.slice(0,3) : c.slice(12,15);
    repl[pos]=pick.length? pick.reduce((a,b)=>a+b,0)/pick.length : 0;
  }
  for(const r of rows){ r.vorp=r.sc==null?null:r.sc-repl[r.p.pos]; }
  const byPos={};
  for(const pos of POS[S.pool]){ rows.filter(r=>r.p.pos===pos&&r.sc!=null).sort((a,b)=>b.sc-a.sc).forEach((r,i)=>r.posRank=i+1); }
  rows.filter(r=>r.sc!=null).sort((a,b)=>b.vorp-a.vorp).forEach((r,i)=>r.poolRank=i+1);
  return {rows,repl};
}

function filterRows(rows){
  let out=rows.filter(r=>r.sc!=null);
  if(S.pos==="FLEX") out=out.filter(r=>FLEX[S.pool].pos.includes(r.p.pos));
  else if(S.pos==="LBSLOT") out=out.filter(r=>r.p.lb_elig);
  else if(S.pos!=="ALL") out=out.filter(r=>r.p.pos===S.pos);
  if(S.own==="fa") out=out.filter(r=>!r.p.owner);
  if(S.own==="mine") out=out.filter(r=>r.p.mine);
  if(S.own==="owned") out=out.filter(r=>r.p.owner);
  if(S.q){const q=S.q.toLowerCase(); out=out.filter(r=>r.p.name.toLowerCase().includes(q)||String(r.p.team).toLowerCase()===q);}
  const key=S.sort||((S.pos==="ALL")?"vorp":"sc");
  const val=r=>key==="vorp"?r.vorp:key==="sc"?r.sc:key==="ps"?r.v.ps:key==="pb"?r.v.pb:key==="name"?0:r.sc;
  out.sort((a,b)=>val(b)-val(a));
  return {out,key};
}

function rangeSvg(v){
  const W=120,H=18;
  const per=S.hz==="w"?1:v.g;
  const lo=S.hz==="w"?v.q10:v.q25/per, hi=v.q90/per, m=v.mean/per;
  const q25=v.q25/per, q75=S.hz==="w"?v.q75:null;
  const max=SCALE[S.pool][S.hz==="w"?"w":"g"];
  const x=t=>Math.max(1,Math.min(W-1,4+(W-8)*Math.max(0,t)/max));
  let s=`<svg viewBox="0 0 ${W} ${H}" aria-hidden="true"><rect x="4" y="7" width="${W-8}" height="4" rx="2" fill="var(--line)"></rect>`;
  s+=`<rect x="${x(lo)}" y="8" width="${Math.max(1,x(hi)-x(lo))}" height="2" fill="var(--muted)"></rect>`;
  const b1=x(q25), b2=q75!=null?x(q75):x(m);
  s+=`<rect x="${b1}" y="5" width="${Math.max(2,b2-b1)}" height="8" rx="3" fill="var(--turf-soft)" stroke="var(--turf)" stroke-width="1"></rect>`;
  s+=`<rect x="${x(m)-1}" y="2" width="2" height="14" fill="var(--fg)"></rect></svg>`;
  return s;
}
function spark(log){
  const W=80,H=22, n=log.length; if(!n) return "";
  const vals=log.filter(v=>v!=null); const mx=Math.max(1,...vals);
  const bw=(W-2)/n; let s=`<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
  log.forEach((v,i)=>{ if(v==null){ s+=`<rect x="${1+i*bw+bw*0.35}" y="${H-2}" width="${bw*0.3}" height="1" fill="var(--line)"></rect>`; return;}
    const h=Math.max(1,(H-3)*Math.max(0,v)/mx); s+=`<rect x="${1+i*bw+1}" y="${H-1-h}" width="${Math.max(1,bw-2)}" height="${h}" rx="1" fill="${i===n-1?'var(--turf)':'var(--muted)'}" opacity="${i===n-1?1:0.55}"></rect>`;});
  return s+"</svg>";
}
function trend(a,b){ if(a==null||b==null) return ""; const d=b-a; if(Math.abs(d)<0.02*Math.max(a,0.05)*2) return ""; return d>0?'<span class="up">▲</span>':'<span class="dn">▼</span>'; }
function usage(p){
  const sp=p.snap!=null?pct(p.snap)+trend(p.snap,p.snap_s):"–";
  switch(p.pos){
    case "QB": return `snap ${sp} · rush ${pct(p.car_sh)}`;
    case "RB": return `snap ${sp} · car ${pct(p.car_sh)}${trend(p.car_sh,p.car_sh_s)} · tgt ${pct(p.tgt_sh)}`;
    case "WR": case "TE": return `snap ${sp} · tgt ${pct(p.tgt_sh)}${trend(p.tgt_sh,p.tgt_sh_s)} · rz ${pct(p.rz_tgt_sh)}`;
    case "K": return `FGA/g ${fmt(p.fga_g)} · FG yds/g ${fmt(p.fgyd_g,0)}`;
    default: return `snap ${sp} · tkl ${fmt((p.tkl_sh||0)*100)}${trend(p.tkl_sh,p.tkl_sh_s)}/100 plays`;
  }
}
function ownPill(p){
  let s=p.mine?'<span class="pill me">MINE</span>':p.owner?`<span class="pill own" title="${esc(p.owner)}">${esc(p.owner.length>14?p.owner.slice(0,13)+"…":p.owner)}</span>`:(DATA.players.some(x=>x.owner)?'<span class="pill fa">FA</span>':"");
  const st=p.ystatus||""; if(st) s+=`<span class="pill inj">${esc(st)}</span>`;
  if(S.hz==="w" && p.w_avail!=null && p.w_avail<0.95 && !st) s+=`<span class="pill inj">${Math.round(p.w_avail*100)}% to play</span>`;
  return s;
}
function detail(r){
  const p=r.p, v=r.v, w=p;
  const isIdp=p.pool==="idp";
  const use=isIdp?[["Snap share",pct(p.snap)],["Last 3 wks",pct(p.snap_s)],["Tackles / 100 opp plays",fmt((p.tkl_sh||0)*100)],["Solo / 100 plays",fmt((p.solo_sh||0)*100)],["Sacks / 100 snaps",fmt((p.sack_rate||0)*100,2)],["QB hits / 100 snaps",fmt((p.hit_rate||0)*100,2)],["TFL / 100 snaps",fmt((p.tfl_rate||0)*100,2)],["PD / 100 snaps",fmt((p.pd_rate||0)*100,2)]]
    : p.pos==="K"?[["FG att / game",fmt(p.fga_g)],["FG yards / game",fmt(p.fgyd_g,0)]]
    : [["Snap share",pct(p.snap)],["Last 3 wks",pct(p.snap_s)],["Target share",pct(p.tgt_sh)],["Air-yards share",pct(p.ay_sh)],["Carry share",pct(p.car_sh)],["RZ target share",pct(p.rz_tgt_sh)],["RZ carry share",pct(p.rz_car_sh)],["Exp. targets / g",fmt(p.exp_tgt)],["Exp. carries / g",fmt(p.exp_car)]];
  const cons=[["Points / game (decayed)",fmt(p.ppg)],["Last 16: avg",fmt(p.roll_mean)],["Last 16: 20th pct game",fmt(p.roll_q20)],["Last 16: 80th pct game",fmt(p.roll_q80)],["Weekly spread (sd)",fmt(p.roll_sd)],["Start-worthy weeks",pct(p.rate_start)],["Boom weeks",pct(p.rate_boom)],["Bust weeks",pct(p.rate_bust)]];
  const wk=p.w_mean!=null?[["Opponent",(p.w_home?"vs ":"@ ")+(p.w_opp||"")],["Implied team total",fmt(p.w_implied)],["Projection",fmt(p.w_mean)],["10th / 90th pct",fmt(p.w_q10)+" / "+fmt(p.w_q90)],["P(start-worthy)",pct(p.w_p_start)],["P(boom)",pct(p.w_p_boom)],["Chance to play",pct(p.w_avail)]]:[["This week","bye"]];
  const ros=[["Games left",p.ros_games],["ROS projection",fmt(p.ros_mean)],["ROS floor (25th sums)",fmt(p.ros_q25)],["ROS ceiling (90th sums)",fmt(p.ros_q90)],["Playoff wks 15-17",fmt(p.po_mean)]];
  const dl=a=>"<dl>"+a.map(([k,v])=>`<dt>${k}</dt><dd>${v}</dd>`).join("")+"</dl>";
  return `<div class="dgrid"><div><h4>Usage</h4>${dl(use)}</div><div><h4>Consistency</h4>${dl(cons)}</div><div><h4>Week ${DATA.meta.week}</h4>${dl(wk)}</div><div><h4>Outlook</h4>${dl(ros)}</div></div>`
   + `<div class="note">Game log this season (weeks 1-${DATA.meta.week-1}): ${p.log.map(v=>v==null?"–":v).join(", ")}${p.owner?` · Owner: ${esc(p.owner)}`:""}</div>`;
}

let SCALE={};
function scales(){
  for(const pool of ["offense","idp"]){
    const ps=DATA.players.filter(p=>p.pool===pool);
    const q=a=>{a=a.filter(x=>x!=null).sort((x,y)=>x-y); return a[Math.floor(a.length*0.99)]||1;};
    SCALE[pool]={w:q(ps.map(p=>p.w_q90)), g:q(ps.map(p=>p.ros_games?p.ros_q90/p.ros_games:null))};
  }
}

function render(){
  try{localStorage.setItem("iblboard",JSON.stringify({pool:S.pool,hz:S.hz,pos:S.pos,lam:S.lam,own:S.own}));}catch(e){}
  document.querySelectorAll("#pool button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.v===S.pool));
  document.querySelectorAll("#hz button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.v===S.hz));
  const chips=[["ALL",S.pool==="offense"?"All (value)":"All IDP (value)"],["FLEX",FLEX[S.pool].label]].concat(S.pool==="idp"?[["LBSLOT","LB slot"]]:[]).concat(POS[S.pool].map(p=>[p,p]));
  if(!chips.some(c=>c[0]===S.pos)) S.pos="ALL";
  $("pos").innerHTML=chips.map(([k,l])=>`<button class="chip" id="pos-${k}" data-v="${k}" aria-pressed="${S.pos===k}">${l}</button>`).join("");
  $("lam").value=S.lam; $("modeName").textContent=modeName(+S.lam); $("own").value=S.own;
  const {rows,repl}=compute(); const {out,key}=filterRows(rows);
  const hzName={w:`Week ${DATA.meta.week}`,ros:`Weeks ${DATA.meta.weeks_left[0]}-${DATA.meta.weeks_left.at(-1)}`,po:"Weeks 15-17"}[S.hz];
  const per=S.hz==="w"?"pts":"total pts";
  $("explain").textContent=`${hzName}, ${modeName(+S.lam)} mode. Score is ${S.lam<0?"the projection pulled toward a bad-week (25th percentile) outcome":S.lam>0?"the projection pulled toward a big-week (90th percentile) outcome":"the mean projection"} in ${per}. Replacement level: `+POS[S.pool].map(p=>`${p} ${fmt(repl[p])}`).join(", ")+".";
  const cols=[["rk","#","l"],["name","Player","l"],["pr","Pos rk",""],["sc",S.hz==="w"?"Score":"Score",""],["vorp","Value",""],["rg",S.hz==="w"?"Range":"Range / game",""],["ps","P(start)",""],["pb","P(boom)",""],["use","Usage","l"],["sp","2026 log","l"]];
  $("thead").innerHTML=cols.map(([k,l,c])=>{const sortable=["sc","vorp","ps","pb"].includes(k);
    return `<th class="${c}">${sortable?`<button id="sort-${k}" data-k="${k}" data-active="${key===k}">${l}${key===k?" ↓":""}</button>`:l}</th>`;}).join("");
  // tiers: break on gaps in the sort key that are large relative to the typical gap among the top rows
  const vals=out.map(r=>key==="vorp"?r.vorp:key==="sc"?r.sc:null);
  const gaps=[]; for(let i=1;i<Math.min(vals.length,60);i++) if(vals[i]!=null) gaps.push(vals[i-1]-vals[i]);
  const mg=gaps.length? gaps.slice().sort((a,b)=>a-b)[Math.floor(gaps.length/2)] : 0;
  let tier=1; const html=[];
  const lim=Math.min(out.length,250);
  for(let i=0;i<lim;i++){
    const r=out[i], p=r.p, v=r.v;
    if(vals[0]!=null && i>0 && vals[i]!=null && (vals[i-1]-vals[i])>Math.max(3.2*mg, S.hz==="w"?0.6:3)){ tier++; html.push(`<tr class="tier"><td colspan="10">Tier ${tier}</td></tr>`);}
    if(i===0 && vals[0]!=null) html.push(`<tr class="tier"><td colspan="10">Tier 1</td></tr>`);
    const pb=v.pb??0, ps=v.ps??0;
    html.push(`<tr class="p${p.mine?" mine":""}" data-id="${p.player_id}" tabindex="0">
      <td class="rk l">${i+1}</td>
      <td class="l"><span class="nm">${esc(p.name)}</span><span class="tm">${esc(p.pos)} · ${esc(p.team)}${S.hz==="w"&&p.w_opp?` ${p.w_home?"v":"@"} ${esc(p.w_opp)}`:""}</span>${ownPill(p)}</td>
      <td class="pos">${p.pos}${r.posRank}</td>
      <td class="big">${fmt(r.sc)}</td>
      <td class="num vorp ${r.vorp>=0?"pos-v":"neg"}">${r.vorp>=0?"+":""}${fmt(r.vorp)}</td>
      <td class="range">${rangeSvg(v)}</td>
      <td><span class="prob"><i style="width:${Math.round(ps*40)}px"></i>${pct(ps)}</span></td>
      <td><span class="prob b"><i style="width:${Math.round(pb*40)}px"></i>${pct(pb)}</span></td>
      <td class="l use">${usage(p)}</td>
      <td class="l spark">${spark(p.log)}</td></tr>`);
    if(S.open===p.player_id) html.push(`<tr class="detail"><td colspan="10">${detail(r)}</td></tr>`);
  }
  if(!out.length) html.push(`<tr><td colspan="10" class="l" style="padding:24px;color:var(--muted)">No players match these filters. Clear the search or switch the ownership filter to All players.</td></tr>`);
  $("tb").innerHTML=html.join("");
}

function init(){
  const m=DATA.meta;
  $("sub").textContent=`Irene's Bush League · ${m.season} week ${m.week} · 12 teams · QB, 2 RB, 2 WR, TE, W/R/T, K, LB, D`;
  $("gen").textContent=`Updated ${m.generated.replace("T"," ")}${m.yahoo_file?` · rosters from ${m.yahoo_file.replace("league_rosters_","").replace(".json","")}`:""}${m.blend?" · offense blended 50/50 with the weekly model":""}`;
  $("bt").textContent=m.backtest||"";
  scales();
  $("pool").addEventListener("click",e=>{const b=e.target.closest("button"); if(!b) return; S.pool=b.dataset.v; S.sort=null; S.open=null; render();});
  $("hz").addEventListener("click",e=>{const b=e.target.closest("button"); if(!b) return; S.hz=b.dataset.v; render();});
  $("pos").addEventListener("click",e=>{const b=e.target.closest("button"); if(!b) return; S.pos=b.dataset.v; S.sort=null; render();});
  $("lam").addEventListener("input",e=>{S.lam=+e.target.value; render();});
  $("own").addEventListener("change",e=>{S.own=e.target.value; render();});
  $("q").addEventListener("input",e=>{S.q=e.target.value.trim(); render();});
  $("thead").addEventListener("click",e=>{const b=e.target.closest("button"); if(!b) return; S.sort=b.dataset.k; render();});
  const toggle=e=>{const tr=e.target.closest("tr.p"); if(!tr) return; S.open=S.open===tr.dataset.id?null:tr.dataset.id; render();};
  $("tb").addEventListener("click",toggle);
  $("tb").addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault(); toggle(e);}});
  render();
}
init();
</script>
"""


def render(payload: dict) -> str:
    js = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", js)

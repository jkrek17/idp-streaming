"""Renders player_values.html: a self-contained player board (data embedded as JSON).

Three task tabs (My lineup, Waivers, Rankings). Each player row shows one lead number, value versus the
waiver wire, and an outlook bar (likely range, replacement line, scored point). Ranking style
(Safe / Balanced / Upside), replacement level and lineup filling are computed live in the browser.
"""
from __future__ import annotations
import json

TEMPLATE = r"""<title>IBL Player Board</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: task tabs over one list of player rows; each row = who, what to do, how many points. Depth opens inline. */
:root{
  --bg:#f5f7f3; --panel:#ffffff; --fg:#16211b; --muted:#5d6b62; --faint:#8a968e; --line:#dbe2da; --soft:#eef2ec;
  --turf:#1d6b47; --turf-mid:#5f9e7c; --turf-soft:#dcebe1; --gold:#a8690a; --gold-soft:#f6e7c9; --bad:#b4442f; --bad-soft:#f6dcd5;
  --below:#b9c2bb; --tierA:#e7ede6; --tierB:#f5f7f3;
  --display:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;
  --body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f1512; --panel:#151d18; --fg:#e4ebe6; --muted:#9aa79f; --faint:#6f7c74; --line:#28332c; --soft:#1b241f;
  --turf:#62c894; --turf-mid:#3f8a64; --turf-soft:#1d3a2b; --gold:#e8ad4c; --gold-soft:#3a2d15; --bad:#e8826b; --bad-soft:#3d211b;
  --below:#46524b; --tierA:#18211c; --tierB:#0f1512; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f1512; --panel:#151d18; --fg:#e4ebe6; --muted:#9aa79f; --faint:#6f7c74; --line:#28332c; --soft:#1b241f;
  --turf:#62c894; --turf-mid:#3f8a64; --turf-soft:#1d3a2b; --gold:#e8ad4c; --gold-soft:#3a2d15; --bad:#e8826b; --bad-soft:#3d211b;
  --below:#46524b; --tierA:#18211c; --tierB:#0f1512; color-scheme:dark}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{background:var(--bg);color:var(--fg);font-family:var(--body);font-size:14px;line-height:1.45}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--bg)}
.wrap{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:16px 48px;max-width:1080px;margin:0 auto}
header{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 16px}
h1{font-family:var(--display);font-weight:700;font-size:30px;margin:0;line-height:1}
h1 span{color:var(--turf)}
.sub{color:var(--muted);font-size:12.5px}
button{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--turf);outline-offset:2px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel)}
.seg button{font:500 13px var(--body);color:var(--muted);background:none;border:0;padding:7px 12px;min-height:36px;cursor:pointer;border-right:1px solid var(--line)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--fg);color:var(--bg)}
.seg.style button[data-v="-1"][aria-pressed="true"]{background:var(--turf);color:var(--panel)}
.seg.style button[data-v="1"][aria-pressed="true"]{background:var(--gold);color:var(--panel)}
.tabs{position:sticky;top:env(safe-area-inset-top,0px);z-index:6;background:var(--bg);display:flex;gap:4px;border-bottom:1px solid var(--line);margin-top:12px}
.tabs button{background:none;border:0;padding:10px 14px;font:600 15px var(--body);color:var(--muted);cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-1px}
.tabs button[aria-selected="true"]{color:var(--fg);border-bottom-color:var(--turf)}
.bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;padding-block:10px}
.chips{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;max-width:100%}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;font:600 12.5px var(--body);padding:6px 12px;min-height:32px;border-radius:999px;border:1px solid var(--line);background:var(--panel);color:var(--muted);cursor:pointer}
.chip[aria-pressed="true"]{border-color:var(--fg);color:var(--bg);background:var(--fg)}
select,input[type=search]{font:13px var(--body);color:var(--fg);background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:7px 10px;min-height:36px}
input[type=search]{width:170px}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600}
.stylewrap{display:flex;align-items:center;gap:8px}
.listhead{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px;align-items:baseline;margin:6px 0 6px;color:var(--muted);font-size:12.5px}
.listhead b{color:var(--fg);font-weight:600}
.callouts{display:grid;gap:8px;margin:10px 0 14px}
.callout{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;display:flex;gap:10px;align-items:flex-start;font-size:13.5px}
.callout .k{flex:none;font:700 10.5px var(--body);letter-spacing:.08em;text-transform:uppercase;padding:3px 7px;border-radius:5px;background:var(--turf-soft);color:var(--turf);margin-top:1px}
.callout .k.warn{background:var(--bad-soft);color:var(--bad)}
.callout .k.info{background:var(--soft);color:var(--muted)}
.list{display:flex;flex-direction:column}
.cols,.row{display:grid;grid-template-columns:28px minmax(0,1.7fr) 64px 156px 62px 72px minmax(96px,1fr);grid-template-areas:"rk player tag bar proj val role";align-items:center;column-gap:12px}
.cols{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:600;padding:4px 12px 6px}
.cols span:nth-child(5),.cols span:nth-child(6){text-align:right}
.cols .axis{display:flex;justify-content:space-between;font-family:var(--mono);letter-spacing:0;text-transform:none;font-weight:400}
.row{padding:9px 12px;border-bottom:1px solid var(--line);background:var(--panel);cursor:pointer;position:relative;font-variant-numeric:tabular-nums;min-height:52px}
.row::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--tierband,transparent)}
.row:hover{background:var(--soft)}
.row.mine{background:color-mix(in srgb,var(--turf-soft) 55%,var(--panel))}
.row.mine::before{background:var(--turf)}
.rk{grid-area:rk;font-family:var(--mono);color:var(--faint);font-size:12px}
.pl{grid-area:player;min-width:0}
.nm{font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.meta{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.meta .own{color:var(--faint)}
.meta .fa{color:var(--turf);font-weight:600}
.meta .me{color:var(--turf);font-weight:700}
.meta .flag{color:var(--bad);font-weight:600}
.tag{grid-area:tag}
.t{display:inline-block;font:700 10.5px var(--body);letter-spacing:.06em;text-transform:uppercase;padding:3px 7px;border-radius:5px;border:1px solid currentColor;white-space:nowrap}
.t.start{background:var(--turf);border-color:var(--turf);color:var(--panel)}
.t.safe{color:var(--turf)}
.t.boom{color:var(--gold)}
.t.risky{color:var(--faint)}
.t.bench{color:var(--faint)}
.t.out{color:var(--bad)}
.ob{grid-area:bar}
.ob svg{display:block;width:156px;height:20px}
.proj{grid-area:proj;text-align:right;font-family:var(--mono);font-size:17px;font-weight:500}
.proj small{display:block;font-size:10px;color:var(--faint);font-family:var(--body);font-weight:400}
.val{grid-area:val;text-align:right;font-family:var(--mono);font-size:13px}
.val.up{color:var(--turf);font-weight:600} .val.dn{color:var(--faint)}
.val small{font-size:10px;color:var(--faint);font-weight:400}
.more{display:block;margin:12px auto 0;font:600 13px var(--body);padding:10px 18px;min-height:44px;border:1px solid var(--line);border-radius:10px;background:var(--panel);cursor:pointer}
.role{grid-area:role;font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.arr{color:var(--fg);font-weight:700}
.tierlbl{font:600 11px var(--body);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:14px 12px 6px;display:flex;gap:8px;align-items:baseline}
.tierlbl span{font-family:var(--mono);letter-spacing:0;text-transform:none;font-weight:400;color:var(--faint)}
.slot{font:700 11px var(--mono);color:var(--muted)}
.detail{background:var(--soft);border-bottom:1px solid var(--line);padding:14px 16px 16px;display:grid;gap:14px}
.summary{font-size:14px;max-width:70ch}
.dgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px 24px}
.dgrid h4{margin:0 0 6px;font:600 11px var(--body);text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.dgrid svg{display:block;max-width:100%}
.kv{display:grid;grid-template-columns:auto auto;gap:2px 14px;font-size:13px;margin:0}
.kv dd{margin:0;text-align:right;font-family:var(--mono)}
.slopes{display:flex;flex-wrap:wrap;gap:12px}
.slope{font-size:11px;color:var(--muted)}
.empty{padding:28px 12px;color:var(--muted);text-align:center;background:var(--panel);border:1px dashed var(--line);border-radius:10px}
details.how{margin-top:24px;border-top:1px solid var(--line);padding-top:12px;font-size:13.5px}
details.how summary{cursor:pointer;font-weight:600}
details.how li,details.how p{max-width:72ch}
details.how pre{font:11px/1.4 var(--mono);overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}
@media (max-width:760px){
  h1{font-size:26px}
  .cols{display:none}
  .row{grid-template-columns:30px auto minmax(0,1fr) 50px 54px;grid-template-areas:"rk player player player player" "rk tag bar proj val";row-gap:6px;column-gap:8px;padding:10px 10px 10px 12px}
  .rk{align-self:start;padding-top:3px;font-size:11px}
  .role{display:none}
  .nm{white-space:normal}
  .meta{white-space:normal}
  .ob svg{width:100%;max-width:150px}
  .proj{font-size:16px}
  .seg button,.chip,select,input[type=search],details.how summary{min-height:44px}
  .chips{mask-image:linear-gradient(90deg,#000 88%,transparent);-webkit-mask-image:linear-gradient(90deg,#000 88%,transparent);padding-right:24px}
  .tabs button{flex:1;padding:10px 6px}
  input[type=search]{width:100%}
  .bar{gap:8px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
<div class="wrap">
<header>
  <div>
    <h1>IBL <span>Player Board</span></h1>
    <div class="sub" id="sub"></div>
  </div>
  <div class="seg" role="group" aria-label="Player pool" id="pool">
    <button id="pool-offense" data-v="offense">Offense</button>
    <button id="pool-idp" data-v="idp">IDP</button>
  </div>
</header>
<nav class="tabs" role="tablist" id="tabs">
  <button role="tab" id="tab-lineup" data-v="lineup">My lineup</button>
  <button role="tab" id="tab-waivers" data-v="waivers">Waivers</button>
  <button role="tab" id="tab-rank" data-v="rank">Rankings</button>
</nav>
<div class="bar" id="controls">
  <div class="seg" role="group" aria-label="Time frame" id="hz">
    <button id="hz-w" data-v="w">This week</button>
    <button id="hz-ros" data-v="ros">Rest of season</button>
    <button id="hz-po" data-v="po">Playoffs</button>
  </div>
  <div class="stylewrap"><span class="lbl">Rank for</span>
    <div class="seg style" role="group" aria-label="Ranking style" id="style">
      <button id="st-safe" data-v="-1" title="Rank by a bad-week outcome: steady players rise">Safe floor</button>
      <button id="st-bal" data-v="0" title="Rank by the average projection">Balanced</button>
      <button id="st-up" data-v="1" title="Rank by a big-week outcome: boom players rise">Upside</button>
    </div>
  </div>
</div>
<div class="bar" id="filters">
  <div class="chips" id="pos" role="group" aria-label="Position"></div>
  <select id="own" aria-label="Whose players"></select>
  <input type="search" id="q" placeholder="Find a player" aria-label="Find a player">
</div>
<div id="main"></div>
<details class="how">
  <summary>How this works</summary>
  <ul>
    <li><b>Projected points</b> use this league's scoring. They come from each player's role (snap, target, carry, red-zone and tackle share), recent scoring, how steady he is week to week, Vegas lines and the matchup. The model trains on every NFL game since 2019.</li>
    <li><b>The bar</b> shows a player's likely range. The thin line runs from a bad week (10th percentile) to a big week (90th), and the thick part is a normal week (25th to 75th). The dot is the number used to rank him. The dashed line is replacement level (a fringe starter), so green means better than that. For rest of season and playoffs the bar shows a typical week.</li>
    <li><b>Rank for</b> moves the dot. Safe floor ranks players by a bad-but-not-awful week, Upside by a big week, and Balanced by the average. Use Safe when you are favored and Upside when you need a big week.</li>
    <li><b>Value</b> is points above a fringe starter: fill 12 teams' starting lineups, then take the next three players at the position. IDP uses one level for DL, LB and DB because the D slot takes any of them. The Waivers tab compares free agents with your own weakest starter instead, per game for rest of season.</li>
    <li><b>Projected points</b> never change with Rank for; only the order and the dot move. <b>Tags.</b> SAFE means even a bad week (25th percentile) is at replacement level. BOOM means at least a 1 in 4 chance of a big week. K and DB projections are the least reliable in testing. Big-week lines: QB 25, RB 20, WR 20, TE 15, K 13, DL 10, LB 12, DB 11 points.</li>
    <li><b>Chance to play</b> combines the injury report, Yahoo tags, IR status and missed games. It is already built into the numbers.</li>
  </ul>
  <pre id="bt"></pre>
</details>
</div>
<script>
const DATA = __DATA__;
const POS = {offense:["QB","RB","WR","TE","K"], idp:["DL","LB","DB"]};
const THR = {QB:[17,25],RB:[10,20],WR:[10,20],TE:[7,15],K:[8,13],DL:[6,12],LB:[6,12],DB:[6,12]};
const SLOTS = [["QB",["QB"]],["RB",["RB"]],["RB",["RB"]],["WR",["WR"]],["WR",["WR"]],["TE",["TE"]],["W/R/T",["RB","WR","TE"]],["K",["K"]],["LB",["LB*"]],["D",["DL","LB","DB"]]];
const HAVE_OWNERS = DATA.players.some(p=>p.owner);
const OWNERS = [...new Set(DATA.players.map(p=>p.owner).filter(Boolean))].sort();
const S = {tab:"lineup", pool:"offense", hz:{lineup:"w",waivers:"ros",rank:"ros"}, lam:0, pos:"ALL", own:"all", q:"", open:null};
try{const s=JSON.parse(localStorage.getItem("iblboard2")||"{}"); for(const k of ["tab","pool","hz","lam","pos","own"]) if(s[k]!=null) S[k]=s[k];}catch(e){}
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const f1=v=>v==null||isNaN(v)?"–":v.toFixed(1);
const pct=v=>v==null||isNaN(v)?"–":Math.round(v*100)+"%";
const sgn=v=>v==null||isNaN(v)?"–":(v>=0?"+":"−")+Math.abs(v).toFixed(1);
const short=(s,n)=>s&&s.length>n?s.slice(0,n-1)+"…":s;

/* ---------- numbers ---------- */
function hv(p,hz){
  if(hz==="w"){ if(p.w_mean==null) return null;
    return {mean:p.w_mean,q10:p.w_q10,q25:p.w_q25,q50:p.w_q50,q75:p.w_q75,q90:p.w_q90,ps:p.w_p_start,pb:p.w_p_boom,g:1,per:1}; }
  const g=p[hz+"_games"]||0; if(!g) return null;
  // totals for value and ranking; the bar divides by games (a typical week)
  return {mean:p[hz+"_mean"],q10:p[hz+"_q10"],q25:p[hz+"_q25"],q50:p[hz+"_q50"],q75:p[hz+"_q75"],q90:p[hz+"_q90"],ps:p.ros_p_start,pb:p.ros_p_boom,g,per:g};
}
const score=(v,l)=>!v?null:(l<0? v.mean+(-l)*0.5*(v.q25-v.mean) : v.mean+l*0.5*(v.q90-v.mean));
function evaluate(hz,lam){
  const rows=DATA.players.map(p=>{const v=hv(p,hz); return {p,v,sc:score(v,lam)};});
  // replacement = a fringe starter: fill 12 teams' starting slots, then average the next 3 (IDP: one level, D takes any)
  const repl={}, avg=a=>a.length?{tot:a.reduce((s,r)=>s+r.sc,0)/a.length, pg:a.reduce((s,r)=>s+r.sc/r.v.per,0)/a.length}:{tot:0,pg:0};
  const fillPool=(pool,caps,flex)=>{ const L=rows.filter(r=>r.p.pool===pool&&r.sc!=null).sort((a,b)=>b.sc-a.sc), used=new Set(), c={...caps};
    for(const r of L){ const k=pool==="idp"?(r.p.lb_elig&&c.LB>0?"LB":null):(c[r.p.pos]>0?r.p.pos:null);
      if(k){c[k]--; used.add(r); continue;} if(c[flex.slot]>0&&flex.pos.includes(r.p.pos)){c[flex.slot]--; used.add(r);} }
    return L.filter(r=>!used.has(r)); };
  const offRest=fillPool("offense",{QB:12,RB:24,WR:24,TE:12,K:12,FLEX:12},{slot:"FLEX",pos:["RB","WR","TE"]});
  for(const pos of POS.offense) repl[pos]=avg(offRest.filter(r=>r.p.pos===pos).slice(0,3));
  const idpRest=fillPool("idp",{LB:12,D:12},{slot:"D",pos:POS.idp});
  const il=avg(idpRest.slice(0,3)); for(const pos of POS.idp) repl[pos]=il;
  for(const r of rows){ if(r.sc==null) continue; r.vorp=r.sc-repl[r.p.pos].tot; r.rpg=repl[r.p.pos].pg; }
  for(const pos in repl){ rows.filter(r=>r.p.pos===pos&&r.sc!=null).sort((a,b)=>b.sc-a.sc).forEach((r,i)=>r.posRank=i+1); }
  return {rows,repl};
}
function tagFor(r){
  const v=r.v; if(!v) return "";
  const per=v.per, rp=r.rpg;
  if(S.hz[S.tab]==="w" && r.p.w_avail!=null && r.p.w_avail<0.5) return '<span class="t out">OUT?</span>';
  if(v.pb>=0.25) return '<span class="t boom">Boom</span>';
  if(v.q25/per>=rp && v.mean/per>rp*1.15) return '<span class="t safe">Safe</span>';
  return "";
}
/* lineup: fill slots greedily by score from a set of rows */
function fillLineup(rows){
  const left=rows.filter(r=>r.sc!=null).sort((a,b)=>b.sc-a.sc); const out=[];
  const dedicated=SLOTS.map((s,i)=>({s,i})).filter(o=>o.s[1].length===1);
  const flex=SLOTS.map((s,i)=>({s,i})).filter(o=>o.s[1].length>1);
  const used=new Set(), slotOf={};
  for(const {s,i} of dedicated){ const r=left.find(r=>!used.has(r)&&(s[1][0]==="LB*"?r.p.lb_elig:r.p.pos===s[1][0])); if(r){used.add(r); slotOf[i]=r;} }
  for(const {s,i} of flex){ const r=left.find(r=>!used.has(r)&&s[1].includes(r.p.pos)); if(r){used.add(r); slotOf[i]=r;} }
  SLOTS.forEach((s,i)=>out.push({slot:s[0],elig:s[1],r:slotOf[i]||null}));
  const bench=rows.filter(r=>!used.has(r));
  return {starters:out,bench};
}

/* ---------- marks ---------- */
let SC={};
function scaleFor(hz,rows){
  const a=rows.map(r=>r.v&&(r.v.q90/r.v.per)).filter(x=>x!=null).sort((x,y)=>x-y);
  return Math.max(4,a[Math.floor(a.length*0.95)]||10);
}
function outlook(r,max,W=156){
  const v=r.v, per=v.per, H=20, x=t=>4+(W-8)*Math.max(0,Math.min(1,t/max));
  const lo=(v.q10!=null?v.q10:v.q25)/per, q25=v.q25/per, q75=(v.q75!=null?v.q75:v.mean+(v.mean-v.q25)*0.9)/per, hi=v.q90/per, dot=r.sc/per, rp=r.rpg;
  const xr=x(rp);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="likely ${f1(lo)} to ${f1(hi)}, ranked at ${f1(dot)}">`;
  s+=`<rect x="4" y="9" width="${W-8}" height="2" rx="1" fill="var(--line)"></rect>`;
  // whisker 10..90 split at replacement
  const seg=(a,b,y,h,c)=>{ if(b<=a) return ""; return `<rect x="${a}" y="${y}" width="${b-a}" height="${h}" rx="${h/2}" fill="${c}"></rect>`; };
  s+=seg(x(lo),Math.min(x(hi),xr),9,2,"var(--below)")+seg(Math.max(x(lo),xr),x(hi),9,2,"var(--turf-mid)");
  s+=seg(x(q25),Math.min(x(q75),xr),5,10,"var(--below)")+seg(Math.max(x(q25),xr),x(q75),5,10,"var(--turf)");
  s+=`<line x1="${xr}" x2="${xr}" y1="1" y2="19" stroke="var(--fg)" stroke-width="1" stroke-dasharray="2 2" opacity=".55"></line>`;
  s+=`<circle cx="${x(dot)}" cy="10" r="4.5" fill="var(--fg)" stroke="var(--panel)" stroke-width="1.5"></circle></svg>`;
  return s;
}
function roleText(p){
  const arr=(a,b)=>a==null||b==null?"":Math.abs(b-a)>=0.05?(b>a?' <span class="arr">↑</span>':' <span class="arr">↓</span>'):"";
  switch(p.pos){
    case "QB": return `${pct(p.snap)} snaps · ${pct(p.car_sh)} of runs`;
    case "RB": return `${pct(p.car_sh)} of carries${arr(p.car_sh,p.car_sh_s)}`;
    case "WR": case "TE": return `${pct(p.tgt_sh)} of targets${arr(p.tgt_sh,p.tgt_sh_s)}`;
    case "K": return `${f1(p.ppg)} pts/g lately`;
    default: return `${pct(p.snap)} snaps${arr(p.snap,p.snap_s)} · ${f1((p.tkl_sh||0)*100)} tkl/100`;
  }
}
function metaText(p,hz){
  let m=`${p.pos} · ${esc(p.team)}`;
  if(hz==="w") m+= p.w_opp?` ${p.w_home?"vs":"@"} ${esc(p.w_opp)}`:" · bye";
  m+=" · "+(p.mine?'<span class="me">My team</span>':p.owner?`<span class="own">${esc(short(p.owner,18))}</span>`:(HAVE_OWNERS?'<span class="fa">Free agent</span>':""));
  if(p.ystatus) m+=` · <span class="flag">${esc(p.ystatus)}</span>`;
  else if(hz==="w"&&p.w_avail!=null&&p.w_avail<0.95&&p.w_opp) m+=` · <span class="flag">${pct(p.w_avail)} to play</span>`;
  return m;
}
function rowHtml(r,i,max,opts={}){
  const p=r.p, hz=S.hz[S.tab];
  const lead=r.v?r.v.mean:null;
  const left=opts.slot?`<span class="slot">${opts.slot}</span>`:(i!=null?i:"");
  const tag=opts.tag!=null?opts.tag:tagFor(r);
  const val=opts.gain!=null?opts.gain:r.vorp;
  const band=opts.band?`style="--tierband:${opts.band}"`:"";
  return `<div class="row${p.mine?" mine":""}" data-id="${p.player_id}" tabindex="0" role="button" aria-expanded="${S.open===p.player_id}" ${band}>
    <span class="rk">${left}</span>
    <span class="pl"><span class="nm">${esc(p.name)}</span><span class="meta">${metaText(p,hz)}</span></span>
    <span class="tag">${tag}</span>
    <span class="ob">${r.v?outlook(r,max,opts.narrow?124:156):""}</span>
    <span class="proj">${f1(lead)}${hz!=="w"?`<small>${r.v.g} games</small>`:""}</span>
    <span class="val ${val>=0?"up":"dn"}">${sgn(val)}${opts.perg?"<small>/g</small>":""}</span>
    <span class="role">${roleText(p)}</span></div>`
    + (S.open===p.player_id?detailHtml(r):"");
}
function colsHtml(max,leadLbl,valLbl){
  const hz=S.hz[S.tab];
  return `<div class="cols"><span></span><span>Player</span><span></span>${max==null?"<span>Likely range</span>":`<span class="axis"><span>0</span><span>${hz==="w"?"likely range, pts":"typical week, pts"}</span><span>${Math.round(max)}</span></span>`}<span>${leadLbl}</span><span>${valLbl}</span><span>Role</span></div>`;
}

/* ---------- detail ---------- */
function summaryText(r){
  const p=r.p; const parts=[];
  if(p.pool==="idp") parts.push(`Plays ${pct(p.snap)} of snaps and makes ${f1((p.tkl_sh||0)*100)} tackles per 100 opponent plays${p.tkl_sh_s!=null&&Math.abs(p.tkl_sh_s-p.tkl_sh)>0.005?(p.tkl_sh_s>p.tkl_sh?", up lately":", down lately"):""}.`);
  else if(p.pos==="K") parts.push(`Averages ${f1(p.fga_g)} field-goal tries a game.`);
  else if(p.pos==="QB") parts.push(`Plays ${pct(p.snap)} of snaps and takes ${pct(p.car_sh)} of his team's runs.`);
  else if(p.pos==="RB") parts.push(`Gets ${pct(p.car_sh)} of carries and ${pct(p.tgt_sh)} of targets${p.car_sh_s!=null&&Math.abs(p.car_sh_s-p.car_sh)>=0.05?(p.car_sh_s>p.car_sh?", with carries rising":", with carries falling"):""}.`);
  else parts.push(`Gets ${pct(p.tgt_sh)} of targets on ${pct(p.snap)} of snaps${p.tgt_sh_s!=null&&Math.abs(p.tgt_sh_s-p.tgt_sh)>=0.03?(p.tgt_sh_s>p.tgt_sh?", trending up":", trending down"):""}.`);
  if(p.roll_q20!=null) parts.push(`Most weeks he scores ${f1(p.roll_q20)} to ${f1(p.roll_q80)}; he hits ${THR[p.pos][1]}+ in about ${pct(p.rate_boom)} of games.`);
  return parts.join(" ");
}
function logChart(p,max){
  const log=p.log||[], n=log.length, W=320, H=96, top=8, bot=16, h=H-top-bot, bw=(W-8)/Math.max(n+1,1);
  const y=v=>top+h-h*Math.max(0,Math.min(1,v/max));
  const rp=evaluate("w",0).repl[p.pos].pg, boom=THR[p.pos][1];
  let s=`<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="game log">`;
  s+=`<line x1="4" x2="${W-4}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)"></line>`;
  log.forEach((v,i)=>{ const x0=4+i*bw+2, w=bw-4;
    if(v==null){ s+=`<rect x="${x0}" y="${y(0)-2}" width="${w}" height="2" fill="none" stroke="var(--faint)"></rect>`; }
    else{ const c=v>=boom?"var(--turf)":v>=rp?"var(--turf-mid)":"var(--below)"; s+=`<rect x="${x0}" y="${y(v)}" width="${w}" height="${Math.max(1,y(0)-y(v))}" rx="1.5" fill="${c}"></rect>`; }
    s+=`<text x="${x0+w/2}" y="${H-4}" font-size="9" text-anchor="middle" fill="var(--faint)" font-family="var(--mono)">${i+1}</text>`; });
  if(p.w_mean!=null){ const x0=4+n*bw+2, w=bw-4; s+=`<rect x="${x0}" y="${y(p.w_q75)}" width="${w}" height="${Math.max(1,y(p.w_q25)-y(p.w_q75))}" rx="1.5" fill="var(--turf-soft)" stroke="var(--turf)" stroke-dasharray="2 2"></rect><text x="${x0+w/2}" y="${H-4}" font-size="9" text-anchor="middle" fill="var(--turf)" font-family="var(--mono)">${DATA.meta.week}</text>`; }
  s+=`<line x1="4" x2="${W-4}" y1="${y(rp)}" y2="${y(rp)}" stroke="var(--fg)" stroke-dasharray="3 3" opacity=".5"></line>`;
  s+=`<line x1="4" x2="${W-4}" y1="${y(boom)}" y2="${y(boom)}" stroke="var(--gold)" stroke-dasharray="1 3"></line>`;
  return s+"</svg>";
}
function consBar(p){
  const bust=p.rate_bust||0, start=p.rate_start||0, boom=p.rate_boom||0;
  const parts=[["Bust",bust,"var(--below)"],["OK",Math.max(0,1-bust-start),"var(--line)"],["Start",Math.max(0,start-boom),"var(--turf-mid)"],["Boom",boom,"var(--turf)"]];
  const tot=parts.reduce((a,b)=>a+b[1],0)||1; let x=0, W=300;
  let s=`<svg viewBox="0 0 ${W} 34" width="${W}" height="34" role="img" aria-label="share of weeks">`;
  for(const [l,v,c] of parts){ const w=W*v/tot; if(w<=0) continue; s+=`<rect x="${x}" y="0" width="${w}" height="18" fill="${c}"></rect>`; if(w>34) s+=`<text x="${x+w/2}" y="13" font-size="10" text-anchor="middle" fill="var(--fg)" font-family="var(--body)">${l} ${Math.round(v*100)}%</text>`; x+=w; }
  return s+`<text x="0" y="31" font-size="10" fill="var(--muted)" font-family="var(--body)">Bust = under half a useful week.</text></svg>`;
}
function slope(label,a,b,fmt=pct){
  if(a==null||b==null) return "";
  const W=88,H=34, mx=Math.max(a,b,0.0001)*1.15, y=v=>H-6-(H-12)*(v/mx);
  return `<div class="slope"><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true"><line x1="22" x2="${W-22}" y1="${y(a)}" y2="${y(b)}" stroke="var(--fg)" stroke-width="1.5"></line><circle cx="22" cy="${y(a)}" r="2.5" fill="var(--faint)"></circle><circle cx="${W-22}" cy="${y(b)}" r="3" fill="var(--turf)"></circle><text x="0" y="${y(a)+3}" font-size="9" fill="var(--muted)" font-family="var(--mono)">${fmt(a)}</text><text x="${W-19}" y="${y(b)+3}" font-size="9" fill="var(--fg)" font-family="var(--mono)">${fmt(b)}</text></svg><div>${label}</div></div>`;
}
function detailHtml(r){
  const p=r.p, mx=Math.max(THR[p.pos][1]*1.25, ...(p.log||[]).filter(v=>v!=null), p.w_q75||0);
  const k=v=>f1((v||0)*100);
  const k2=v=>((v||0)*100).toFixed(1);
  const sl = p.pool==="idp" ? [slope("snaps",p.snap,p.snap_s),slope("tackles/100 plays",p.tkl_sh,p.tkl_sh_s,k),slope("QB hits/100 snaps",p.hit_rate,p.hit_rate_s,k2),slope("TFL/100 snaps",p.tfl_rate,p.tfl_rate_s,k2)]
    : p.pos==="K"? [] : p.pos==="RB"? [slope("snaps",p.snap,p.snap_s),slope("carry share",p.car_sh,p.car_sh_s),slope("target share",p.tgt_sh,p.tgt_sh_s)]
    : p.pos==="QB"? [slope("snaps",p.snap,p.snap_s)] : [slope("snaps",p.snap,p.snap_s),slope("target share",p.tgt_sh,p.tgt_sh_s)];
  const wk=p.w_mean!=null?`<dl class="kv"><dt>Matchup</dt><dd>${p.w_home?"vs":"@"} ${esc(p.w_opp)}</dd>${p.pool==="idp"?`<dt>Tackles / game (recent)</dt><dd>${f1(p.exp_tkl)}</dd>`:`<dt>Team expected pts</dt><dd>${f1(p.w_implied)}</dd>`}<dt>Projected</dt><dd>${f1(p.w_mean)}</dd><dt>Bad / big week</dt><dd>${f1(p.w_q10)} / ${f1(p.w_q90)}</dd><dt>Useful week (${THR[p.pos][0]}+), projected</dt><dd>${pct(p.w_p_start)}</dd><dt>Big week (${THR[p.pos][1]}+), projected</dt><dd>${pct(p.w_p_boom)}</dd><dt>Chance to play</dt><dd>${pct(p.w_avail)}</dd></dl>`:`<p class="sub">Bye in week ${DATA.meta.week}.</p>`;
  return `<div class="detail"><div class="summary">${summaryText(r)}</div>
    <div class="dgrid">
      <div><h4>Season game log · this week shaded</h4>${logChart(p,mx)}<div class="sub">Dashed = replacement level · dotted = big week · hollow = no game (bye or out)</div></div>
      <div><h4>How often he delivered, last 16 games</h4>${consBar(p)}<h4 style="margin-top:10px">Role, season → last 3 weeks</h4><div class="slopes">${sl.join("")}</div></div>
      <div><h4>Week ${DATA.meta.week}</h4>${wk}<h4 style="margin-top:10px">Outlook</h4><dl class="kv"><dt>Rest of season (${p.ros_games} g)</dt><dd>${f1(p.ros_mean)}</dd><dt>Playoffs wk 15-17</dt><dd>${f1(p.po_mean)}</dd>${p.owner?`<dt>Owner</dt><dd>${esc(short(p.owner,20))}</dd>`:""}</dl></div>
    </div></div>`;
}

/* ---------- views ---------- */
let evaluateCache=null;
function poolRows(rows){ return rows.filter(r=>r.p.pool===S.pool); }
function applyFilters(rows,{own=true}={}){
  let out=rows.filter(r=>r.sc!=null);
  if(S.pos==="FLEX") out=out.filter(r=>(S.pool==="offense"?["RB","WR","TE"]:POS.idp).includes(r.p.pos));
  else if(S.pos==="LBSLOT") out=out.filter(r=>r.p.lb_elig);
  else if(S.pos!=="ALL") out=out.filter(r=>r.p.pos===S.pos);
  if(own){ if(S.own==="fa") out=out.filter(r=>!r.p.owner); else if(S.own==="mine") out=out.filter(r=>r.p.mine);
    else if(S.own==="owned") out=out.filter(r=>r.p.owner); else if(S.own.startsWith("o:")) out=out.filter(r=>r.p.owner===S.own.slice(2)); }
  if(S.q){const q=S.q.toLowerCase(); out=out.filter(r=>r.p.name.toLowerCase().includes(q)||String(r.p.team).toLowerCase()===q);}
  return out;
}
function tiers(list,key){
  const vals=list.map(key), n=Math.min(vals.length,60), gaps=[];
  for(let i=1;i<n;i++) gaps.push(vals[i-1]-vals[i]);
  const mg=gaps.length?gaps.slice().sort((a,b)=>a-b)[Math.floor(gaps.length/2)]:0;
  const span=n>1?vals[0]-vals[n-1]:0, thr=Math.max(3*mg,0.06*span);
  const t=[0]; for(let i=1;i<vals.length;i++){ const size=i-t.at(-1); if((vals[i-1]-vals[i]>thr&&size>=2)||size>=12) t.push(i); }
  return t;
}
function viewLineup(ev){
  const hz=S.hz.lineup;
  const mine=ev.rows.filter(r=>r.p.mine);
  const {starters,bench}=fillLineup(mine);
  const own=ev.rows.filter(r=>r.v&&(r.p.owner||r.p.mine));
  const maxBy={offense:scaleFor(hz,own.filter(r=>r.p.pool==="offense")),idp:scaleFor(hz,own.filter(r=>r.p.pool==="idp"))};
  const max=maxBy.offense;
  // callouts: free agents who would start, and starters with a problem
  const calls=[];
  const fas=ev.rows.filter(r=>!r.p.owner&&r.sc!=null);
  const seen=new Set();
  for(const st of starters){
    const cur=st.r; const elig=st.elig;
    const best=fas.filter(r=>!seen.has(r.p.player_id)&&(elig[0]==="LB*"?r.p.lb_elig:elig.includes(r.p.pos))).sort((a,b)=>b.sc-a.sc)[0];
    if(best&&(!cur||best.sc>cur.sc+0.75)){ seen.add(best.p.player_id); calls.push({g:best.sc-(cur?cur.sc:0),h:`<span class="k">Add</span><span><b>${esc(best.p.name)}</b> (free agent, ${best.p.pos}) would start at ${st.slot}${cur?` over ${esc(cur.p.name)}: <b>${sgn(best.v.mean-cur.v.mean)}</b> projected pts${S.lam?` (${S.lam<0?"floor":"upside"} edge ${sgn(best.sc-cur.sc)})`:""}`:""}.</span>`}); }
    if(cur&&cur.p.w_mean!=null&&cur.p.w_avail<0.9) calls.push({g:99,h:`<span class="k warn">Check</span><span><b>${esc(cur.p.name)}</b> has a ${pct(cur.p.w_avail)} chance to play${cur.p.ystatus?` (${esc(cur.p.ystatus)})`:""}. Have a backup ready.</span>`});
  }
  const byes=mine.filter(r=>r.p.w_mean==null).map(r=>r.p.name);
  if(byes.length) calls.push({g:-1,h:`<span class="k info">Bye</span><span>${byes.map(esc).join(", ")} ${byes.length>1?"are":"is"} off this week.</span>`});
  calls.sort((a,b)=>b.g-a.g);
  let h=`<div class="listhead"><span><b>Best lineup for week ${DATA.meta.week}</b>${S.lam?`, picked for ${styleName()}`:""}.</span><span>Projected total: <b>${f1(starters.reduce((a,s)=>a+(s.r?s.r.v.mean:0),0))}</b></span></div>`;
  if(calls.length) h+=`<div class="callouts">${calls.slice(0,5).map(c=>`<div class="callout">${c.h}</div>`).join("")}</div><div class="listhead"><span>Free agents are based on rosters from ${rosterWk()}; confirm they're still available.</span></div>`;
  h+=colsHtml(null,"Proj pts","Value")+`<div class="list">`;
  for(const st of starters){
    if(!st.r){ h+=`<div class="row"><span class="rk"><span class="slot">${st.slot}</span></span><span class="pl"><span class="nm" style="color:var(--bad)">Empty</span><span class="meta">No eligible player on your roster</span></span></div>`; continue; }
    h+=rowHtml(st.r,null,maxBy[st.r.p.pool],{slot:st.slot,tag:'<span class="t start">Start</span>'});
  }
  h+=`</div><div class="tierlbl">Bench</div><div class="list">`;
  bench.sort((a,b)=>(b.sc??-1)-(a.sc??-1)).forEach(r=>{ h+= r.v? rowHtml(r,null,maxBy[r.p.pool],{slot:"BN",tag:'<span class="t bench">Bench</span>'}) : `<div class="row"><span class="rk"><span class="slot">BN</span></span><span class="pl"><span class="nm">${esc(r.p.name)}</span><span class="meta">${r.p.pos} · ${esc(r.p.team)} · bye this week</span></span></div>`; });
  return h+"</div>";
}
function viewWaivers(ev){
  const hz=S.hz.waivers, perg=hz!=="w";
  const pr=poolRows(ev.rows);
  const {starters}=fillLineup(ev.rows.filter(r=>r.p.mine));
  const pg=r=>r.sc/r.v.per;
  const weakest=(pos,lb)=>starters.filter(s=>s.r&&s.r.v&&(s.elig[0]==="LB*"?lb:s.elig.includes(pos))).map(s=>s.r).sort((a,b)=>pg(a)-pg(b))[0]||null;
  let list=applyFilters(pr,{own:false}).filter(r=>!r.p.owner);
  for(const r of list){ const w=weakest(r.p.pos,r.p.lb_elig); r.gain=w?pg(r)-pg(w):r.vorp/r.v.per; }
  // drop candidate: weakest bench player by rest-of-season points per game, whole roster
  const rosEv=evaluate("ros",0); const mineRos=rosEv.rows.filter(r=>r.p.mine);
  const lu=fillLineup(mineRos); const drop=lu.bench.filter(r=>r.v).sort((a,b)=>a.v.mean/a.v.per-b.v.mean/b.v.per)[0];
  const max=scaleFor(hz,list.slice(0,60));
  let h=`<div class="callouts"><div class="callout"><span class="k warn">Check</span><span>Rosters are from ${rosterWk()}. Anyone added since then still shows here as a free agent.</span></div></div>`;
  h+=`<div class="listhead"><span><b>Free agents</b>, by ${perg?"points per game":"points"} gained over your weakest starter at that slot (${hzName(hz)}${S.lam?`, ${styleName()}`:""}).</span>${drop?`<span>Drop candidate: <b>${esc(drop.p.name)}</b> (${f1(drop.v.mean/drop.v.per)}/g rest of season)</span>`:""}</div>`;
  h+=colsHtml(max,hz==="w"?"Proj pts":"Proj pts",perg?"Gain/g":"Gain")+`<div class="list">`;
  const groups=[["Would start for you",r=>r.gain>=0.5,40],["Close to your starters",r=>r.gain>-1.5,25],["Stash or speculative",r=>true,15]];
  const done=new Set(); let n=0;
  for(const [lbl,fn,cap] of groups){
    const g=list.filter(r=>!done.has(r)&&fn(r)).sort((a,b)=>b.gain-a.gain).slice(0,cap); if(!g.length) continue;
    h+=`</div><div class="tierlbl">${lbl}</div><div class="list">`;
    g.forEach(r=>{done.add(r); n++; h+=rowHtml(r,n,max,{gain:r.gain,perg});});
  }
  if(!n) h+=`<div class="empty">No free agents match. Clear the search or pick another position.</div>`;
  return h+"</div>";
}
function viewRank(ev){
  const hz=S.hz.rank;
  let list=applyFilters(poolRows(ev.rows));
  const byVal=S.pos==="ALL"||S.pos==="FLEX"||S.pos==="LBSLOT";
  const key=r=>byVal?r.vorp:r.sc;
  list.sort((a,b)=>key(b)-key(a));
  const total=list.length; list=list.slice(0,S.more?250:60);
  const max=scaleFor(hz,list.slice(0,80));
  const t=tiers(list,key);
  let h=`<div class="listhead"><span><b>${S.pool==="offense"?"Offense":"IDP"} ${posLabel()}</b>, ${hzName(hz)}, ranked for ${styleName()}. ${byVal?"Sorted by value (points above a fringe starter) so positions compare fairly.":"Sorted by projected points."}</span></div>`;
  h+=colsHtml(max,"Proj pts","Value")+`<div class="list">`;
  let tier=0;
  list.forEach((r,i)=>{ if(t.includes(i)){ tier++; const end=(t[t.indexOf(i)+1]||list.length)-1;
      h+=`</div><div class="tierlbl">Tier ${tier}</div><div class="list">`; }
    h+=rowHtml(r,i+1,max,{band:tier%2?"var(--tierA)":"var(--line)"}); });
  if(!list.length) h+=`<div class="empty">No players match these filters. Clear the search or switch "Whose players" to All players.</div>`;
  h+="</div>";
  if(total>list.length) h+=`<button class="more" id="more">Show ${Math.min(total,250)-list.length} more</button>`;
  return h;
}
const rosterWk=()=>DATA.meta.yahoo_file?("week "+DATA.meta.yahoo_file.replace(/\D+/g,"")):"an unknown week";
const styleName=()=>({"-1":"a safe floor","0":"balanced","1":"upside"})[String(S.lam)];
const hzName=hz=>({w:`week ${DATA.meta.week}`,ros:`rest of season (weeks ${DATA.meta.weeks_left[0]}-${DATA.meta.weeks_left.at(-1)})`,po:"playoffs (weeks 15-17)"})[hz];
const posLabel=()=>S.pos==="ALL"?"all positions":S.pos==="FLEX"?(S.pool==="offense"?"W/R/T flex":"any IDP (D slot)"):S.pos==="LBSLOT"?"LB-eligible":S.pos;

function render(){
  try{localStorage.setItem("iblboard2",JSON.stringify({tab:S.tab,pool:S.pool,hz:S.hz,lam:S.lam,pos:S.pos,own:S.own}));}catch(e){}
  const hz=S.hz[S.tab];
  document.querySelectorAll("#tabs button").forEach(b=>b.setAttribute("aria-selected",b.dataset.v===S.tab));
  document.querySelectorAll("#pool button").forEach(b=>b.setAttribute("aria-pressed",b.dataset.v===S.pool));
  $("pool").hidden=S.tab==="lineup";
  document.querySelectorAll("#hz button").forEach(b=>{b.setAttribute("aria-pressed",b.dataset.v===hz); b.hidden=S.tab==="lineup"&&b.dataset.v!=="w";});
  $("hz").hidden=S.tab==="lineup";
  document.querySelectorAll("#style button").forEach(b=>b.setAttribute("aria-pressed",+b.dataset.v===S.lam));
  $("filters").hidden=S.tab==="lineup";
  const chips=[["ALL","All"],["FLEX",S.pool==="offense"?"W/R/T":"Any IDP"]].concat(S.pool==="idp"?[["LBSLOT","LB-eligible"]]:[]).concat(POS[S.pool].map(p=>[p,p]));
  if(!chips.some(c=>c[0]===S.pos)) S.pos="ALL";
  $("pos").innerHTML=chips.map(([k,l])=>`<button class="chip" id="pos-${k}" data-v="${k}" aria-pressed="${S.pos===k}">${l}</button>`).join("");
  $("own").hidden=S.tab!=="rank";
  const opts=[["all","All players"],["fa","Free agents"],["mine","My team"],["owned","All rostered"]].concat(OWNERS.map(o=>["o:"+o,o]));
  $("own").innerHTML=opts.map(([v,l])=>`<option value="${esc(v)}"${S.own===v?" selected":""}>${esc(l)}</option>`).join("");
  evaluateCache=evaluate(hz,S.lam);
  $("main").innerHTML= S.tab==="lineup"?viewLineup(evaluateCache):S.tab==="waivers"?viewWaivers(evaluateCache):viewRank(evaluateCache);
}
function init(){
  const m=DATA.meta;
  $("sub").textContent=`Irene's Bush League · Week ${m.week} · rosters as of ${m.yahoo_file?m.yahoo_file.replace(/\D+/g," ").trim().replace(/^/,"wk "):"n/a"} (recent adds may be missing)`;
  $("bt").textContent=(m.backtest||"");
  const on=(id,ev,fn)=>$(id).addEventListener(ev,fn);
  on("tabs","click",e=>{const b=e.target.closest("button"); if(!b) return; S.tab=b.dataset.v; S.open=null; render();});
  on("pool","click",e=>{const b=e.target.closest("button"); if(!b) return; S.pool=b.dataset.v; S.open=null; render();});
  on("hz","click",e=>{const b=e.target.closest("button"); if(!b) return; S.hz[S.tab]=b.dataset.v; render();});
  on("style","click",e=>{const b=e.target.closest("button"); if(!b) return; S.lam=+b.dataset.v; render();});
  on("pos","click",e=>{const b=e.target.closest("button"); if(!b) return; S.pos=b.dataset.v; S.more=false; render();});
  on("own","change",e=>{S.own=e.target.value; render();});
  on("q","input",e=>{S.q=e.target.value.trim(); render();});
  const toggle=e=>{const row=e.target.closest(".row[data-id]"); if(!row) return; S.open=S.open===row.dataset.id?null:row.dataset.id; render();
    const el=document.querySelector(`.row[data-id="${S.open}"]`); if(el) el.focus({preventScroll:true});};
  on("main","click",e=>{ if(e.target.id==="more"){S.more=true; render(); return;} toggle(e); });
  on("main","keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault(); toggle(e);}});
  render();
}
init();
</script>
"""


def render(payload: dict) -> str:
    js = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", js)

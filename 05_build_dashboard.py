import json
R=json.load(open("results.json")); seg=__import__("pandas").read_csv("data/segments.csv")
D={k:R[k] for k in ["segments","clusters","profile_wd","profile_we","speed_wd","heat","effects","models","classification","importance","sim","total_delay_veh_h","total_co2_t"]}
D["names"]={int(r.segment_id):r.segment_name for r in seg.itertuples()}
html=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ventura Traffic Congestion Dashboard (simulated data)</title>
<style>:root{--bg:#f7f8fa;--card:#fff;--tx:#1d2733;--mu:#667;--ac:#2c7fb8;--bd:#dde3ea}@media(prefers-color-scheme:dark){:root{--bg:#12161c;--card:#1b222b;--tx:#e6ebf1;--mu:#98a3b0;--ac:#6bb6e6;--bd:#2c3642}}
body{margin:0;font:14px system-ui,sans-serif;background:var(--bg);color:var(--tx)}header{padding:16px 20px}h1{margin:0;font-size:20px}.warn{background:#fff3cd;color:#664d03;padding:8px 20px;font-size:13px}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:14px;padding:0 20px 24px}.c{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px}.c h2{margin:0 0 8px;font-size:14px}
.k{display:flex;gap:10px;flex-wrap:wrap;padding:0 20px 14px}.k div{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 14px}.k b{display:block;font-size:20px}.k span{color:var(--mu);font-size:12px}
select,input{font:inherit;background:var(--card);color:var(--tx);border:1px solid var(--bd);border-radius:6px;padding:4px}canvas{width:100%;height:210px}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:3px 6px;border-bottom:1px solid var(--bd);text-align:left}
.hm{display:grid;grid-template-columns:30px repeat(24,1fr);gap:1px;font-size:9px}.hm i{height:16px;display:block}small{color:var(--mu)}</style></head><body>
<header><h1>Ventura County Corridor Congestion Dashboard</h1><small>Jan-Jun 2025, 12 stylised segments, 15-minute data</small></header>
<div class="warn"><b>Simulated data.</b> All values come from a mechanistic simulator, not real sensors. Use this as a template for real NPMRDS/PeMS data.</div>
<div class="k" id="kpi"></div>
<main>
<div class="c"><h2>Segment <select id="seg"></select> <select id="day"><option value="wd">Weekday</option><option value="we">Weekend</option></select></h2><canvas id="cp"></canvas><small id="cl"></small></div>
<div class="c"><h2>Travel-time-index heatmap (day x hour)</h2><div class="hm" id="hm"></div><small>Rows Mon-Sun. Pale = free flow, dark red = heavy delay.</small></div>
<div class="c"><h2>Vehicle-hours of delay by segment</h2><canvas id="dl"></canvas></div>
<div class="c"><h2>What-if: conditions on selected segment</h2><label><input type="checkbox" id="r1"> light rain</label> <label><input type="checkbox" id="r2"> heavy rain</label> <label><input type="checkbox" id="in"> incident</label>
<p>Hour <input type="range" id="hr" min="0" max="23" value="8"> <b id="hv">8:00</b></p><p id="wi" style="font-size:16px"></p><small>Effects are within-estimator % changes from the simulated data (rain and incident multipliers combine multiplicatively).</small></div>
<div class="c"><h2>Forecast models (test MAE, mph) <select id="hz"><option>15 min</option><option>30 min</option><option selected>60 min</option></select></h2><canvas id="md"></canvas><small id="cf"></small></div>
<div class="c"><h2>Top forecast features</h2><canvas id="im"></canvas></div>
<div class="c" style="grid-column:1/-1"><h2>Signal control simulation (mean delay, s/vehicle)</h2><table id="sm"></table></div>
</main><script>
const D=__DATA__;const $=i=>document.getElementById(i);const css=n=>getComputedStyle(document.body).getPropertyValue(n);
function bars(cv,labels,vals,fmt,col){const c=$(cv),x=c.getContext("2d"),W=c.width=c.clientWidth*2,H=c.height=420;x.clearRect(0,0,W,H);x.font="22px system-ui";const n=labels.length,lw=W*.42,mx=Math.max(...vals)||1,bh=H/n;
labels.forEach((l,i)=>{x.fillStyle=css("--tx");x.fillText(l.slice(0,34),4,i*bh+bh*.65);x.fillStyle=col||css("--ac");const w=(W-lw-90)*vals[i]/mx;x.fillRect(lw,i*bh+bh*.15,w,bh*.65);x.fillStyle=css("--tx");x.fillText(fmt(vals[i]),lw+w+6,i*bh+bh*.65)})}
function line(cv,series){const c=$(cv),x=c.getContext("2d"),W=c.width=c.clientWidth*2,H=c.height=420;x.clearRect(0,0,W,H);x.font="22px system-ui";const all=series.flatMap(s=>s.v),mn=Math.min(...all),mx=Math.max(...all);
const px=i=>50+i*(W-70)/23,py=v=>H-40-(v-mn)/(mx-mn||1)*(H-70);x.strokeStyle=css("--bd");x.fillStyle=css("--mu");[0,6,12,18,23].forEach(h=>{x.fillText(h+"h",px(h)-10,H-10)});x.fillText(mx.toFixed(2),0,24);x.fillText(mn.toFixed(2),0,H-44);
series.forEach(s=>{x.beginPath();x.strokeStyle=s.c;x.lineWidth=4;s.v.forEach((v,i)=>i?x.lineTo(px(i),py(v)):x.moveTo(px(i),py(v)));x.stroke()})}
const sel=$("seg");Object.entries(D.names).forEach(([k,v])=>sel.add(new Option(k+" "+v,k)));
function heat(s){const el=$("hm");el.innerHTML="";const days=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];days.forEach((d,i)=>{el.insertAdjacentHTML("beforeend","<span>"+d+"</span>");(D.heat[s+"_"+i]||[]).forEach(v=>{const t=Math.min(1,(v-1)/2);el.insertAdjacentHTML("beforeend",`<i title="${v.toFixed(2)}" style="background:hsl(${50-50*t},90%,${95-45*t}%)"></i>`)})})}
function wi(){const s=sel.value,h=+$("hr").value,E=D.effects,tti=(D.profile_wd[s]||[])[h]||1;let m=1;if($("r1").checked)m*=1+E.rain_light.pct/100;if($("r2").checked)m*=1+E.rain_heavy.pct/100;if($("in").checked)m*=1+E.incident.pct/100;$("hv").textContent=h+":00";
$("wi").innerHTML=`Typical weekday TTI ${tti.toFixed(2)} &rarr; <b>${(tti*m).toFixed(2)}</b> (${((m-1)*100).toFixed(0)}% longer trip)`}
function upd(){const s=sel.value,d=$("day").value;line("cp",[{v:D["profile_"+d][s],c:css("--ac")}]);$("cl").textContent="Hotspot cluster: "+D.clusters[s]+" | line = travel time index by hour (1.0 free flow)";heat(s);wi()}
function mdl(){const h=$("hz").value,m=D.models.filter(r=>r.horizon==h);bars("md",m.map(r=>r.model),m.map(r=>r.mae),v=>v.toFixed(2),"#e67e22");const c=D.classification;$("cf").textContent=`Congestion-level classification (60 min): accuracy ${c.gb_acc.toFixed(3)} vs persistence ${c.persist_acc.toFixed(3)}; macro-F1 ${c.gb_f1.toFixed(2)} vs ${c.persist_f1.toFixed(2)}`}
sel.onchange=upd;$("day").onchange=upd;$("hz").onchange=mdl;["r1","r2","in","hr"].forEach(i=>$(i).oninput=wi);
$("kpi").innerHTML=[[Math.round(D.total_delay_veh_h/1000)+"k","vehicle-hours delay"],[Math.round(D.total_co2_t)+" t","CO2 emitted"],["12","segments"],["208,512","observations"]].map(a=>`<div><b>${a[0]}</b><span>${a[1]}</span></div>`).join("");
const sg=[...D.segments].sort((a,b)=>b.delay-a.delay);bars("dl",sg.map(r=>r.segment_name),sg.map(r=>r.delay/1000),v=>v.toFixed(0)+"k");bars("im",D.importance.slice(0,8).map(a=>a[0]),D.importance.slice(0,8).map(a=>a[1]),v=>v.toFixed(2),"#16a085");
$("sm").innerHTML="<tr><th>Scenario</th><th>Controller</th><th>Mean delay (s/veh)</th><th>Peak queue</th></tr>"+D.sim.map(r=>`<tr><td>${r.scenario}</td><td>${r.controller}</td><td>${r.mean_delay_s.toFixed(1)} &plusmn; ${r.ci95.toFixed(1)}</td><td>${Math.round(r.max_total_queue)}</td></tr>`).join("");
upd();mdl();addEventListener("resize",()=>{upd();mdl();bars("dl",sg.map(r=>r.segment_name),sg.map(r=>r.delay/1000),v=>v.toFixed(0)+"k")});
</script></body></html>'''.replace("__DATA__",json.dumps(D))
open("outputs/Traffic_Dashboard.html","w").write(html); print(len(html)//1024,"KB")

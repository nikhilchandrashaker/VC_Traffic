"""EDA, hotspot clustering, effect estimation, forecasting models, figures -> results.json"""
import numpy as np, pandas as pd, json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.metrics import mean_absolute_error as MAE, mean_squared_error, r2_score, accuracy_score, f1_score, confusion_matrix
from sklearn.inspection import permutation_importance
from sklearn.cluster import KMeans
plt.rcParams.update({"figure.dpi":150,"axes.spines.top":False,"axes.spines.right":False,"font.size":9})
o = pd.read_csv("data/observations.csv",parse_dates=["timestamp"]); seg = pd.read_csv("data/segments.csv")
o = o.merge(seg[["segment_id","free_flow_mph","length_mi","lanes","road_type","segment_name"]],on="segment_id")
o["hour"]=o.timestamp.dt.hour; o["dow"]=o.timestamp.dt.dayofweek
R = {}
# ---- delay & hotspots
o["delay_veh_h"] = o.volume_veh_15min*o.length_mi*(1/o.avg_speed_mph-1/o.free_flow_mph)
dl = o.groupby("segment_id").agg(delay=("delay_veh_h","sum"),tti=("travel_time_index","mean"),
     severe=("congestion_level",lambda s:(s>=3).mean()),co2=("co2_kg","sum")).reset_index().merge(seg[["segment_id","segment_name","road_type"]])
R["segments"]=dl.round(3).to_dict("records")
R["total_delay_veh_h"]=float(o.delay_veh_h.sum()); R["total_co2_t"]=float(o.co2_kg.sum()/1000)
wd = o[(o.dow<5)&(o.is_holiday==0)]
prof = wd.pivot_table(index="segment_id",columns="hour",values="travel_time_index").values
km = KMeans(3,n_init=10,random_state=0).fit(prof); order=np.argsort(km.cluster_centers_.max(1)[::1])
lab = {c:n for c,n in zip(order,["Low-congestion","Moderate commuter","Severe commuter"])}
R["clusters"]={int(s):lab[c] for s,c in zip(seg.segment_id,km.labels_)}
R["profile_wd"]={int(s):prof[i].round(3).tolist() for i,s in enumerate(seg.segment_id)}
R["profile_we"]={int(s):v.round(3).tolist() for s,v in o[o.dow>=5].pivot_table(index="segment_id",columns="hour",values="travel_time_index").iterrows()}
R["speed_wd"]={int(s):v.round(1).tolist() for s,v in wd.pivot_table(index="segment_id",columns="hour",values="avg_speed_mph").iterrows()}
hm = o.pivot_table(index=["segment_id","dow"],columns="hour",values="travel_time_index")
R["heat"]={f"{s}_{d}":v.round(3).tolist() for (s,d),v in hm.iterrows()}
net = o.pivot_table(index="dow",columns="hour",values="travel_time_index"); R["net_heat"]=net.round(3).values.tolist()
# ---- effects: within-transformed OLS with day-block bootstrap
o["ltt"]=np.log(o.travel_time_index); o["qh"]=o.timestamp.dt.hour*4+o.timestamp.dt.minute//15
X = pd.DataFrame({"rain_light":((o.precip_mm_15min>.05)&(o.precip_mm_15min<=.5)).astype(float),
  "rain_heavy":(o.precip_mm_15min>.5).astype(float),"incident":o.incident_active.astype(float)})
key = o.segment_id.astype(str)+"_"+o.dow.astype(str)+"_"+o.qh.astype(str)
Xd = X-X.groupby(key).transform("mean"); yd = o["ltt"]-o["ltt"].groupby(key).transform("mean")
b = np.linalg.lstsq(Xd.values,yd.values,rcond=None)[0]
day = o.timestamp.dt.normalize().factorize()[0]; rng=np.random.default_rng(1); nd=day.max()+1
order_idx = np.argsort(day,kind="stable"); starts=np.searchsorted(day[order_idx],np.arange(nd+1))
bs=[]
for _ in range(100):
    pick=rng.integers(0,nd,nd); idx=np.concatenate([order_idx[starts[d]:starts[d+1]] for d in pick])
    bs.append(np.linalg.lstsq(Xd.values[idx],yd.values[idx],rcond=None)[0])
bs=np.array(bs); R["effects"]={n:{"pct":float((np.exp(b[i])-1)*100),"lo":float((np.exp(np.percentile(bs[:,i],2.5))-1)*100),"hi":float((np.exp(np.percentile(bs[:,i],97.5))-1)*100)} for i,n in enumerate(X.columns)}
# ---- forecasting
piv = lambda c: o.pivot(index="timestamp",columns="segment_id",values=c).values
SP,VO,IN = piv("avg_speed_mph"),piv("volume_veh_15min"),piv("incident_active")
ff = seg.free_flow_mph.values; T,ns = SP.shape; RA = SP/ff
ids = list(seg.segment_id); ix={s:i for i,s in enumerate(ids)}
dn=[[ix[int(float(x))] for x in str(v).split(";") if x not in("","nan")] for v in seg.downstream_ids]
up=[[ix[int(float(x))] for x in str(v).split(";") if x not in("","nan")] for v in seg.upstream_ids]
nb = lambda L,A: np.stack([A[:,l].mean(1) if l else np.full(T,np.nan) for l in L],1)
rain = o.drop_duplicates("timestamp").sort_values("timestamp").precip_mm_15min.values
ts_ = np.sort(o.timestamp.unique()); tsi = pd.DatetimeIndex(ts_)
sh = lambda A,k: np.vstack([np.full((k,A.shape[1]),np.nan),A[:-k]])
feats = {"speed_t":SP,"lag1":sh(SP,1),"lag2":sh(SP,2),"lag3":sh(SP,3),"lag4":sh(SP,4),"lag8":sh(SP,8),"lag_1day":sh(SP,96),
  "vol_t":VO,"vol_lag1":sh(VO,1),"incident":IN,"inc_lag4":sh(IN,4)}
feats["roll4"]=(SP+feats["lag1"]+feats["lag2"]+feats["lag3"])/4
graph = {"down_ratio_t":nb(dn,RA),"up_ratio_t":nb(up,RA),"down_ratio_lag2":sh(nb(dn,RA),2),"up_ratio_lag2":sh(nb(up,RA),2)}
glob = {"rain":np.repeat(rain[:,None],ns,1),"hour_sin":np.repeat(np.sin(2*np.pi*(tsi.hour+tsi.minute/60)/24).values[:,None],ns,1),
  "hour_cos":np.repeat(np.cos(2*np.pi*(tsi.hour+tsi.minute/60)/24).values[:,None],ns,1),"dow":np.repeat(tsi.dayofweek.values[:,None],ns,1),
  "holiday":np.repeat(np.isin(tsi.normalize().values,pd.to_datetime(["2025-01-01","2025-01-20","2025-02-17","2025-05-26","2025-06-19"]).values)[:,None],ns,1)}
stat = {"ff":np.tile(ff,(T,1)),"lanes":np.tile(seg.lanes.values,(T,1)),"is_art":np.tile((seg.road_type=="arterial").values,(T,1))}
def build(use_graph=True):
    d={**feats,**glob,**stat,**(graph if use_graph else {})}
    return list(d), np.stack([np.asarray(v,float)[96:T-4].ravel() for v in d.values()],1)
names,Xall = build(True); gi=[i for i,n in enumerate(names) if n in graph]; Xng = np.delete(Xall,gi,1); nng=[n for n in names if n not in graph]
split = np.searchsorted(tsi[96:T-4], pd.Timestamp("2025-05-01"))*ns
H={1:"15 min",2:"30 min",4:"60 min"}; res=[]; keep={}
def tgt(h): return SP[96+h:T-4+h].ravel()
Ste = SP[96:T-4].ravel()
for h in H:
    y=tgt(h); tr,te=slice(0,split),slice(split,None); m_te=(y[te]/np.tile(ff,len(y[te])//ns))<.7
    def rep(nm,p):
        res.append(dict(model=nm,horizon=H[h],mae=float(MAE(y[te],p)),rmse=float(mean_squared_error(y[te],p)**.5),r2=float(r2_score(y[te],p)),mae_congested=float(MAE(y[te][m_te],p[m_te]))))
    rep("Persistence",Ste[te])
    Xi=np.nan_to_num(Xng,nan=0); rd=Ridge(1.0).fit(Xi[tr],y[tr]); rep("Ridge regression",rd.predict(Xi[te]))
    rf=RandomForestRegressor(60,max_depth=14,min_samples_leaf=5,max_samples=.3,n_jobs=-1,random_state=0).fit(Xi[tr],y[tr]); rep("Random Forest",rf.predict(Xi[te]))
    g0=HistGradientBoostingRegressor(max_iter=250,learning_rate=.08,random_state=0).fit(Xng[tr],y[tr]); rep("Gradient boosting (no graph)",g0.predict(Xng[te]))
    g1=HistGradientBoostingRegressor(max_iter=250,learning_rate=.08,random_state=0).fit(Xall[tr],y[tr]); p1=g1.predict(Xall[te]); rep("Gradient boosting + graph features",p1)
    keep[h]=(g1,y,p1)
R["models"]=res
g1,y,p1=keep[2]; sub=np.random.default_rng(0).choice(np.arange(split,len(y)),12000,replace=False)
pi=permutation_importance(g1,Xall[sub],y[sub],n_repeats=3,random_state=0,scoring="neg_mean_absolute_error")
imp=sorted(zip(names,pi.importances_mean),key=lambda t:-t[1]); R["importance"]=[(n,float(v)) for n,v in imp[:10]]
# classification @30min
lvl=lambda r: np.select([r>.85,r>.70,r>.55,r>.40],[0,1,2,3],4)
rt=lvl(y/np.tile(ff,len(y)//ns)); cur=lvl(Ste/np.tile(ff,len(y)//ns))
cl=HistGradientBoostingClassifier(max_iter=200,random_state=0).fit(Xall[:split],rt[:split]); pc=cl.predict(Xall[split:])
R["classification"]={"gb_acc":float(accuracy_score(rt[split:],pc)),"gb_f1":float(f1_score(rt[split:],pc,average="macro")),
  "persist_acc":float(accuracy_score(rt[split:],cur[split:])),"persist_f1":float(f1_score(rt[split:],cur[split:],average="macro"))}
cm=confusion_matrix(rt[split:],pc,normalize="true")
R["n_train"]=int(split); R["n_test"]=int(len(y)-split)
# ---- figures
def save(n): plt.tight_layout(); plt.savefig(f"figures/{n}.png"); plt.close()
fig,ax=plt.subplots(figsize=(7,3)); im=ax.imshow(net.values,aspect="auto",cmap="YlOrRd"); ax.set_yticks(range(7)); ax.set_yticklabels("Mon Tue Wed Thu Fri Sat Sun".split())
ax.set_xlabel("Hour of day"); ax.set_title("Network-mean travel time index (1.0 = free flow)"); plt.colorbar(im,ax=ax); save("fig_heatmap")
fig,ax=plt.subplots(figsize=(7,3.3)); d=dl.sort_values("delay"); ax.barh(d.segment_name,d.delay/1000,color=["#c0392b" if r=="freeway" else "#2c7fb8" if r=="arterial" else "#7f8c8d" for r in d.road_type])
ax.set_xlabel("Vehicle-hours of delay (thousands), Jan-Jun 2025 (simulated)"); save("fig_delay")
fig,ax=plt.subplots(figsize=(7,3)); w=o[(o.segment_id==3)&(o.timestamp>="2025-02-17")&(o.timestamp<"2025-02-24")]
ax.plot(w.timestamp,w.avg_speed_mph,lw=.9); ax.fill_between(w.timestamp,0,70*w.incident_active,color="r",alpha=.2,label="incident active"); ax.fill_between(w.timestamp,0,70*(w.precip_mm_15min>.05),color="b",alpha=.15,label="rain")
ax.set_ylabel("Speed (mph)"); ax.set_title("Segment 3 (US-101 Oxnard-Camarillo), one week"); ax.legend(frameon=False); save("fig_week")
fig,ax=plt.subplots(figsize=(5,2.8)); e=R["effects"]; nm=list(e); v=[e[k]["pct"] for k in nm]
ax.bar(nm,v,yerr=[[e[k]["pct"]-e[k]["lo"] for k in nm],[e[k]["hi"]-e[k]["pct"] for k in nm]],color="#e67e22",capsize=4); ax.set_ylabel("% change in travel time"); ax.set_title("Estimated effects (95% block-bootstrap CI)"); save("fig_effects")
mm=pd.DataFrame(res); fig,ax=plt.subplots(figsize=(7,3.2)); ms=mm.model.unique()
for i,m in enumerate(ms): ax.bar(np.arange(3)+i*.16,mm[mm.model==m].mae,.16,label=m)
ax.set_xticks(np.arange(3)+.32); ax.set_xticklabels(list(H.values())); ax.set_ylabel("Test MAE (mph)"); ax.legend(fontsize=6,frameon=False); ax.set_title("Forecast error by horizon (May-Jun holdout)"); save("fig_models")
fig,ax=plt.subplots(figsize=(7,3)); s3=ix[3]; rows=np.arange(len(y)); sel=(rows%ns==s3)&(rows>=split)
yy,pp=y[sel],p1[sel[split:]]; tt=tsi[96+2:T-4+2][:len(y)//ns][split//ns:]; a=slice(96*10,96*13)
ax.plot(tt[a],yy[a],label="actual",lw=1); ax.plot(tt[a],pp[a],label="GB+graph forecast (60 min)",lw=1); ax.set_ylabel("Speed (mph)"); ax.legend(frameon=False); ax.set_title("Hold-out forecast, segment 3"); save("fig_forecast")
fig,ax=plt.subplots(figsize=(5,3)); ax.barh([n for n,_ in imp[:8]][::-1],[v for _,v in imp[:8]][::-1],color="#16a085"); ax.set_xlabel("Permutation importance (MAE increase, mph)"); ax.set_title("Top features, 60-min model"); save("fig_importance")
fig,ax=plt.subplots(figsize=(3.8,3.4)); ax.imshow(cm,cmap="Blues"); [ax.text(j,i,f"{cm[i,j]:.2f}",ha="center",va="center",fontsize=7) for i in range(cm.shape[0]) for j in range(cm.shape[1])]
ax.set_xlabel("Predicted level (60 min)"); ax.set_ylabel("Actual level"); ax.set_title("Congestion-level confusion (row-normalised)"); save("fig_confusion")
fig,ax=plt.subplots(figsize=(6,3.2)); pos={1:(3,1.2),2:(4,1.4),3:(5,1.6),4:(6,1.8),5:(7,2),6:(1,.3),7:(2,.7),8:(8,.7),9:(2,2.2),10:(3,2.3),11:(4,2.5),12:(5,2.7)}
cc={"Low-congestion":"#27ae60","Moderate commuter":"#f1c40f","Severe commuter":"#c0392b"}
for a,b in [(1,2),(2,3),(3,4),(4,5),(6,7),(7,1),(9,1),(8,5)]: ax.annotate("",pos[b],pos[a],arrowprops=dict(arrowstyle="->",color="gray"))
for a,b in [(1,10),(2,11),(3,12)]: ax.plot(*zip(pos[a],pos[b]),ls=":",c="#2c7fb8")
for s,(x_,y_) in pos.items(): ax.scatter(x_,y_,s=420,c=cc[R["clusters"][s]],zorder=3,edgecolor="k"); ax.text(x_,y_,s,ha="center",va="center",fontsize=8,zorder=4)
ax.set_axis_off(); ax.set_title("Stylised network: node colour = hotspot cluster; dotted = parallel arterial"); save("fig_network")
fig,ax=plt.subplots(figsize=(7,1.9)); ax.set_axis_off(); bx=["Network &\nweather\nsimulator","observations\n.csv (15-min)","Feature\nbuilder\n(lags, graph)","Forecast\nmodels\n15/30/60 min","Hotspots &\neffects","Signal\nsimulation","Paper +\ndashboard"]
for i,t in enumerate(bx): ax.text(i,0,t,ha="center",va="center",fontsize=7,bbox=dict(boxstyle="round,pad=.4",fc="#eaf2f8",ec="#2c7fb8"))
for i in range(6): ax.annotate("",(i+.62,0),(i+.38,0),arrowprops=dict(arrowstyle="->"))
ax.set_xlim(-.6,6.6); ax.set_ylim(-.6,.6); save("fig_pipeline")
json.dump(R,open("results.json","w"),default=float); print(pd.DataFrame(res).round(2).to_string()); print(R["classification"],R["effects"],R["importance"][:5])

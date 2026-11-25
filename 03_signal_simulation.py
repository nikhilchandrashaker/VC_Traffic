"""Two-phase signalised-intersection queue simulation: fixed-time vs Webster-style vs max-pressure (adaptive).
1-second steps, 2 h, 30 replications. Arrival scenarios are stylised (NOT calibrated to the simulated dataset)."""
import numpy as np, pandas as pd, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
S_FLOW, LOST, T, REPS = 0.9, 3, 7200, 30     # veh/s discharge per phase while green, lost s per switch
def arrivals(sc):
    t=np.arange(T); ns=np.full(T,.28); ew=np.full(T,.28)
    if sc=="tidal": ns[:2400],ew[:2400]=.55,.18; ns[-2400:],ew[-2400:]=.18,.55
    return ns,ew
def run(ctrl,sc,seed,gsplit=None,trace=False):
    r=np.random.default_rng(seed); ln,le=arrivals(sc); an=r.poisson(ln); ae=r.poisson(le)
    q=[0,0]; ph=0; since=0; lost=0; cred=0.0; tot=0; area=0; qs=[]
    for t in range(T):
        q[0]+=an[t]; q[1]+=ae[t]; tot+=an[t]+ae[t]
        cap_mult=.6 if (sc=="incident" and 2400<=t<4800) else 1.0
        if lost>0: lost-=1
        else:
            since+=1
            if ctrl=="fixed": sw = since>=(gsplit[ph] if gsplit else 27)
            else:
                o=1-ph; sw = since>=10 and ((q[o]-q[ph]>3) or (q[ph]==0 and q[o]>0) or since>=60)
            if sw: ph=1-ph; since=0; lost=LOST
            else:
                c=S_FLOW*(cap_mult if ph==0 else 1.0); cred+=c; n=min(int(cred),q[ph]); q[ph]-=n; cred-=n
                if q[ph]==0: cred=min(cred,1)
        area+=q[0]+q[1]
        if trace and t%60==0: qs.append(q[0]+q[1])
    return (area/max(tot,1), qs)
rows=[]; trace={}
for sc in ["balanced","tidal","incident"]:
    ln,le=arrivals(sc); w=54*ln.mean()/(ln.mean()+le.mean()); gs=(int(np.clip(w,10,44)),int(54-np.clip(w,10,44)))
    for name,ctrl,gsp in [("Fixed-time (27/27 s)","fixed",None),("Webster-style (demand-split)","fixed",gs),("Max-pressure (adaptive)","mp",None)]:
        d=[];tr=[]
        for s in range(REPS):
            dl,q=run(ctrl,sc,s,gsp,trace=True); d.append(dl); tr.append(q)
        d=np.array(d); rows.append(dict(scenario=sc,controller=name,mean_delay_s=d.mean(),ci95=1.96*d.std(ddof=1)/np.sqrt(REPS),mean_total_queue=np.mean(tr),max_total_queue=np.mean(np.max(tr,1))))
        trace[(sc,name)]=np.mean(tr,0)
df=pd.DataFrame(rows).round(2); df.to_csv("data/simulation_results.csv",index=False); print(df.to_string())
fig,axs=plt.subplots(1,3,figsize=(8,2.8),sharey=True)
for ax,sc in zip(axs,["balanced","tidal","incident"]):
    for (s,n),v in trace.items():
        if s==sc: ax.plot(np.arange(len(v)),v,label=n.split(" (")[0],lw=1)
    ax.set_title(sc); ax.set_xlabel("minutes")
axs[0].set_ylabel("vehicles queued"); axs[0].legend(fontsize=6,frameon=False); plt.tight_layout(); plt.savefig("figures/fig_signal_sim.png",dpi=150)
R=json.load(open("results.json")); R["sim"]=df.to_dict("records"); json.dump(R,open("results.json","w"),default=float)

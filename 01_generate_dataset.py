"""Generate the SIMULATED Ventura County Traffic Congestion dataset (15-min, 2025-01-01..2025-06-30).
Every value is synthetic (mechanistic simulation). Segment names are stylized corridors, not measured sensors."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
S = [(1,"US-101 Ventura (Main St-Seaward)","US-101","freeway",3,65,5.5,0,"in",1.00),
(2,"US-101 Ventura-Oxnard (Victoria Ave)","US-101","freeway",3,65,7.0,0,"in",1.08),
(3,"US-101 Oxnard-Camarillo (Rice Ave)","US-101","freeway",3,65,8.5,0,"in",1.05),
(4,"US-101 Camarillo-Conejo Grade","US-101","freeway",3,65,6.0,0,"in",1.10),
(5,"US-101 Conejo Grade-Thousand Oaks","US-101","freeway",3,65,7.5,0,"mix",0.92),
(6,"SR-126 Santa Paula-Saticoy","SR-126","highway",2,65,9.0,0,"in",0.88),
(7,"SR-126 Saticoy-Ventura","SR-126","highway",2,60,5.0,0,"in",0.97),
(8,"SR-118 Moorpark-Simi Valley","SR-118","highway",2,65,8.0,0,"in",0.95),
(9,"SR-33 Ojai-Ventura","SR-33","highway",2,55,10.0,0,"mix",0.72),
(10,"Telegraph Rd (Ventura)","Telegraph Rd","arterial",2,45,6.0,8,"mix",0.90),
(11,"Victoria Ave (Oxnard-Ventura)","Victoria Ave","arterial",3,45,7.0,10,"mix",0.88),
(12,"Rose Ave (Oxnard)","Rose Ave","arterial",2,40,5.5,9,"mix",0.92)]
seg = pd.DataFrame(S, columns="segment_id segment_name road road_type lanes speed_limit_mph length_mi signals profile peak_load".split())
seg["free_flow_mph"] = np.where(seg.road_type=="arterial", seg.speed_limit_mph*0.72, seg.speed_limit_mph*0.97).round(1)
seg["cap_per_lane_vph"] = np.where(seg.road_type=="arterial", 800, 2000)
seg["has_transit"] = (seg.road_type=="arterial").astype(int)
edges = [(1,2),(2,3),(3,4),(4,5),(6,7),(7,1),(9,1),(8,5)]
alt = [(1,10),(2,11),(3,12)]
seg["downstream_ids"] = [";".join(str(b) for a,b in edges if a==i) for i in seg.segment_id]
seg["upstream_ids"] = [";".join(str(a) for a,b in edges if b==i) for i in seg.segment_id]
ns = len(seg)
ts = pd.date_range("2025-01-01", "2025-06-30 23:45", freq="15min"); T = len(ts)
hr = ts.hour.values + ts.minute.values/60; dow = ts.dayofweek.values; mon = ts.month.values
dnorm = ts.normalize()
hol = np.isin(dnorm.values, pd.to_datetime(["2025-01-01","2025-01-20","2025-02-17","2025-05-26","2025-06-19"]).values)
wkend = dow >= 5
wet_p = {1:.17,2:.18,3:.15,4:.08,5:.03,6:.01}; rain = np.zeros(T)
days = dnorm.unique(); dcode = dnorm.factorize()[0]
for d in days:
    if rng.random() < wet_p[d.month]:
        idx = np.where(dnorm==d)[0]; st = rng.integers(0,70); du = rng.integers(8,60); sc = rng.gamma(2,0.35)
        k = np.arange(du); shape = np.sin(np.pi*(k+.5)/du)**1.5 * rng.gamma(3,.4,du)/1.2
        for j,v in zip(range(st,min(st+du,96)), shape): rain[idx[j]] = sc*v*0.6
rain = np.round(rain,2)
doy = ts.dayofyear.values
temp = 57+0.09*doy+7*np.sin((hr-9)/24*2*np.pi)-3*(rain>0.05)+rng.normal(0,1,T)
vis = np.clip(10-6*np.minimum(rain,1.5)+rng.normal(0,.3,T),0.5,10)
wind = np.clip(rng.gamma(3,2.2,T)+4*(rain>0.5),0,60)
weather = pd.DataFrame(dict(timestamp=ts,precip_mm_15min=rain,temp_f=temp.round(1),visibility_mi=vis.round(1),wind_mph=wind.round(1)))
g = lambda h,m,s: np.exp(-((h-m)/s)**2/2)
am,pm,mid = g(hr,7.5,1.2),g(hr,17,1.5),0.45*g(hr,12.5,2.5)
D = np.zeros((T,ns))
for i,r in seg.iterrows():
    wd = {"in":1.0*am+.55*pm+mid,"out":.55*am+pm+mid,"mix":.85*(am+pm)+mid}[r.profile]
    we = 0.62*g(hr,13,4)
    base = np.where(wkend|hol, we*0.85, wd)*(1+0.1*((dow==4)&(hr>14)))+0.12
    daymul = np.exp(rng.normal(0,.06,len(days)))[dcode]
    ar = np.zeros(T); e = rng.normal(0,.03,T)
    for t in range(1,T): ar[t] = .9*ar[t-1]+e[t]
    D[:,i] = r.peak_load*base*daymul*(1+0.01*(mon-1))*np.exp(ar)
ff = seg.free_flow_mph.values; lanes = seg.lanes.values; capl = seg.cap_per_lane_vph.values; ln = seg.length_mi.values
isart = (seg.road_type=="arterial").values; sid = seg.segment_id.values; ix = {s:i for i,s in enumerate(sid)}
down = [[ix[b] for a,b in edges if a==s] for s in sid]
SP = np.zeros((T,ns)); VC = np.zeros((T,ns)); VOL = np.zeros((T,ns)); INC = np.zeros((T,ns),int); Q = np.zeros((T,ns))
prev = ff.copy(); rem = np.zeros(ns,int); mult = np.ones(ns); incs = []
types = ["collision","breakdown","debris","lane_closure"]
for t in range(T):
    r = rain[t]
    capm = 1-.05*(r>.05)-.10*(r>.5)-.08*(r>1.5); ffm = 1-.03*(r>.05)-.05*(r>.5)
    for i in range(ns):
        if rem[i]==0 and rng.random() < 1.5e-4*ln[i]*(1+1.2*(r>.1)+.8*min(D[t,i],1.2)):
            sev = rng.choice([1,2,3],p=[.5,.35,.15]); du = int(np.clip(rng.lognormal(np.log(3),.6)*sev**.3,1,12))
            rem[i]=du; mult[i]={1:.8,2:.55,3:.3}[sev]
            incs.append((len(incs)+1,sid[i],ts[t],du*15,rng.choice(types,p=[.35,.35,.15,.15]),sev,mult[i]))
    cong = 1-prev/ff
    spill = np.array([cong[d].mean() if d else 0 for d in down])
    dem = D[t].copy()
    for a,b in alt: dem[ix[b]] *= 1+.25*cong[ix[a]]
    im = np.where(rem>0,mult,1.0); INC[t]=(rem>0)
    vc = dem/(capm*im*(1-.3*spill)); rem = np.maximum(rem-1,0)
    sp = ff*ffm/(1+.6*vc**5); sp = .6*sp+.4*prev
    sp = np.clip(sp*np.exp(rng.normal(0,.02,ns)),3,ff+4); prev = sp
    SP[t]=sp; VC[t]=vc
    flow = lanes*capl*.25*np.minimum(vc,1)*(1-.1*np.maximum(vc-1,0))
    VOL[t] = rng.poisson(np.maximum(flow,0))
    Q[t] = np.clip(2500*np.maximum(vc-.95,0)*np.sqrt(lanes),0,15000)
tid = np.repeat(np.arange(T),ns); sidx = np.tile(np.arange(ns),T)
o = pd.DataFrame({"timestamp":ts[tid],"segment_id":sid[sidx]})
o["volume_veh_15min"]=VOL.ravel().astype(int); sp=SP.ravel(); o["avg_speed_mph"]=sp.round(1)
o["density_veh_per_mile_per_lane"]=(VOL.ravel()*4/np.maximum(sp,3)/lanes[sidx]).round(1)
o["travel_time_index"]=(ff[sidx]/sp).round(3); o["queue_length_ft"]=Q.ravel().round(0).astype(int)
ratio = sp/ff[sidx]; o["congestion_level"]=np.select([ratio>.85,ratio>.70,ratio>.55,ratio>.40],[0,1,2,3],4)
o["incident_active"]=INC.ravel(); o["is_weekend"]=wkend[tid].astype(int); o["is_holiday"]=hol[tid].astype(int)
pk = (((hr>=6.5)&(hr<9))|((hr>=15.5)&(hr<18.5)))[tid]
o["is_peak_hour"]=(pk & (o.is_weekend.values==0)).astype(int)
mpg = np.clip(26*(1-.55*np.maximum(0,(45-sp)/45))*np.where(sp>65,.95,1),8,30)
fuel = o.volume_veh_15min*ln[sidx]/mpg; o["fuel_gal"]=fuel.round(2); o["co2_kg"]=(fuel*8.887).round(1)
x = np.minimum(VC.ravel(),.95); C=100; gC=.5
o["signal_delay_s_per_veh"]=np.where(isart[sidx],.5*C*(1-gC)**2/(1-x*gC),np.nan).round(1)
o["bus_delay_min"]=np.where(isart[sidx],ln[sidx]*(60/sp-60/ff[sidx]),np.nan).round(2)
o["bus_boardings_15min"]=np.where(isart[sidx],rng.poisson(8+22*np.minimum(D.ravel(),1.2)),np.nan)
o["precip_mm_15min"]=rain[tid]
o.to_csv("data/observations.csv",index=False); weather.to_csv("data/weather.csv",index=False)
seg.to_csv("data/segments.csv",index=False)
pd.DataFrame(incs,columns="incident_id segment_id start_time duration_min incident_type severity capacity_multiplier".split()).to_csv("data/incidents.csv",index=False)
sg=[(f"S{r.segment_id}-{k+1}",r.segment_id,int(rng.choice([90,100,110,120])),int(rng.integers(0,100))) for _,r in seg[seg.road_type=="arterial"].iterrows() for k in range(r.signals)]
sg=pd.DataFrame(sg,columns="signal_id segment_id cycle_s offset_s".split())
sg["main_green_s"]=(sg.cycle_s*.5).astype(int)-3; sg["side_green_s"]=sg.cycle_s-sg.main_green_s-6; sg["control_type"]="pretimed"
sg.to_csv("data/signals.csv",index=False)
print(o.shape, "incidents:",len(incs), "rain intervals:",int((rain>0.05).sum()))

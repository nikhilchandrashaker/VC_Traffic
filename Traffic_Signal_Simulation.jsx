import { useState, useRef, useEffect, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

// Interactive twin of src/03_signal_simulation.py: same rules, 1 simulated second per step, 2 simulated hours.
// Stylised two-phase intersection (NS vs EW). Arrival rates are NOT calibrated to the dataset.
const T = 7200, S_FLOW = 0.9, LOST = 3;
const C = { road: "#1f2a33", line: "#f2c230", red: "#d64545", green: "#2f9e6e", paper: "#f3f5f6", mute: "#5b6772", blue: "#2c7fb8" };
const SCEN = {
  balanced: "Balanced demand: both directions 0.28 veh/s",
  tidal: "Tidal: north-south heavy for 40 min, then balanced, then east-west heavy",
  incident: "Incident: north-south capacity cut 40% from minute 40 to 80",
};
const rates = (sc, t) => (sc === "tidal" ? (t < 2400 ? [0.55, 0.18] : t >= T - 2400 ? [0.18, 0.55] : [0.28, 0.28]) : [0.28, 0.28]);
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function poisson(l, r) { const L = Math.exp(-l); let k = 0, p = 1; do { k++; p *= r(); } while (p > L); return k - 1; }
function arrivalsFor(sc, seed) { const r = rng(seed), an = new Uint8Array(T), ae = new Uint8Array(T); for (let t = 0; t < T; t++) { const [a, b] = rates(sc, t); an[t] = poisson(a, r); ae[t] = poisson(b, r); } return { an, ae }; }
const newCtl = (type) => ({ type, q: [0, 0], ph: 0, since: 0, lost: 0, cred: 0, tot: 0, area: 0, peak: 0 });
function step(s, t, an, ae, sc) {
  s.q[0] += an; s.q[1] += ae; s.tot += an + ae;
  const cap = sc === "incident" && t >= 2400 && t < 4800 ? 0.6 : 1;
  if (s.lost > 0) s.lost--;
  else {
    s.since++;
    const o = 1 - s.ph;
    const sw = s.type === "fixed" ? s.since >= 27 : s.since >= 10 && (s.q[o] - s.q[s.ph] > 3 || (s.q[s.ph] === 0 && s.q[o] > 0) || s.since >= 60);
    if (sw) { s.ph = o; s.since = 0; s.lost = LOST; }
    else { s.cred += S_FLOW * (s.ph === 0 ? cap : 1); const n = Math.min(Math.floor(s.cred), s.q[s.ph]); s.q[s.ph] -= n; s.cred -= n; if (s.q[s.ph] === 0) s.cred = Math.min(s.cred, 1); }
  }
  s.area += s.q[0] + s.q[1]; s.peak = Math.max(s.peak, s.q[0] + s.q[1]);
}

function Lamp({ on, color }) { return <circle r="6" fill={on ? color : "#3a4650"} />; }
function Intersection({ s, title, accent }) {
  const go = [s.lost === 0 && s.ph === 0, s.lost === 0 && s.ph === 1];
  const cars = (n, dir) => Array.from({ length: Math.min(n, 24) }, (_, i) => dir === "ns"
    ? <rect key={i} x={118} y={106 - i * 9} width={12} height={7} rx={2} fill={C.blue} />
    : <rect key={i} x={106 - i * 13} y={150} width={11} height={12} rx={2} fill={C.line} stroke={C.road} strokeWidth=".5" />);
  return (
    <div className="rounded-lg bg-white p-3" style={{ border: "1px solid #d9dfe4" }}>
      <h3 className="mb-1 text-sm font-semibold" style={{ borderLeft: `4px solid ${accent}`, paddingLeft: 8 }}>{title}</h3>
      <svg viewBox="0 0 300 300" className="w-full" role="img" aria-label={`${title}: ${s.q[0]} vehicles waiting north-south, ${s.q[1]} east-west`}>
        <rect width="300" height="300" fill="#e9eef1" />
        <rect x="108" y="0" width="38" height="300" fill={C.road} /><rect x="0" y="136" width="300" height="38" fill={C.road} />
        <line x1="127" y1="0" x2="127" y2="136" stroke="#fff" strokeDasharray="6 6" /><line x1="0" y1="155" x2="108" y2="155" stroke="#fff" strokeDasharray="6 6" />
        {cars(s.q[0], "ns")}{cars(s.q[1], "ew")}
        {s.q[0] > 24 && <text x="136" y="40" fontSize="10" fill={C.road}>+{s.q[0] - 24} more</text>}
        {s.q[1] > 24 && <text x="4" y="190" fontSize="10" fill={C.road}>+{s.q[1] - 24} more</text>}
        <g transform="translate(160,110)"><Lamp on={go[0]} color={C.green} /><g transform="translate(0,16)"><Lamp on={!go[0]} color={C.red} /></g></g>
        <g transform="translate(90,180)"><Lamp on={go[1]} color={C.green} /><g transform="translate(16,0)"><Lamp on={!go[1]} color={C.red} /></g></g>
        <text x="190" y="30" fontSize="11" fill={C.mute}>North-south waiting: {s.q[0]}</text>
        <text x="190" y="262" fontSize="11" fill={C.mute}>East-west waiting: {s.q[1]}</text>
        <text x="190" y="278" fontSize="11" fill={C.mute}>{s.lost > 0 ? "Clearing intersection" : `Green: ${s.ph === 0 ? "north-south" : "east-west"}`}</text>
      </svg>
      <dl className="mt-1 grid grid-cols-3 gap-2 text-center text-xs">
        <div><dt style={{ color: C.mute }}>Average delay</dt><dd className="text-lg font-bold">{s.tot ? (s.area / s.tot).toFixed(1) : "0.0"} s</dd></div>
        <div><dt style={{ color: C.mute }}>Waiting now</dt><dd className="text-lg font-bold">{s.q[0] + s.q[1]}</dd></div>
        <div><dt style={{ color: C.mute }}>Longest queue</dt><dd className="text-lg font-bold">{s.peak}</dd></div>
      </dl>
    </div>
  );
}

export default function SignalSimulation() {
  const [sc, setSc] = useState("tidal");
  const [seed, setSeed] = useState(7);
  const [speed, setSpeed] = useState(20);
  const [running, setRunning] = useState(false);
  const [view, setView] = useState({ t: 0, f: newCtl("fixed"), m: newCtl("mp"), hist: [] });
  const sim = useRef(null);
  const reset = useCallback((scn = sc, sd = seed) => {
    sim.current = { sc: scn, arr: arrivalsFor(scn, sd), t: 0, f: newCtl("fixed"), m: newCtl("mp"), hist: [] };
    setView({ t: 0, f: { ...sim.current.f, q: [0, 0] }, m: { ...sim.current.m, q: [0, 0] }, hist: [] });
  }, [sc, seed]);
  useEffect(() => { reset(); setRunning(false); }, [sc, seed]); // eslint-disable-line
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      const S = sim.current;
      for (let i = 0; i < speed && S.t < T; i++) {
        step(S.f, S.t, S.arr.an[S.t], S.arr.ae[S.t], S.sc); step(S.m, S.t, S.arr.an[S.t], S.arr.ae[S.t], S.sc); S.t++;
        if (S.t % 60 === 0) S.hist.push({ min: S.t / 60, Fixed: S.f.q[0] + S.f.q[1], "Max-pressure": S.m.q[0] + S.m.q[1] });
      }
      setView({ t: S.t, f: { ...S.f, q: [...S.f.q] }, m: { ...S.m, q: [...S.m.q] }, hist: [...S.hist] });
      if (S.t >= T) setRunning(false);
    }, 100);
    return () => clearInterval(id);
  }, [running, speed]);

  const done = view.t >= T;
  const df = view.f.tot ? view.f.area / view.f.tot : 0, dm = view.m.tot ? view.m.area / view.m.tot : 0;
  const clock = `${String(Math.floor(view.t / 3600)).padStart(1, "0")}:${String(Math.floor((view.t % 3600) / 60)).padStart(2, "0")}:${String(view.t % 60).padStart(2, "0")}`;
  const Btn = ({ children, onClick, on }) => <button onClick={onClick} className="rounded px-3 py-1.5 text-sm" style={{ background: on ? C.road : "#e8ecef", color: on ? "#fff" : C.road }}>{children}</button>;

  return (
    <div className="min-h-screen p-5" style={{ background: C.paper, color: C.road, fontFamily: "system-ui, sans-serif" }}>
      <h1 className="text-2xl font-bold">Fixed-time vs adaptive signals</h1>
      <p className="mb-3 max-w-2xl text-sm" style={{ color: C.mute }}>Both intersections get the same cars at the same moments. The left one switches every 27 seconds. The right one switches when the other direction has more cars waiting.</p>
      <div className="mb-3 rounded px-3 py-2 text-sm" style={{ background: "#fff3cd", color: "#664d03" }}><b>Stylised model.</b> One two-phase intersection with made-up arrival rates, not calibrated to the Ventura dataset.</div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        {Object.keys(SCEN).map((k) => <Btn key={k} on={sc === k} onClick={() => setSc(k)}>{k[0].toUpperCase() + k.slice(1)}</Btn>)}
        <span className="mx-2 h-5 w-px" style={{ background: "#c5ccd2" }} />
        <Btn on={running} onClick={() => (done ? (reset(), setRunning(true)) : setRunning(!running))}>{running ? "Pause" : done ? "Run again" : view.t ? "Resume" : "Start"}</Btn>
        <Btn onClick={() => { setRunning(false); reset(); }}>Reset</Btn>
        <Btn onClick={() => setSeed(seed + 1)}>New random traffic</Btn>
        <label className="ml-2 text-sm">Speed {speed}x <input type="range" min="1" max="60" value={speed} onChange={(e) => setSpeed(+e.target.value)} /></label>
      </div>
      <p className="mb-3 text-sm" style={{ color: C.mute }}>{SCEN[sc]}. Simulated clock <b style={{ color: C.road }}>{clock}</b> of 2:00:00.</p>

      <div className="grid gap-4 md:grid-cols-2">
        <Intersection s={view.f} title="Fixed-time (27 s green each way)" accent={C.red} />
        <Intersection s={view.m} title="Max-pressure (adaptive)" accent={C.green} />
      </div>

      <section className="mt-4 rounded-lg bg-white p-4" style={{ border: "1px solid #d9dfe4" }}>
        <h2 className="mb-2 text-sm font-semibold">Vehicles waiting over time</h2>
        <div style={{ height: 220 }}>
          <ResponsiveContainer><LineChart data={view.hist}><CartesianGrid stroke="#e8ecef" /><XAxis dataKey="min" type="number" domain={[0, 120]} tick={{ fontSize: 11 }} label={{ value: "minutes", position: "insideBottomRight", offset: -2, fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
            <Line dataKey="Fixed" stroke={C.red} dot={false} strokeWidth={2} isAnimationActive={false} /><Line dataKey="Max-pressure" stroke={C.green} dot={false} strokeWidth={2} isAnimationActive={false} /></LineChart></ResponsiveContainer>
        </div>
        {done && <p className="mt-2 text-sm"><b>Finished.</b> Average delay was {df.toFixed(1)} s with fixed timing and {dm.toFixed(1)} s with max-pressure ({df > 0 ? Math.round((1 - dm / df) * 100) : 0}% lower). One run is noisy; the report averages 30 runs per scenario.</p>}
      </section>
    </div>
  );
}

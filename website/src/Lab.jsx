import { useEffect, useId, useMemo, useRef, useState } from "react";

const modes = {
  eeg: { title:"EEG", levels:[["burst","Amplitude transient"],["clean","No transient"]], filters:[["standard","0.1 Hz high-pass"],["high","1 Hz high-pass"]] },
  emg: { title:"EMG", levels:[["normal","Standard amplitude"],["strong","Double amplitude"]], filters:[["standard","450 Hz low-pass"],["low","120 Hz low-pass"]] },
};
const bands = [["delta","δ","0.5–4"],["theta","θ","4–8"],["alpha","α","8–13"],["beta","β","13–30"],["gamma","γ","30–45"]];
const nf = (n,d=2) => n.toLocaleString("en", {minimumFractionDigits:d,maximumFractionDigits:d});
const power = n => n === 0 ? "0" : Math.abs(n)<.01 ? n.toExponential(2) : nf(n);
const asset = new URL(import.meta.env.BASE_URL, document.baseURI);
const load = (id, signal) => fetch(new URL("scenarios/" + id + ".json", asset), {signal}).then(r => {
  if (!r.ok) throw new Error("Scenario could not be loaded.");
  return r.json();
});

function Chart({ kind, data, channel }) {
  const spectrum = kind === "spectrum";
  const uid = useId();
  const plot = useRef(null);
  const [width, setWidth] = useState(740);
  useEffect(() => {
    const box = plot.current;
    const measure = () => setWidth(Math.max(225, Math.round(box.clientWidth)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(box);
    return () => observer.disconnect();
  }, []);
  const [cursor, setCursor] = useState(null);
  const [visibility, setVisibility] = useState([true,true]);
  const { x, ys, xTicks, yTicks, xLabel, yLabel, fitX, fitY, paths } = useMemo(() => {
    const x = spectrum ? data.freqs : channel.raw.map((_, i) => data.start + i / data.sfreq);
    const ys = spectrum ? [channel.rawPsd,channel.psd] : [channel.raw,channel.processed];
    const xLimit = spectrum ? x.at(-1) : data.start + 1;
    const tickCount = width < 410 ? 4 : 6;
    const xTicks = Array.from({length:tickCount}, (_,i) => x[0]+i*(xLimit-x[0])/(tickCount-1));
    const base = spectrum ? Math.max(...ys.flat()) : Math.max(...ys.flat().map(Math.abs));
    const max = spectrum ? Math.ceil(Math.log10(base)) : Math.ceil(base/20)*20;
    const min = spectrum ? max-8 : -max;
    const fitX = val => 58 + (width-80) * (val - x[0]) / (xLimit - x[0]);
    const fitY = val => 172 - 148 * ((spectrum ? Math.log10(Math.max(10**min, val)) : val)-min)/(max-min);
    const paths = ys.map(row => row.map((val,i) => (i?"L":"M")+fitX(x[i]).toFixed(2)+" "+fitY(val).toFixed(2)).join(""));
    return {x,ys,xTicks,yTicks:Array.from({length:5},(_,i)=>min+i*(max-min)/4),
      xLabel:spectrum?"Frequency (Hz)":"Time (s)",yLabel:spectrum?"PSD (µV²/Hz)":"Amplitude (µV)",fitX,fitY,paths};
  }, [data,channel,spectrum,width]);
  const active = cursor == null ? null : Math.min(cursor,x.length-1);
  const title = spectrum ? "Welch spectrum" : "Signal trace";
  const right = width - 22;
  function pointer(e) {
    const box = e.currentTarget.getBoundingClientRect();
    const relative = (((e.clientX-box.left)/box.width)*width-58)/(width-80);
    setCursor(Math.max(0, Math.min(x.length-1, Math.round(relative*(spectrum ? x.length-1 : data.sfreq)))));
  }
  return <section className="chart">
    <div className="chart-head"><h4>{title}</h4><span>{yLabel}</span></div>
    <div className="chart-scroll" ref={plot}>
      <svg viewBox={["0","0",width,"218"].join(" ")} preserveAspectRatio="none" role="img" aria-labelledby={uid} onPointerDown={pointer} onPointerMove={pointer} onPointerLeave={()=>setCursor(null)}>
        <title id={uid}>{title} for synthetic {data.mode.toUpperCase()} {channel.name}. Raw and processed values share an axis. {spectrum && "Vertical axis is logarithmic."}</title>
        {yTicks.map(tick => {const value=spectrum?10**tick:tick; return <g key={tick}>
          <line x1="58" x2={right} y1={fitY(value)} y2={fitY(value)} />
          <text x="49" y={fitY(value)+4} textAnchor="end">{spectrum ? "10^"+tick : nf(tick,0)}</text>
        </g>})}
        {xTicks.map(tick=><g key={tick}><line x1={fitX(tick)} x2={fitX(tick)} y1="24" y2="172"/>
          <text x={fitX(tick)} y="192" textAnchor="middle">{nf(tick,spectrum?0:1)}</text></g>)}
        <text x={(58+right)/2} y="213" textAnchor="middle">{xLabel}</text>
        {paths.map((path,i)=>visibility[i]&&<path key={i} d={path} className={i?"processed":"raw"} vectorEffect="non-scaling-stroke"/>)}
        {active!=null&&<line className="cursor" x1={fitX(x[active])} x2={fitX(x[active])} y1="24" y2="172"/>}
      </svg>
    </div>
    <div className="chart-controls">
      <button type="button" aria-pressed={visibility[0]} className="legend raw-key" onClick={()=>setVisibility(([a,b])=>[!a,b])}>Raw</button>
      <button type="button" aria-pressed={visibility[1]} className="legend filtered-key" onClick={()=>setVisibility(([a,b])=>[a,!b])}>Processed</button>
      <label className="inspect">Inspect {spectrum?"frequency":"time"}
        <input type="range" min="0" max={x.length-1} value={active ?? 0} onChange={e=>setCursor(+e.target.value)} /></label>
    </div>
    <output className="readout">{active!=null ? <>{nf(x[active],spectrum?2:3)} {spectrum?"Hz":"s"} · raw {power(ys[0][active])} · processed {power(ys[1][active])} {spectrum?"µV²/Hz":"µV"}</> : <>Select a point or use the inspection slider to read exact values.</>}</output>
  </section>;
}

export default function Lab() {
  const [mode, setMode] = useState("eeg");
  const [level, setLevel] = useState("burst");
  const [preset, setPreset] = useState("standard");
  const [channelIndex, setChannel] = useState(0);
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState(null);
  const id = mode+"-"+level+"-"+preset;
  useEffect(() => {
    const controller = new AbortController();
    load(id,controller.signal).then(data=> {
      if (data.provenance !== "synthetic" || data.mode !== mode || data.level !== level || data.preset !== preset) throw new Error("Unexpected scenario");
      if (!controller.signal.aborted) setState({id,retry,data});
    }).catch(()=>{if(!controller.signal.aborted) setState({id,retry,error:true});});
    return () => controller.abort();
  }, [id,retry,mode,level,preset]);
  const current = state?.id===id&&state.retry===retry ? state : null;
  const data = current?.data;
  const channel = data?.channels[channelIndex];
  const settings = modes[mode];
  function switchMode(next) {
    setMode(next); setLevel(modes[next].levels[0][0]); setPreset("standard"); setChannel(0);
  }
  return <div className="lab">
    <div className="lab-top"><span className="machine-id">BIO / SIGNAL CONSOLE</span><span className="synthetic"><i/> Synthetic data</span></div>
    <div className="lab-body">
      <aside className="settings" aria-label="Scenario controls">
        <h3>Experiment setup</h3>
        <div className="segmented" aria-label="Signal type">{Object.keys(modes).map(m=>
          <button key={m} type="button" aria-pressed={mode===m} onClick={()=>switchMode(m)}>{m.toUpperCase()}</button>)}</div>
        <label>{mode==="eeg"?"Signal condition":"Signal amplitude"}<select value={level} onChange={e=>setLevel(e.target.value)}>
          {settings.levels.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
        <label>Filter preset<select value={preset} onChange={e=>setPreset(e.target.value)}>
          {settings.filters.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
        <label>Channel<select value={channelIndex} onChange={e=>setChannel(+e.target.value)}>
          {Array.from({length:mode==="eeg"?8:1}, (_,i)=><option value={i} key={i}>Ch{i+1}</option>)}</select></label>
        <div className="instrument-meta"><div><span>Sample rate</span><strong>{mode==="eeg"?"250":"1,000"} Hz</strong></div><div><span>Analysis length</span><strong>12 s</strong></div><div><span>Welch window</span><strong>{mode==="eeg"?4:2} s</strong></div></div>
        <p className="fine">All scenarios are generated by BioSignal Lab’s Python engine. This public lab accepts no recordings.</p>
      </aside>
      <div className="lab-view" aria-busy={!current}>
        {!current&&<p className="lab-message" role="status">Loading synthetic scenario…</p>}
        {current?.error&&<div className="lab-message" role="alert">The scenario could not be loaded. <button type="button" onClick={()=>setRetry(n=>n+1)}>Retry</button></div>}
        {channel&&<>
          <div className="status-row" role="status">{mode.toUpperCase()} / {channel.name} <span>Engine v{data.engine}</span></div>
          <Chart key={id+":"+channel.name+":wave"} data={data} channel={channel}/>
          <Chart key={id+":"+channel.name+":psd"} kind="spectrum" data={data} channel={channel}/>
          <div className="analysis" aria-label="Quality summaries">
            <div><span>Processed RMS</span><strong>{nf(channel.quality.rms_uv)} <small>µV</small></strong></div>
            <div><span>Raw RMS</span><strong>{nf(channel.rawQuality.rms_uv)} <small>µV</small></strong></div>
            <div><span>Raw candidate windows</span><strong>{channel.candidates.length}</strong></div>
          </div>
          {mode==="eeg" ? <section className="band-panel"><h4>Processed EEG band power</h4>
            <p className="fine">Relative to integrated 0.5–45 Hz power.</p>
            {bands.map(([name,symbol,range])=>{const row=channel.bands[0]; const fraction=row[name+"_relative"];return <div className="band" key={name}>
              <span>{symbol} {name} <small>{range} Hz</small></span><progress aria-label={name+" relative power"} value={fraction??0} max="1"/><span>{power(row[name+"_uv2"])} µV²</span>
            </div>;})}</section> : <p className="emg-note">EMG summary uses broadband power and time-domain amplitude. EEG bands are omitted.</p>}
          <details><summary>Parameters and interpretation notes</summary>
            <p>Seed {data.seed} · NumPy {data.numpy} · SciPy {data.scipy}. The trace shows a 1 s excerpt. Welch uses the full 12 s, Hann windows, 50% overlap and constant detrending. The spectra share a logarithmic axis. Axes are rescaled for each scenario.</p>
            <p>High-pass {data.config.highpass_hz} Hz · Low-pass {data.config.lowpass_hz??"off"} {data.config.lowpass_hz?"Hz":""} · Notch {data.config.notch_hz} Hz · Candidate windows are review cues.</p>
            <p>Raw candidate windows: {channel.candidates.length ? channel.candidates.map(x=>x.start_s+"–"+x.end_s+" s").join(", ") : "none flagged"}.</p><ul>{data.warnings.map(w=><li key={w}>{w}</li>)}</ul>
          </details>
          <a className="text-link data-link" href={new URL("scenarios/"+id+".json",asset)} download>Download this synthetic scenario (JSON)</a>
        </>}
      </div>
    </div>
  </div>;
}

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { asset, fetchSynthetic } from "./assets";
import Spectrogram from "./Spectrogram";

const modes = {
  eeg: { title:"EEG", levels:[["burst","Amplitude transient"],["clean","No transient"]], filters:[["standard","0.1 Hz high-pass"],["high","1 Hz high-pass"],["low","35 Hz low-pass"],["no-notch","50 Hz notch off"]] },
  emg: { title:"EMG", levels:[["normal","Standard amplitude"],["strong","Double amplitude"]], filters:[["standard","450 Hz low-pass"],["low","120 Hz low-pass"]] },
};
const bands = [["delta","δ","0.5–4"],["theta","θ","4–8"],["alpha","α","8–13"],["beta","β","13–30"],["gamma","γ","30–45"]];
const nf = (n,d=2) => n.toLocaleString("en", {minimumFractionDigits:d,maximumFractionDigits:d});
const power = n => n === 0 ? "0" : Math.abs(n)<.01 ? n.toExponential(2) : nf(n);
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

const colors=["#8ce9ce","#bbabff","#90c0f3","#efa5c1","#aade91","#dfbf8b","#8dd1ec","#cbc3f1"];

function Strip({data,selected,onSelect}){
  const peak=Math.max(...data.channels.flatMap(c=>[...c.raw,...c.processed]).map(Math.abs));
  const height=data.channels.length*38+27;
  const path=(seq,y)=>seq.map((v,i)=>(i?"L":"M")+(54+620*i/data.sfreq).toFixed(1)+" "+(y-v*16/peak).toFixed(1)).join("");
  return <section className="montage">
    <div><h4>Channel overview</h4><span>Processed · common scale ±{Math.ceil(peak).toLocaleString("en")} µV</span></div>
    <svg className="strip-svg" viewBox={"0 0 716 "+height} role="img" aria-label="Overview of all processed synthetic EEG channels on one shared amplitude scale.">
      {data.channels.map(({name,processed},i)=>{
        const y=19+38*i;
        return <g key={name} onClick={()=>onSelect(i)}>
          <rect x="6" y={y-17} width="704" height="34" rx="3" fill={selected===i?"#263655":"transparent"}/>
          <path d={`M54 ${y}H674`} stroke="#4b6086" strokeWidth=".6"/>
          <text x="14" y={y+4} fill={colors[i]}>{name}</text>
          <path className="story-trace" stroke={colors[i]} d={path(processed,y)}/>
        </g>;
      })}
      <text x="54" y={height-7}>4.5 s</text><text x="674" y={height-7} textAnchor="end">5.5 s</text>
    </svg>
    <div className="channel-tabs" aria-label="Channels">{data.channels.map((c,i)=><button key={c.name} type="button"
      aria-pressed={selected===i} onClick={()=>onSelect(i)}>{c.name}</button>)}</div>
  </section>;
}

export default function Lab() {
  const [mode,setMode]=useState("eeg");
  const [level,setLevel]=useState("burst");
  const [preset,setPreset]=useState("standard");
  const [rate,setRate]=useState(250);
  const [channelIndex,setChannel]=useState(0);
  const [view,setView]=useState("trace");
  const [retry,setRetry]=useState(0);
  const [state,setState]=useState(null);
  const id=[mode,level,preset,rate].join("-");
  useEffect(()=>{
    const controller=new AbortController();
    fetchSynthetic(id,controller.signal).then(data=>{
      if(data.mode!==mode||data.level!==level||data.preset!==preset||data.sfreq!==rate) throw new Error("Unexpected scenario");
      if(!controller.signal.aborted) setState({id,retry,data});
    }).catch(()=>{if(!controller.signal.aborted) setState({id,retry,error:true});});
    return()=>controller.abort();
  },[id,retry,mode,level,preset,rate]);
  const current=state?.id===id&&state.retry===retry?state:null;
  const data=current?.data;
  const channel=data?.channels[channelIndex];
  const settings=modes[mode];
  function switchMode(next) {
    if(next===mode) return;
    setMode(next);setLevel(modes[next].levels[0][0]);setPreset("standard");
    setChannel(0);setRate(next==="eeg"?250:1000);
  }
  return <div className="lab">
    <div className="lab-top"><span className="machine-id">Signal workbench</span><span className="synthetic"><i/> Synthetic data</span></div>
    <div className="lab-body">
      <aside className="settings" aria-label="Scenario controls">
        <h3>Experiment setup</h3>
        <div className="segmented" aria-label="Signal type">{Object.keys(modes).map(m=>
          <button key={m} type="button" aria-pressed={mode===m} onClick={()=>switchMode(m)}>{m.toUpperCase()}</button>)}</div>
        <label>{mode==="eeg"?"Signal condition":"Signal amplitude"}<select value={level} onChange={e=>setLevel(e.target.value)}>
          {settings.levels.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
        <label>Sampling frequency<select value={rate} onChange={e=>setRate(+e.target.value)}>
          {(mode==="eeg"?[128,250,500]:[1000,2000]).map(v=><option key={v} value={v}>{v.toLocaleString("en")} Hz</option>)}</select></label>
        <label>Filter preset<select value={preset} onChange={e=>setPreset(e.target.value)}>
          {settings.filters.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
        <label>Channel<select value={channelIndex} onChange={e=>setChannel(+e.target.value)}>
          {Array.from({length:mode==="eeg"?8:1},(_,i)=><option key={i} value={i}>Ch{i+1}</option>)}</select></label>
        <div className="instrument-meta"><div><span>Samples</span><strong>{(12*rate).toLocaleString("en")}</strong></div><div><span>Duration</span><strong>12 s</strong></div><div><span>Welch window</span><strong>{mode==="eeg"?4:2} s</strong></div></div>
        <p className="fine">This console reads a finite catalogue computed by BioSignal Lab’s Python engine. Each sample rate generates a new synthetic series.</p>
      </aside>
      <div className="lab-view" aria-busy={!current}>
        {!current&&<p className="lab-message" role="status">Loading synthetic scenario…</p>}
        {current?.error&&<div className="lab-message" role="alert">The scenario could not be loaded. <button type="button" onClick={()=>setRetry(n=>n+1)}>Retry</button></div>}
        {channel&&<>
          <div className="status-row" role="status">{mode.toUpperCase()} / {channel.name} <span>{rate.toLocaleString("en")} Hz · Engine v{data.engine}</span></div>
          <div className="mode-switch" aria-label="Analysis view">
            {[["trace","Trace"],["spectrum","Spectrum"],["time-frequency","Spectrogram"]].map(([key,label])=>
              <button key={key} type="button" aria-pressed={view===key} onClick={()=>setView(key)}>{label}</button>)}
          </div>
          {view==="trace"&&mode==="eeg"&&<Strip data={data} selected={channelIndex} onSelect={setChannel}/>}
          {view==="trace"&&<Chart key={id+channel.name+":trace"} data={data} channel={channel}/>}
          {view==="spectrum"&&<Chart key={id+channel.name+":welch"} kind="spectrum" data={data} channel={channel}/>}
          {view==="time-frequency"&&<Spectrogram key={id} id={id} channel={channelIndex}/>}
          <div className="analysis" aria-label="Quality summaries">
            <div><span>Processed RMS</span><strong>{nf(channel.quality.rms_uv)} <small>µV</small></strong></div>
            <div><span>Raw RMS</span><strong>{nf(channel.rawQuality.rms_uv)} <small>µV</small></strong></div>
            <div><span>{mode==="eeg"?"Raw candidate windows":"Median frequency"}</span><strong>{mode==="eeg"?channel.candidates.length:<>{nf(channel.quality.emg_median_frequency_hz,1)} <small>Hz</small></>}</strong></div>
          </div>
          {mode==="eeg"?<section className="band-panel"><h4>Processed EEG band power</h4>
            <p className="fine">Relative to integrated 0.5–45 Hz power.</p>
            {bands.map(([name,symbol,range])=>{const row=channel.bands[0];const fraction=row[name+"_relative"];return <div className="band" key={name}>
              <span>{symbol} {name} <small>{range} Hz</small></span><progress aria-label={name+" relative power"} value={fraction??0} max="1"/>
              <span>{power(row[name+"_uv2"])} µV²</span></div>;})}</section>:
            <p className="emg-note">EMG amplitude and median frequency depend on acquisition and analysis settings.</p>}
          <details><summary>Parameters and interpretation</summary>
            <p>Seed {data.seed} · NumPy {data.numpy} · SciPy {data.scipy}. Traces show a 1 s excerpt. Welch uses the full 12 s with Hann windows, 50% overlap and constant detrending. Axis ranges can change with the scenario.</p>
            <p>High-pass {data.config.highpass_hz} Hz · Low-pass {data.config.lowpass_hz==null?"off":data.config.lowpass_hz+" Hz"} · Notch {data.config.notch_hz==null?"off":data.config.notch_hz+" Hz"}.</p>
            <p>Raw candidate windows: {channel.candidates.length?channel.candidates.map(x=>x.start_s+"–"+x.end_s+" s").join(", "):"none flagged"}. These are heuristic review cues.</p>
            <ul>{data.warnings.map(w=><li key={w}>{w}</li>)}</ul>
          </details>
          <a className="text-link data-link" href={asset("scenarios/"+id+".json")} download>Download this synthetic scenario (JSON)</a>
        </>}
      </div>
    </div>
  </div>;
}

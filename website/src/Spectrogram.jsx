import {useEffect, useRef, useState} from "react";
import {fetchSynthetic} from "./assets";

const stops=[[12,20,48],[48,56,113],[104,81,175],[94,166,198],[172,240,215]];
function color(normalized) {
  const t=Math.min(.999999,Math.max(0,normalized))*(stops.length-1);
  const i=Math.floor(t);
  return stops[i].map((v,j)=>Math.round(v+(stops[i+1][j]-v)*(t-i)));
}
function Heatmap({data,channel}) {
  const canvas=useRef(null);
  const [timeIndex,setTimeIndex]=useState(0);
  const [freqIndex,setFreqIndex]=useState(0);
  const values=data.density[channel];
  const peak=Math.max(...values.flat());
  const top=Math.ceil(Math.log10(peak));
  const bottom=top-7;
  const frequency=data.freqs[freqIndex];
  const time=data.times[timeIndex];
  const density=values[freqIndex][timeIndex];
  useEffect(()=>{
    const context=canvas.current.getContext("2d");
    if(!context) return;
    const w=data.times.length,h=data.freqs.length;
    const pixels=context.createImageData(w,h);
    for(let f=0;f<h;f++) for(let t=0;t<w;t++){
      const offset=((h-1-f)*w+t)*4;
      const level=(Math.log10(Math.max(10**bottom,values[f][t]))-bottom)/(top-bottom);
      pixels.data.set([...color(level),255],offset);
    }
    context.putImageData(pixels,0,0);
  },[data,values,bottom,top]);
  function pick(e){
    const rect=e.currentTarget.getBoundingClientRect();
    const sample=(fraction,n)=>Math.max(0,Math.min(n-1,Math.floor(fraction*n)));
    setTimeIndex(sample((e.clientX-rect.left)/rect.width,data.times.length));
    setFreqIndex(sample(1-(e.clientY-rect.top)/rect.height,data.freqs.length));
  }
  return <section className="chart spectrum-heat">
    <div className="chart-head"><h4>Processed spectrogram</h4><span>Density (µV²/Hz)</span></div>
    <div className="heatmap">
      <div className="heat-y"><span>{data.freqs.at(-1)} Hz</span><span>{data.freqs.at(-1)/2} Hz</span><span>0 Hz</span></div>
      <canvas width={data.times.length} height={data.freqs.length} ref={canvas} onPointerDown={pick} role="img"
        aria-label="Spectrogram of the selected synthetic channel. Sliders provide numeric access to each time-frequency bin."/>
      <div className="heat-x"><span>{data.times[0]} s</span><span>Window centers</span><span>{data.times.at(-1)} s</span></div>
    </div>
    <div className="heat-scale"><span>10^{bottom}</span><i/><span>10^{top} µV²/Hz</span></div>
    <div className="heat-controls">
      <label>Time bin<input type="range" min="0" max={data.times.length-1} value={timeIndex}
        aria-valuetext={time+" seconds"} onChange={e=>setTimeIndex(+e.target.value)}/></label>
      <label>Frequency bin<input type="range" min="0" max={data.freqs.length-1} value={freqIndex}
        aria-valuetext={frequency+" hertz"} onChange={e=>setFreqIndex(+e.target.value)}/></label>
    </div>
    <output className="readout">{time} s · {frequency} Hz · {density.toExponential(4)} µV²/Hz</output>
    <p className="fine">{data.windowSeconds} s Hann windows · 50% overlap · logarithmic color scale. The display uses a fixed frequency crop for each modality.</p>
  </section>;
}
export default function Spectrogram({id,channel}) {
  const [state,setState]=useState(null);
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();
    fetchSynthetic(id+"-spectrogram",controller.signal).then(data=>setState({id,retry,data})).catch(()=>{
      if(!controller.signal.aborted) setState({id,retry,error:true});
    });
    return()=>controller.abort();
  },[id,retry]);
  const current=state?.id===id&&state.retry===retry?state:null;
  if(!current) return <p className="lab-message" role="status">Loading spectrogram…</p>;
  if(current.error) return <div className="lab-message" role="alert">Spectrogram unavailable. <button onClick={()=>setRetry(r=>r+1)}>Retry spectrogram</button></div>;
  return <><Heatmap key={channel} data={current.data} channel={channel}/>
    <a className="text-link data-link" href={new URL("scenarios/"+id+"-spectrogram.json",document.baseURI)} download>Download spectrogram data (JSON)</a></>;
}

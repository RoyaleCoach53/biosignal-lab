import { Component, forwardRef, lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useIsPresent, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from "motion/react";
import { fetchSynthetic } from "./assets";
import { HeadArt, MuscleArt, NeuronArt } from "./story-art";

const HeadModel=lazy(()=>import("./HeadModel"));
let graphicsSupport;
function hasWebGL(){
  if(graphicsSupport!=null) return graphicsSupport;
  try {
    const context=document.createElement("canvas").getContext("webgl2");
    graphicsSupport=!!context;
    context?.getExtension("WEBGL_lose_context")?.loseContext();
  } catch { graphicsSupport=false; }
  return graphicsSupport;
}
class HeadBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(){this.props.onFailure();}
  render(){return this.state.failed?null:this.props.children;}
}
function AcquisitionModel({progress,step,allow3D}){
  const reduced=useReducedMotion();
  const [capable,setCapable]=useState(false);
  const [ready,setReady]=useState(false);
  useEffect(()=>{
    if(allow3D&&!reduced) setCapable(hasWebGL());
  },[allow3D,reduced]);
  const live=allow3D&&!reduced&&capable;
  function failure(){setCapable(false);setReady(false);}
  return <div className={"head-visual"+(live&&ready?" head-live":"")}><HeadArt step={step}/>
    {live&&<div className="head-canvas" aria-hidden="true"><HeadBoundary onFailure={failure}>
      <Suspense fallback={null}><HeadModel progress={progress} onReady={canvas=>{
        canvas.addEventListener("webglcontextlost",failure,{once:true});setReady(true);
      }}/></Suspense>
    </HeadBoundary></div>}
  </div>;
}
const names = ["Neural origins","Scalp acquisition","Filter response","Welch estimation","Surface EMG"];
const hues = ["#87dbc9","#a99df6","#85b3e8","#dda1ba","#a3c780","#ceb581","#82c3e4","#bdb4ea"];
const bands = [["Delta",.5,4],["Theta",4,8],["Alpha",8,13],["Beta",13,30],["Gamma",30,45]];
const paths = name => ({standard:"0.1 Hz HP + 50 Hz notch", high:"1 Hz high-pass",low:"35 Hz low-pass","no-notch":"Notch off"})[name];

function useMedia(query) {
  const [match,setMatch]=useState(()=>matchMedia(query).matches);
  useEffect(()=>{const q=matchMedia(query); const update=()=>setMatch(q.matches);
    q.addEventListener("change",update); update(); return()=>q.removeEventListener("change",update);
  },[query]);
  return match;
}

const tracePath = (values,w,x,y,amp) => values.map((n,i)=>(i?"L":"M")+
  (x+w*i/Math.max(1,values.length)).toFixed(1)+" "+(y-n*amp).toFixed(1)).join("");

function TraceStack({eeg,selected,filter,onSelect}){
  const max = Math.max(...eeg.raw.flat().map(Math.abs),...eeg.processed.flat().map(Math.abs),
    ...Object.values(eeg.filters).flat().map(Math.abs));
  return <svg viewBox="0 0 740 412" role="img" aria-label="Eight synthetic EEG channels, with raw and filtered traces on a common scale.">
    <g className="art-grid">
      {[0,1,2,3,4,5].map(i=><path key={i} d={`M${77+i*126} 16v354`}/>)}
      {eeg.raw.map((_,i)=><path key={i} d={`M77 ${37+i*43}h630`}/>)}
    </g>
    {eeg.raw.map((trace,i)=>{
      const y=37+i*43;
      return <g key={i} onClick={()=>onSelect(i)}>
        {selected===i&&<rect x="3" y={y-21} width="723" height="42" fill="#22324c" opacity=".65"/>}
        <text className="plot-label" x="18" y={y+4} fill={hues[i]}>CH {i+1}</text>
        <path d={tracePath(trace,630,77,y,18/max)} stroke="#93a6c8" strokeDasharray="4 4" opacity=".67" className="story-trace"/>
        <path d={tracePath(i===0?eeg.filters[filter]:eeg.processed[i],630,77,y,18/max)} stroke={hues[i]} className="story-trace"/>
      </g>;
    })}
    <g className="plot-label">{[0,1,2,3,4,5].map(i=><text key={i} x={77+i*126} y="389" textAnchor="middle">{(eeg.start+i/5).toFixed(1)} s</text>)}</g>
  </svg>;
}

function WelchArt({welch,mode,band}){
  const spectral=mode>=2;
  const spectra=mode===2?welch.periodograms:[welch.average];
  let lines, powerTicks;
  if(spectral) {
    const max=4, min=-6;
    const at = val=>298-253*(Math.log10(Math.max(10**min,val))-min)/(max-min);
    powerTicks=[-6,-4,-2,0,2,4].map(t=>[at(10**t),"10^"+t]);
    lines=spectra.map(seq=>seq.map((v,i)=>(i?"L":"M")+(72+620*welch.freqs[i]/60).toFixed(1)+" "+at(v).toFixed(1)).join(""));
  } else {
    const lim=Math.max(...welch.segment.map(Math.abs));
    powerTicks=[-lim,0,lim].map(v=>[171-113*v/lim,Math.round(v)]);
    lines=[tracePath(mode===0?welch.segment:welch.windowed,620,72,171,113/lim)];
  }
  return <svg viewBox="0 0 740 333" role="img" aria-label={spectral?"Computed power density by frequency. Vertical axis is logarithmic.":"Computed sample amplitude over time."}>
    <g className="art-grid">{powerTicks.map(([y])=><path key={y} d={`M72 ${y}h620`}/>)}</g>
    <g className="plot-label">{powerTicks.map(([y,label])=><text key={y} textAnchor="end" x="65" y={y+4}>{label}</text>)}</g>
    {spectral&&band!=null&&<rect x={72+620*bands[band][1]/60} width={620*(bands[band][2]-bands[band][1])/60} y="45" height="253" fill="#9989ed" opacity=".17"/>}
    {lines.map((d,i)=><path key={i} d={d} stroke={spectral&&mode===2?hues[i]:"#aef1df"} opacity={mode===2?".65":"1"} className="story-trace"/>)}
    <g className="plot-label">{(spectral?[0,10,20,30,40,50,60]:[0,1,2,3,4]).map(t=>
      <text key={t} x={72+620*t/(spectral?60:4)} y="321" textAnchor="middle">{t} {spectral?"Hz":"s"}</text>)}</g>
  </svg>;
}

function Scene({index,t,story,retry,error,allow3D=false}) {
  const [pulse,setPulse]=useState(0);
  const [manual,setManual]=useState(null);
  const [channel,setChannel]=useState(0);
  const [filter,setFilter]=useState("standard");
  const [welch,setWelch]=useState(3);
  const [band,setBand]=useState(2);
  let body,controls,readout;
  if(index===0){
    body=<NeuronArt key={pulse} highlight={pulse>0}/>;
    controls=<button onClick={()=>setPulse(p=>p+1)}>Trace the axon</button>;
    readout="Illustration of propagation along an axon. Scalp EEG reflects aggregate activity.";
  } else if(index===1){
    const step=manual??Math.min(3,Math.floor(t*4));
    body=<AcquisitionModel progress={t} step={step} allow3D={allow3D}/>;
    controls=["Electrodes","Amplify","Convert","Sample"].map((label,i)=><button key={label} aria-pressed={step===i} onClick={()=>setManual(i)}>{label}</button>);
    readout=["Electrodes pick up a potential difference at the scalp.","The differential amplifier boosts the signal. Analog filtering reduces frequencies that could alias.","The converter samples the conditioned voltage and represents it as discrete numbers.","Digital samples preserve a time series with a specified sampling rate and amplitude scale."][step];
  } else if(!story) {
    body=<p className="scene-loading" role={error?"alert":"status"}>{error?"The synthetic example could not be loaded.":"Loading the Python-generated example…"}</p>;
    controls=error?<button onClick={retry}>Retry example</button>:null;
    readout="Data source: the fixed BioSignal Lab synthetic catalogue.";
  } else if(index===2){
    body=<TraceStack eeg={story.eeg} selected={channel} filter={filter} onSelect={setChannel}/>;
    controls=<>{["standard","high","low","no-notch"].map((preset)=><button key={preset} aria-pressed={filter===preset} onClick={()=>{setFilter(preset);setChannel(0);}}>{paths(preset)}</button>)}</>;
    readout=`Synthetic, 250 Hz · 4.5–5.5 s excerpt · Ch ${channel+1}. Solid: filtered. Dashed: raw. Common scale ±${Math.ceil(Math.max(...story.eeg.raw.flat().map(Math.abs),...story.eeg.processed.flat().map(Math.abs),...Object.values(story.eeg.filters).flat().map(Math.abs)))} µV per channel. Preset controls change channel 1; the other channels retain the reference filter.`;
  } else if(index===3){
    body=<WelchArt welch={story.welch} mode={welch} band={band}/>;
    controls=<>{["Segment","Apply Hann","Estimate","Average"].map((label,i)=><button key={label} aria-pressed={welch===i} onClick={()=>setWelch(i)}>{label}</button>)}
      {welch>=2&&<label className="band-select">Focus <select value={band??""} onChange={e=>setBand(e.target.value===""?null:+e.target.value)}>
        <option value="">Entire display</option>{bands.map(([name,low,high],i)=><option value={i} key={name}>{name} · {low}–{high} Hz</option>)}</select></label>}</>;
    readout=["One 4 s segment from the processed synthetic EEG, in µV. Adjacent segments overlap by 50%.","The segment mean is removed and a periodic Hann taper is applied. Samples are in µV.","Five one-sided segment periodograms from the full 12 s recording, in µV²/Hz.","Welch mean in µV²/Hz. The display shows 0–60 Hz. Shading identifies the selected project band."][welch];
  } else {
    const emg=story.emg;
    const max=Math.max(...emg.processed.map(Math.abs));
    body=<div className="muscle-scene"><MuscleArt/>
      <svg viewBox="0 0 740 121" role="img" aria-label="Processed synthetic EMG waveform, one second of data.">
        <path d="M44 52h650" stroke="#384c6b"/>
        <path d={tracePath(emg.processed,650,44,52,37/max)} stroke="#a1ecd7" className="story-trace"/>
        <g className="plot-label"><text x="44" y="112">4.5 s</text><text x="694" y="112" textAnchor="end">5.5 s</text></g>
      </svg></div>;
    controls=<div className="story-emg-metrics"><span>RMS <b>{emg.quality.emg_rms_uv.toFixed(2)} µV</b></span><span>Median frequency <b>{emg.quality.emg_median_frequency_hz.toFixed(1)} Hz</b></span></div>;
    readout="Illustration above · computed synthetic EMG below · 1,000 Hz · amplitude in µV.";
  }
  return <div className="scene">
    <div className="scene-name"><span><i/>{names[index]}</span><span>{index<2?"ILLUSTRATION":"SYNTHETIC / PYTHON"}</span></div>
    <div className="scene-image">{body}</div>
    <div className="scene-controls">{controls}</div>
    <p className="scene-caption">{readout}</p>
  </div>;
}

const sceneVariants = {
  enter: direction => ({opacity:0, scale:.978, y:22*direction}),
  current: {opacity:1,scale:1,y:0},
  exit: direction => ({opacity:0,scale:1.018,y:-18*direction}),
};

const SceneTransition = forwardRef(function SceneTransition({direction,reduced,children},ref){
  const present=useIsPresent();
  return <motion.div ref={ref} className="scene-layer" aria-hidden={present?undefined:true}
    inert={present?undefined:true} custom={direction} variants={sceneVariants}
    initial={reduced?false:"enter"} animate="current" exit="exit"
    transition={{duration:reduced?0:.31,ease:[.22,.61,.36,1]}}>
    {children}
  </motion.div>;
});

export default function Journey({copy}) {
  const root=useRef(null);
  const reduced=useReducedMotion();
  const small=useMedia("(max-width: 900px)");
  const pin=!small;
  const {scrollYProgress}=useScroll({target:root,offset:["start center","end center"]});
  const zoom=useTransform(scrollYProgress,[0,.2,.4,.6,.8,1],[.97,1,.975,1,.975,1]);
  const slide=useTransform(scrollYProgress,[0,.2,.4,.6,.8,1],[7,0,-6,0,-6,0]);
  const [{position,direction},setScene]=useState({position:0,direction:1});
  const [story,setStory]=useState(null);
  const [error,setError]=useState(false);
  const [load,setLoad]=useState(false);
  const [attempt,setAttempt]=useState(0);
  useMotionValueEvent(scrollYProgress,"change",value=>{
    const next=Math.max(0,Math.min(4.999,value*5));
    setScene(previous=>Math.floor(previous.position*4)===Math.floor(next*4)?previous:
      {position:next,direction:next>previous.position?1:-1});
    if(next>=1.5) setLoad(true);
  });
  const index=Math.floor(position);
  useLayoutEffect(()=>{
    if(!location.hash.startsWith("#chapter-")) return;
    const target=document.getElementById(location.hash.slice(1));
    if(target&&root.current.contains(target)) target.scrollIntoView({block:"start",behavior:"instant"});
  },[]);
  useEffect(()=>{
    if(pin) return;
    const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setLoad(true);observer.disconnect();}},{rootMargin:"360px"});
    const trigger=root.current.querySelector("#chapter-processing");
    observer.observe(trigger);
    return()=>observer.disconnect();
  },[pin]);
  useEffect(()=>{
    if(!load) return;
    const controller=new AbortController();
    fetchSynthetic("story",controller.signal).then(setStory).catch(()=>{if(!controller.signal.aborted)setError(true);});
    return()=>controller.abort();
  },[load,attempt]);
  const retry=()=>{setError(false);setAttempt(a=>a+1);};
  const sceneProps={story,retry,error};
  const ids=["origin","acquisition","processing","spectrum","emg"];
  return <section className="journey shell" ref={root} aria-label="From neurons to measurable signals">
    <div className="chapter-track">
      {copy.chapters.map(([tag,title,body],i)=><article className="chapter" key={ids[i]} id={"chapter-"+ids[i]} aria-labelledby={"title-"+ids[i]}>
        <div className="chapter-copy"><p className="eyebrow">{tag}</p><h2 id={"title-"+ids[i]}>{title}</h2><p>{body}</p></div>
        {!pin&&<div className="inline-scene" lang="en" dir="ltr"><Scene index={i} t={0} {...sceneProps}/></div>}
      </article>)}
    </div>
    {pin&&<div className="stage-wrap" lang="en" dir="ltr">
      <div className="stage-progress" aria-hidden="true"><span>FIELD NOTES</span><motion.div style={{scaleX:scrollYProgress}}/><span>0{index+2} / 07</span></div>
      <motion.div className="stage" style={reduced?undefined:{scale:zoom,y:slide}}>
        <AnimatePresence mode="popLayout" custom={direction} initial={false}>
          <SceneTransition key={index} direction={direction} reduced={reduced}>
            <Scene index={index} t={position-index} {...sceneProps} allow3D/>
          </SceneTransition>
        </AnimatePresence>
      </motion.div>
      <nav className="chapter-nav" aria-label="Jump to a chapter">{ids.map((id,i)=>
        <a key={id} href={"#chapter-"+id} aria-label={String(i+2).padStart(2,"0")+" · "+names[i]} aria-current={index===i?"location":undefined}>{String(i+2).padStart(2,"0")}</a>)}</nav>
    </div>}
  </section>;
}

import { Component, lazy, Suspense, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import "@fontsource-variable/space-grotesk/wght.css";
import "@fontsource-variable/inter/wght.css";
import { asset } from "./assets";
import { arabic, english } from "./story-content";
import "./style.css";
import "./cinema.css";

const Journey = lazy(()=>import("./Journey"));
const Lab = lazy(()=>import("./Lab.jsx"));
const Atlas = lazy(()=>import("./Atlas.jsx"));
const repo = "https://github.com/RoyaleCoach53/biosignal-lab";
const docs = repo+"/blob/v0.3.0/docs";
const adopted = repo+"/blob/cd9b0a0dadda5cd3ce7c66faa66ea03b6d74f3b6/docs";
const release = repo+"/releases/tag/v0.3.0";

class AtlasBoundary extends Component {
  state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  componentDidCatch(){this.props.onFailure();}
  render(){return this.state.failed?null:this.props.children;}
}

function Hero({copy}) {
  const root=useRef(null);
  const reduced=useReducedMotion();
  const [active,setActive]=useState(false);
  const [ready,setReady]=useState(false);
  const [lost,setLost]=useState(false);
  const {scrollYProgress}=useScroll({target:root,offset:["start start","end start"]});
  const scale=useTransform(scrollYProgress,[0,1],[1,1.13]);
  const y=useTransform(scrollYProgress,[0,1],[0,105]);
  const copyY=useTransform(scrollYProgress,[0,1],[0,56]);
  const enter=(delay)=>reduced?{}:{initial:{opacity:0,y:19},animate:{opacity:1,y:0},transition:{delay,duration:.7,ease:[.22,.61,.36,1]}};
  function toggle(){
    if(active&&!lost){setActive(false);setReady(false);return;}
    let supported=false;
    try {
      const context=document.createElement("canvas").getContext("webgl2");
      supported=!!context;
      context?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch { /* The poster remains available. */ }
    setLost(!supported);setReady(false);setActive(supported);
  }
  return <section className="cinema-hero" ref={root} aria-labelledby="headline">
    <div className="hero-coordinate shell" aria-hidden="true"><span>01 / NEURAL ACTIVITY</span><span>EEG + EMG</span></div>
    <div className="hero-inner shell">
      <motion.div className="opening-copy" style={reduced?undefined:{y:copyY}}>
        <motion.p className="eyebrow intro-kicker" {...enter(.02)}><i/>{copy.teaser}</motion.p>
        <h1 id="headline">{copy.headline.map((line,i)=><motion.span key={line} {...enter(.08+i*.085)}>{line}</motion.span>)}</h1>
        <motion.p className="opening-description" {...enter(.27)}>{copy.intro}</motion.p>
        <motion.div className="opening-actions" {...enter(.36)}><a className="button primary" href="#journey">{copy.enter}</a><a className="button ghost" href="#lab">{copy.lab}</a></motion.div>
      </motion.div>
      <figure className="opening-art" lang="en" dir="ltr">
        <div className="atlas-reticle" aria-hidden="true"><i/><i/><i/><i/><span className="reticle-cross"/><span className="reticle-plane"/></div>
        <motion.div className="opening-mesh" style={reduced?undefined:{scale,y}}>
          <img className="opening-poster" src={asset("neural-atlas.svg")} width="520" height="450"
               alt="Procedural brain illustration" fetchPriority="high" style={{opacity:active&&!lost&&ready?0:1}}/>
          {active&&!lost&&<div className="atlas-canvas"><AtlasBoundary onFailure={()=>setLost(true)}>
            <Suspense fallback={<p className="atlas-note" role="status">Loading 3D…</p>}>
              <Atlas progress={scrollYProgress} reduced={reduced} onReady={()=>setReady(true)}
                onFailure={e=>{e.preventDefault();setLost(true);}}/>
            </Suspense>
          </AtlasBoundary></div>}
        </motion.div>
        <figcaption className="opening-legend">
          <span><i/>Cortical form <small>Procedural illustration</small></span>
          <button className="atlas-toggle" type="button" aria-pressed={active&&!lost} onClick={toggle}>{active&&!lost?"Close 3D":"Explore in 3D"}</button>
        </figcaption>
        {lost&&<p className="atlas-failure" role="status">Static atlas · WebGL unavailable</p>}
      </figure>
    </div>
    <div className="hero-index shell"><a href="#journey"><span aria-hidden="true">↓</span>{copy.scroll}</a><span>FIELD ATLAS / BIOSIGNAL LAB</span></div>
  </section>;
}

function Deferred({id,margin,children,fallback,force=false}) {
  const element=useRef(null);
  const [show,setShow]=useState(false);
  useEffect(()=>{
    if(show||force) return;
    if(!("IntersectionObserver" in window)){setShow(true);return;}
    const observer=new IntersectionObserver(([entry])=>{if(entry.isIntersecting){setShow(true);observer.disconnect();}},{rootMargin:margin});
    observer.observe(element.current);
    return()=>observer.disconnect();
  },[show,force,margin]);
  return <div ref={element} className={id+"-mount"}>
    {(show||force)?<Suspense fallback={fallback}>{children}</Suspense>:fallback}
  </div>;
}

function App(){
  const [rtl,setRtl]=useState(false);
  const [menu,setMenu]=useState(false);
  const [anchor,setAnchor]=useState(location.hash);
  const toggle=useRef(null);
  const copy=rtl?arabic:english;
  useEffect(()=>{
    document.documentElement.lang=rtl?"ar":"en";
    document.documentElement.dir=rtl?"rtl":"ltr";
  },[rtl]);
  useEffect(()=>{
    const observe=()=>setAnchor(location.hash);
    window.addEventListener("hashchange",observe);
    return()=>window.removeEventListener("hashchange",observe);
  },[]);
  return <>
    <a className="skip" href="#content">{rtl?"انتقل إلى المحتوى":"Skip to content"}</a>
    <header className="masthead"><div className="nav shell">
      <a className="brand" href="#" aria-label="BioSignal Lab home"><img src={asset("mark.svg")} alt="" width="34" height="34"/><b>BioSignal<span> Lab</span></b></a>
      <button type="button" ref={toggle} className="menu-toggle" aria-expanded={menu} aria-controls="main-links" onClick={()=>setMenu(x=>!x)}>{rtl?"القائمة":"Menu"}</button>
      <nav id="main-links" className={menu?"open":""} aria-label={rtl?"التنقل الرئيسي":"Main navigation"} onKeyDown={e=>{if(e.key==="Escape"){setMenu(false);toggle.current?.focus();}}}>
        {["journey","lab","methods"].map((id,i)=><a key={id} href={"#"+id} onClick={()=>setMenu(false)}>{copy.nav[i]}</a>)}
      </nav>
      <div className="nav-end"><a className="nav-source" href={repo}>GitHub</a><button type="button" className="language"
        aria-label={rtl?"EN · Switch to English":"عربي · عرض بالعربية"} onClick={()=>setRtl(x=>!x)}>{rtl?"EN":"عربي"}</button></div>
    </div></header>
    <main id="content" tabIndex={-1}>
      <Hero copy={copy}/>
      <div className="journey-anchor" id="journey">
        <Deferred id="journey" margin="500px" force={anchor==="#journey"||anchor.startsWith("#chapter-")} fallback={<div className="journey-placeholder shell" aria-hidden="true"/>}>
          <Journey copy={copy}/>
        </Deferred>
      </div>
      <section className="lab-section section" id="lab" aria-labelledby="lab-head">
        <div className="shell"><header className="section-title"><p className="eyebrow"><i/>{rtl?"٠٧ / المختبر":"07 / THE LABORATORY"}</p>
          <h2 id="lab-head">{rtl?"مختبر الإشارات.":"Enter the laboratory."}</h2><p>{copy.labIntro}</p></header>
          <div lang="en" dir="ltr"><Deferred id="lab" margin="300px" force={anchor==="#lab"} fallback={<p className="lab-message" role="status">Loading workbench…</p>}><Lab/></Deferred></div></div>
      </section>
      <section className="shell technical section" id="methods" aria-labelledby="methods-head">
        <div><p className="eyebrow"><i/>{rtl?"المنهجية والأدلة":"METHODS & EVIDENCE"}</p>
          <h2 id="methods-head">{copy.methods}</h2><p>{copy.limits}</p></div>
        <div className="method-references">
          {[docs+"/METHODS.md",docs+"/real_world/REPORT.md",docs+"/LIMITATIONS.md"].map((url,i)=><a key={url} href={url}>{copy.notes[i]}</a>)}
          <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4907333/">Neural sources · Buzsáki et al.</a>
          <a href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html">Welch method · SciPy</a>
          <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC4254845/">Surface EMG · Farina et al.</a>
        </div>
      </section>
    </main>
    <footer className="project-footer"><div className="shell">
      <a className="brand" href="#"><img src={asset("mark.svg")} alt="" width="30" height="30"/><b>BioSignal<span> Lab</span></b></a>
      <div><a href={release}>{copy.release}</a><a href={adopted+"/QUICK_START.md"}>{copy.quick}</a>
        <a href={repo+"/blob/v0.3.0/CONTRIBUTING.md"}>{copy.contributing}</a><a href={repo}>{copy.source}</a></div>
    </div></footer>
  </>;
}
createRoot(document.getElementById("root")).render(<App/>);

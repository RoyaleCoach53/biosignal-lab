import { Component, lazy, Suspense, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { LazyMotion, domAnimation, m, useReducedMotion, useScroll, useTransform } from "motion/react";
import "@fontsource-variable/space-grotesk/wght.css";
import "@fontsource-variable/inter/wght.css";
import "./style.css";

const Lab = lazy(()=>import("./Lab.jsx"));
const Atlas = lazy(()=>import("./Atlas.jsx"));
const repo = "https://github.com/RoyaleCoach53/biosignal-lab";
const docs = repo+"/tree/v0.3.0/docs";
const adopted = repo+"/blob/cd9b0a0dadda5cd3ce7c66faa66ea03b6d74f3b6/docs";
const asset = new URL(import.meta.env.BASE_URL,document.baseURI);
const external = {
  release:repo+"/releases/tag/v0.3.0", quick:adopted+"/QUICK_START.md",
  methods:docs+"/METHODS.md", limits:docs+"/LIMITATIONS.md", validation:docs+"/real_world/REPORT.md",
  beta:adopted+"/beta/PROGRAM.md", issues:repo+"/issues", contribute:repo+"/blob/v0.3.0/CONTRIBUTING.md",
  science:adopted+"/EEG_TUTORIAL.md",
};
const en = {
  nav:["Signal lab","Methods","Resources"], status:"v0.3.0 · RESEARCH ALPHA",
  kicker:"OPEN-SOURCE BIOSIGNAL ANALYSIS", shape:["The shape","of a signal."],
  hero:"An open research toolkit for seeing, processing and explaining EEG and EMG. Start with synthetic data and follow every step from waveform to spectrum.",
  primary:"Enter the signal lab", secondary:"View GitHub",
  modes:["EEG / BRAIN ACTIVITY","EMG / MUSCLE ACTIVITY","MIT / OPEN SOURCE"],
  visual:["NEURAL ATLAS","Procedural illustration","Interactive 3D","Close 3D","Static atlas"],
  overview:["THE SIGNAL PATH","From samples to evidence.","Follow a trace through preprocessing and spectral estimation. Each step exposes the input, measurement units and assumptions that affect the result."],
  flow:[["Waveform","Compare raw and filtered amplitude in µV. A filter changes what you measure."],["Spectrum","Use Welch power spectral density to see where energy sits across frequencies."],["Review","Compare band powers and amplitude metrics. Inspect candidate windows in the raw signal."]],
  demo:["INTERACTIVE WORKBENCH","Run a signal experiment.","Choose a synthetic condition and change one parameter at a time. The charts display outputs from the same Python engine used by BioSignal Lab."],
  methods:["REPRODUCIBLE SCIENCE","The method is part of the result.","Sampling, filter edges and window length can change how a signal looks. Published methods and benchmark settings make those effects inspectable."],
  protocol:["Read the method","PhysioNet comparison","Scientific limitations"],
  caution:["Research alpha","The published pilot compares numerical results with MNE-Python under matched settings. The sample is small, and filtering can differ under native padding defaults. Quality flags are heuristic review cues. For research and education only."],
  resources:["OPEN RESEARCH","Take the lab further.","Install the released toolkit, reproduce an EEG analysis, or help test the learning workflow."],
  links:[["Download v0.3.0","Research Alpha release with Python distributions and verification files."],["Student quick start","Run a first synthetic analysis with the dashboard."],["PhysioNet EEG tutorial","Trace a public recording from EDF import to an MNE comparison."],["Contribute on GitHub","Find contribution guidelines, report bugs and propose changes."]],
  beta:["INDEPENDENT BETA","Help us test the workflow.","The proposed five-person pilot asks students and researchers to try the tutorial and record friction, numerical results and questions. Participation is voluntary.","Read the beta protocol"],
  foot:"Open science, from sample to spectrum.",
};
const ar = {
  nav:["مختبر الإشارة","المنهجية","المصادر"], status:"الإصدار البحثي الأولي · v0.3.0",
  kicker:"تحليل الإشارات الحيوية مفتوح المصدر", shape:["شكل","الإشارة."],
  hero:"أداة بحثية مفتوحة لفهم إشارات الدماغ والعضلات ومعالجتها. ابدأ ببيانات اصطناعية وتتبّع الإشارة من الموجة إلى الطيف.",
  primary:"ادخل مختبر الإشارة",secondary:"عرض المستودع",
  modes:["EEG / نشاط الدماغ","EMG / نشاط العضلات","MIT / مفتوح المصدر"],
  visual:["أطلس عصبي","رسم توضيحي برمجي","عرض ثلاثي الأبعاد","إغلاق العرض","أطلس ثابت"],
  overview:["مسار الإشارة","من العينات إلى النتائج.","تتبّع الإشارة عبر المعالجة وحساب الطيف. تعرض كل خطوة الوحدات والافتراضات المؤثرة على النتائج."],
  flow:[["الموجة","قارن السعة الخام والمُرشَّحة بالميكروفولت."],["الطيف","استخدم كثافة القدرة الطيفية لتحديد توزيع الطاقة عبر الترددات."],["المراجعة","قارن قدرة النطاقات ومقاييس السعة وافحص المقاطع المرشحة للمراجعة."]],
  demo:["المختبر التفاعلي","جرّب تحليل الإشارة.","اختر حالة اصطناعية وغيّر معلمة واحدة كل مرة. تعرض الرسوم نتائج حسابها محرك بايثون. عناصر التحكم أدناه باللغة الإنجليزية."],
  methods:["علم قابل لإعادة الإنتاج","المنهجية جزء من النتيجة.","معدل أخذ العينات وإعدادات المرشحات وطول النافذة قد تغيّر النتائج. توضح الوثائق إعدادات المقارنة وحدودها."],
  protocol:["قراءة المنهجية","مقارنة PhysioNet","الحدود العلمية"],
  caution:["إصدار بحثي أولي","تقارن الدراسة التجريبية النتائج العددية مع MNE-Python عند تطابق الإعدادات. حجم العينة صغير وقد تختلف النتائج مع إعدادات الحواف. مؤشرات الجودة للمراجعة. للاستخدام البحثي والتعليمي فقط."],
  resources:["بحث مفتوح","واصل العمل مع المختبر.","ثبّت أداة بايثون أو أعد تجربة تحليل الإشارة أو ساعد في اختبار المادة التعليمية."],
  links:[["تنزيل v0.3.0","الإصدار البحثي وملفات التحقق."],["دليل البدء للطلاب","جرّب تحليلاً لإشارة اصطناعية."],["درس EEG على PhysioNet","تتبّع التسجيل من الاستيراد إلى المقارنة."],["ساهم على GitHub","اقرأ إرشادات المساهمة وأبلغ عن المشكلات."]],
  beta:["اختبار مستقل","ساعد في اختبار خطوات العمل.","برنامج مقترح لخمسة طلاب وباحثين لتجربة الدرس وتسجيل المشكلات والنتائج. المشاركة تطوعية.","قراءة بروتوكول الاختبار"],
  foot:"علم مفتوح، من العينة إلى الطيف.",
};

function Symbol({name}) {
  const paths = {wave:"M1 13h4l3-8 4 15 4-11 3 4h4", bars:"M3 20v-5m5 5V9m5 11V3m5 17V8m4 12v-6", review:"M2 5h20v14H2z M6 12l3 3 7-7", git:"M6 4v10a4 4 0 0 0 4 4h5m-9-7h6a4 4 0 0 0 4-4V6 M3 4a3 3 0 1 0 6 0 3 3 0 1 0 -6 0M13 4a3 3 0 1 0 6 0 3 3 0 1 0 -6 0M15 18a3 3 0 1 0 6 0 3 3 0 1 0 -6 0"};
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}

class AtlasBoundary extends Component {
  state = { failed:false };
  static getDerivedStateFromError(){ return {failed:true}; }
  componentDidCatch(){ this.props.onFailure(); }
  render(){return this.state.failed?<p className="atlas-note" role="status">3D is unavailable. The static atlas is still visible.</p>:this.props.children;}
}

function Hero({c}) {
  const [active,setActive] = useState(false);
  const [lost,setLost] = useState(false);
  const [ready,setReady] = useState(false);
  const root=useRef(null);
  const reduced=useReducedMotion();
  const {scrollYProgress}=useScroll({target:root,offset:["start start","end start"]});
  const scale=useTransform(scrollYProgress,[0,1],[1,.91]);
  const y=useTransform(scrollYProgress,[0,1],[0,34]);
  const entrance = (delay) => reduced ? {} : {initial:{opacity:0,y:14},animate:{opacity:1,y:0},transition:{delay,duration:.6,ease:[.2,.65,.23,1]}};
  return <section className="hero shell" ref={root} aria-labelledby="headline">
    <div className="hero-copy">
      <m.p {...entrance(.04)} className="eyebrow"><i/>{c.kicker}</m.p>
      <m.h1 {...entrance(.10)} id="headline">{c.shape[0]}<br/><span>{c.shape[1]}</span></m.h1>
      <m.p {...entrance(.18)} className="hero-intro">{c.hero}</m.p>
      <m.div {...entrance(.24)} className="hero-actions"><a className="button primary" href="#lab">{c.primary}</a><a className="button secondary" href={repo}><Symbol name="git"/>{c.secondary}</a></m.div>
    </div>
    <m.figure className="hero-visual" style={reduced?undefined:{y,scale}}>
      <div className="plot-corner top-left"/><div className="plot-corner top-right"/><div className="plot-corner bottom-left"/><div className="plot-corner bottom-right"/>
      <div className="atlas-top" dir="ltr"><i/><span>{c.visual[0]}</span><span className="axis">x / y / z</span></div>
      <div className="atlas-stage">
        <div className="atlas-reference" aria-hidden="true"><div className="orb one"/><div className="orb two"/><div className="orb three"/><div className="cross horizontal"/><div className="cross vertical"/><div className="scan"/></div>
        <img className="atlas-poster" src={new URL("neural-atlas.svg",asset)} width="520" height="450" alt={c.visual[1]} fetchPriority="high" style={{display:active&&!lost&&ready?"none":undefined}}/>
        {active&&!lost&&<div className="atlas-canvas"><AtlasBoundary onFailure={()=>setLost(true)}><Suspense fallback={<p className="atlas-note" role="status">Loading interactive atlas…</p>}>
          <Atlas onReady={()=>setReady(true)} onFailure={e=>{e.preventDefault();setLost(true);}}/>
        </Suspense></AtlasBoundary></div>}
        <span className="atlas-label left" aria-hidden="true">L</span><span className="atlas-label right" aria-hidden="true">R</span>
      </div>
      <figcaption className="atlas-caption">
        <span>{c.visual[1]}</span>
        <button type="button" aria-pressed={active&&!lost} onClick={()=>{
          if(active&&!lost){setActive(false);setReady(false);return;}
          let supported=false;
          try {
            const context=document.createElement("canvas").getContext("webgl2");
            supported=!!context;
            context?.getExtension("WEBGL_lose_context")?.loseContext();
          } catch { /* Static illustration remains available. */ }
          setLost(!supported);setActive(supported);
        }}>{active&&!lost?c.visual[3]:c.visual[2]}</button>
      </figcaption>
      {lost&&<p className="atlas-failure" role="status">{c.visual[4]} · WebGL unavailable</p>}
    </m.figure>
  </section>;
}
function SignalPath() {
  const reduced=useReducedMotion();
  const path="M0 27H126l9-8 9 17 11-29 12 38 11-25 8 7H475l13-13 11 13h13l11-17 11 17h13l12-8 9 8H920";
  return <div className="flow-trace" aria-hidden="true">
    <svg viewBox="0 0 920 50" preserveAspectRatio="none">
      <path d={path} className="trace-base"/>
      <m.path d={path} className="trace-lit" initial={reduced?false:{pathLength:0}}
        whileInView={{pathLength:1}} viewport={{once:true,amount:.85}}
        transition={{duration:reduced?0:1.15,ease:"easeOut"}} />
      {[15,460,905].map(x=><circle key={x} cx={x} cy="27" r="3" />)}
    </svg>
  </div>;
}
function SectionTitle({data,id}) {
  return <header className="section-title"><p className="eyebrow"><i/>{data[0]}</p><h2 id={id}>{data[1]}</h2><p>{data[2]}</p></header>;
}
function App(){
  const [arabic,setArabic]=useState(false);
  const [showNav,setShowNav]=useState(false);
  const [showLab,setShowLab]=useState(location.hash==="#lab");
  const lab=useRef(null);
  const c=arabic?ar:en;
  useEffect(()=>{
    document.documentElement.lang=arabic?"ar":"en";
    document.documentElement.dir=arabic?"rtl":"ltr";
  },[arabic]);
  useEffect(()=>{
    if (showLab) return;
    if (!("IntersectionObserver" in window)) { setShowLab(true); return; }
    const observer=new IntersectionObserver(([entry])=>{if(entry.isIntersecting){setShowLab(true);observer.disconnect();}},{rootMargin:"320px"});
    observer.observe(lab.current);
    return ()=>observer.disconnect();
  },[showLab]);
  return <LazyMotion features={domAnimation}>
    <a className="skip" href="#content">Skip to content</a>
    <header className="masthead"><div className="nav shell">
      <a className="brand" href="#" aria-label="BioSignal Lab home"><img src={new URL("mark.svg",asset)} alt="" width="34" height="34"/><b>BioSignal<span> Lab</span></b></a>
      <button type="button" className="menu-toggle" aria-expanded={showNav} aria-controls="main-links" onClick={()=>setShowNav(v=>!v)}>{arabic?"القائمة":"Menu"}</button>
      <nav id="main-links" className={showNav?"open":""} aria-label={arabic?"التنقّل الرئيسي":"Main navigation"} onKeyDown={e=>{if(e.key==="Escape"){setShowNav(false);document.querySelector(".menu-toggle")?.focus();}}}>
        {["lab","methods","resources"].map((id,i)=><a key={id} href={"#"+id} onClick={()=>setShowNav(false)}>{c.nav[i]}</a>)}
      </nav>
      <div className="nav-end"><a className="release-status" href={external.release}><i/>{c.status}</a><button className="language" type="button" aria-label={arabic?"EN · Switch to English":"عربي · عرض بالعربية"} onClick={()=>setArabic(a=>!a)}>{arabic?"EN":"عربي"}</button></div>
    </div></header>
    <main id="content" tabIndex={-1}>
      <Hero c={c}/>
      <div className="ribbon"><div className="shell">{c.modes.map((s,i)=><span key={s}><i className={"badge-dot dot-"+i}/>{s}</span>)}</div></div>
      <section className="shell section path-section" aria-labelledby="flow-head">
        <SectionTitle data={c.overview} id="flow-head"/>
        <SignalPath/><div className="flow">{c.flow.map(([title,desc],i)=><article key={title}>
          <span className="flow-symbol"><Symbol name={["wave","bars","review"][i]}/></span><h3>{title}</h3><p>{desc}</p>
        </article>)}</div>
      </section>
      <section className="lab-section section" id="lab" ref={lab} aria-labelledby="lab-head"><div className="shell">
        <SectionTitle data={c.demo} id="lab-head"/>
        <div className="lab-mount" lang="en" dir="ltr">{showLab&&<Suspense fallback={<p className="lab-message" role="status">Loading workbench…</p>}><Lab/></Suspense>}</div>
      </div></section>
      <section className="shell section methods" id="methods" aria-labelledby="methods-head">
        <div><SectionTitle data={c.methods} id="methods-head"/>
          <div className="method-links">{[external.methods,external.validation,external.limits].map((url,i)=><a className="text-link" href={url} key={url}>{c.protocol[i]}</a>)}</div>
        </div>
        <aside className="method-aside"><Symbol name="review"/><h3>{c.caution[0]}</h3><p>{c.caution[1]}</p></aside>
      </section>
      <section className="resources section" id="resources" aria-labelledby="resources-head"><div className="shell">
        <SectionTitle data={c.resources} id="resources-head"/>
        <div className="resource-grid">{c.links.map(([title,body],i)=><article key={title}>
          <span className="resource-type">{["RELEASE","LEARNING","REPRODUCE","DEVELOP"][i]}</span><h3><a href={[external.release,external.quick,external.science,external.contribute][i]}>{title}</a></h3><p>{body}</p></article>)}</div>
        <div className="beta"><div><p className="eyebrow"><i/>{c.beta[0]}</p><h3>{c.beta[1]}</h3><p>{c.beta[2]}</p></div><a className="button secondary" href={external.beta}>{c.beta[3]}</a></div>
      </div></section>
    </main>
    <footer className="shell"><a className="brand" href="#"><img src={new URL("mark.svg",asset)} alt="" width="30" height="30"/><b>BioSignal<span> Lab</span></b></a><p>{c.foot}</p><a className="text-link" href={repo}>GitHub · MIT</a><span className="preview-label">Design preview</span></footer>
  </LazyMotion>;
}
createRoot(document.getElementById("root")).render(<App/>);

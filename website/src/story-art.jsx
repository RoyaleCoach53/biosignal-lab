import { useId } from "react";

const dendrites = [
  "M334 230Q299 178 265 167T181 113Q140 89 96 100 M265 167Q236 110 256 67Q269 38 256 20 M207 130Q179 135 151 162Q120 171 76 162 M163 106Q120 76 129 47",
  "M347 225Q333 181 357 133T354 63Q335 31 310 23 M357 133Q396 110 412 67L456 36 M354 63Q371 43 366 18 M386 104Q427 114 465 91L502 89",
  "M359 233Q397 186 443 202T541 168Q567 139 608 141 M480 207Q522 216 558 207L612 222 M518 192Q508 162 519 134L549 110 M558 155Q560 120 591 101",
  "M337 252Q274 243 229 268T121 301Q85 294 55 277 M229 268Q197 227 154 224L98 231 M174 289Q154 316 131 330L91 341 M105 299Q97 329 68 351",
  "M349 268Q337 300 357 331T352 409Q337 433 313 451 M355 324Q382 310 401 326L429 343 M361 375Q380 404 426 421L472 446",
  "M319 246Q300 227 268 230L240 208 M362 252Q381 264 412 255Q433 239 458 245",
];
const axon = "M362 260C411 283 422 313 459 301S518 281 541 316S578 359 624 329S663 277 699 296";
const branches = [
  ["M135 415Q181 389 209 403T278 385Q308 358 351 380M209 403L180 434M256 399L271 439", "#9586e6"],
  ["M28 114Q49 128 51 154T85 191M51 154L28 182M69 168Q95 150 113 152", "#769ec6"],
  ["M520 77Q556 51 583 70T646 55M583 70L609 110M630 66L659 98", "#769ec6"],
];
export function NeuronArt({highlight}) {
  const uid=useId().replaceAll(":","");
  return <svg className="scientific-art" viewBox="0 0 740 480" role="img" aria-label="Illustration of a branching neuron with a cell body, dendrites, an axon and a synaptic gap.">
    <defs><radialGradient id={uid+"s"}><stop stopColor="#d8d0ff"/><stop offset=".32" stopColor="#8a72de"/><stop offset=".74" stopColor="#483c89"/><stop offset="1" stopColor="#211940"/></radialGradient>
      <filter id={uid+"glow"}><feGaussianBlur stdDeviation="4"/></filter></defs>
    <g fill="none" strokeWidth="1.2" opacity=".48">{branches.map(([d,stroke])=><path key={d} d={d} stroke={stroke}/>)}</g>
    <g fill="none" strokeLinecap="round" strokeLinejoin="round">
      {dendrites.map((d,i)=><path key={d} d={d} stroke={i%2?"#aa9bf0":"#7594d5"} strokeWidth={i<4?2.2:1.3} opacity=".84"/>)}
      <path d={axon} stroke="#8e69eb" strokeWidth="9" opacity=".43" filter={`url(#${uid}glow)`}/>
      <path d={axon} stroke="#c2acff" strokeWidth="2.7"/>
      <path d="M690 296q-12-18-1-32m0 32q-9 11-5 24 M722 310q-15-9-13-24m13 24q-13 12-8 29" stroke="#d1d4ff" strokeWidth="1.5"/>
      {highlight&&<path d={axon} pathLength="100" className="axon-flash" stroke="#b7ffec" strokeWidth="4" strokeDasharray="8 92"/>}
    </g>
    <path d="M320 224Q329 205 345 216Q359 217 367 231Q378 244 370 258Q361 279 344 274Q327 274 316 260Q307 240 320 224Z" fill={`url(#${uid}s)`} stroke="#c6baff" strokeWidth="1.5"/>
    <circle cx="345" cy="243" r="11" fill="none" stroke="#e0d8ff" opacity=".62"/>
    <g className="diagram-annotations"><path d="M173 112v56H134 M344 276v48h-23 M579 345v46h-41"/>
      <text x="67" y="175">DENDRITES</text><text x="254" y="330">CELL BODY</text><text x="485" y="397">AXON</text>
      <text x="642" y="245">SYNAPSE</text></g>
    <circle cx="700" cy="296" r="3.5" fill="#a3f4e6"/>
  </svg>;
}

const headProfile = "M300 403C297 373 290 345 267 328C220 303 199 262 207 216C208 169 232 103 280 77C349 40 428 67 455 111C475 143 468 164 480 192L504 227Q508 234 498 238L475 243Q473 260 479 267L470 275Q478 284 470 290Q475 309 452 317L404 319Q389 366 405 403Z";
const spots = [[270,123],[331,84],[396,100],[441,135],[253,170]];
const chain = ["Electrodes","Amplifier","ADC","Samples"];
export function HeadArt({step}) {
  const uid=useId().replaceAll(":","");
  return <svg className="scientific-art" viewBox="0 0 740 480" role="img" aria-label="Conceptual scalp EEG acquisition. Electrodes sense a potential difference, the amplifier conditions it, and a converter samples it.">
    <defs>
      <radialGradient id={uid+"head"} cx=".63" cy=".28" r=".72"><stop stopColor="#465479"/><stop offset=".5" stopColor="#233350"/><stop offset="1" stopColor="#101527"/></radialGradient>
      <clipPath id={uid+"profile"}><path d={headProfile}/></clipPath>
    </defs>
    <g className="head-profile" transform="translate(-45 -18) scale(1.07)">
      <path d={headProfile} fill={`url(#${uid}head)`} stroke="#7489bb" strokeWidth="1.65"/>
      <g clipPath={`url(#${uid}profile)`}>
        {Array.from({length:9},(_,i)=><ellipse key={i} cx="351" cy={125+i*26} rx={128-(i>5?(i-5)*16:0)} ry="40" transform={`rotate(-13 351 ${125+i*26})`} fill="none" stroke="#94b4e7" opacity=".15"/>)}
        {[-64,-40,-17,12,41,70].map(i=><ellipse key={i} cx={340+i} cy="201" rx={28+Math.abs(i)/2} ry="154" transform={`rotate(${i/4} ${340+i} 201)`} fill="none" stroke="#a6b4e7" opacity=".19"/>)}
        <path d="M226 187Q263 126 311 151T395 149Q437 150 454 198Q423 234 380 227T291 231Q242 234 226 187Z" fill="#8674e2" fillOpacity=".12" stroke="#8b85df" strokeDasharray="3 5"/>
        <path d="M269 189q18-19 35 0t40 0m-41-20q20 15 27-3m30 28q34 7 36-10m-109 34q22 7 41-12" fill="none" stroke="#b0a2ff" strokeWidth="2" opacity=".72"/>
      </g>
      <path d="M352 200q-21-10-24 17q-2 29 17 30q8-15 13-24m91-27q-14-5-23 5m-6 110q-7 12-16 8" fill="none" stroke="#8795b6" opacity=".65"/>
      <path d="M396 100Q430 49 502 94T575 153V358" fill="none" stroke="#79e8d8" strokeOpacity=".51" strokeWidth="1.5"/>
      {spots.map(([x,y],i)=><g key={x} transform={`translate(${x} ${y})`}><circle r="13" fill="#83edda" opacity={i===2?".23":".1"}/><circle r="5.5" fill={i===2?"#a1ffe8":"#8da7cf"} stroke="#c5e8ff"/><circle r="2" fill="#091722"/></g>)}
    </g>
    <g transform="translate(58 423)">{chain.map((name,i)=><g transform={`translate(${i*164} 0)`} key={name}>
      {i<3&&<path d="M132 17h32" stroke="#56719a" strokeDasharray="3 3"/>}
      <rect width="132" height="35" rx="3" fill={step===i?"#26394c":"#111b2c"} stroke={step===i?"#85ead4":"#455878"}/>
      <text x="66" y="22" textAnchor="middle" fill={step===i?"#baffeb":"#b4c2db"} className="diagram-chip">{name}</text>
    </g>)}</g>
  </svg>;
}

export function MuscleArt(){
  const uid=useId().replaceAll(":","");
  return <svg className="scientific-art" viewBox="0 0 740 320" role="img" aria-label="Conceptual forearm muscle fibers and a pair of surface EMG electrodes.">
    <defs><linearGradient id={uid+"fibers"} x2=".85" y2=".48"><stop stopColor="#252b4d"/><stop offset=".45" stopColor="#705a96"/><stop offset="1" stopColor="#302646"/></linearGradient></defs>
    <path d="M39 87C161 103 217 73 323 98S522 130 676 114L704 175C558 177 467 256 332 251S143 187 42 188Z" fill="#202640" stroke="#526481" strokeWidth="2"/>
    <path d="M70 142C217 100 270 100 342 114S515 178 665 144C516 224 442 235 344 226S205 190 70 142Z" fill={`url(#${uid}fibers)`} stroke="#a691df" strokeWidth="1.3"/>
    {Array.from({length:13},(_,i)=><path key={i} d={`M72 142C167 ${116+i*5} 235 ${100+i*8} 341 ${116+i*8}S519 ${186+i*2} 645 150`} fill="none" stroke={i%3===0?"#d6aaff":"#a18cdc"} opacity={i%3===0?".72":".43"} strokeWidth="1.5"/>)}
    <path d="M313 151Q299 67 430 46h102M435 179Q430 79 528 59" fill="none" stroke="#82e8d8" strokeWidth="2"/>
    {[ [313,151],[435,179] ].map(([x,y])=><g key={x}><circle cx={x} cy={y} r="16" fill="#a2ffe2" opacity=".18"/><circle cx={x} cy={y} r="8" fill="#8bf1d8" stroke="#d4ffec"/><circle cx={x} cy={y} r="3" fill="#253249"/></g>)}
    <text x="538" y="51" className="diagram-label">SURFACE PAIR</text>
  </svg>;
}

import { Canvas, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BufferGeometry, DoubleSide, Float32BufferAttribute, Vector3 } from "three";

// Artistic contours. Measurements and electrode placement are illustrative.
const rings=[
  [-1.40,.42,.44,.05],[-1.12,.37,.43,.04],[-.84,.46,.56,.08],
  [-.64,.43,.65,.10],[-.49,.50,.67,.13],[-.35,.62,.66,.14],
  [-.12,.70,.64,.16],[.10,.72,.66,.17],[.35,.68,.73,.16],
  [.59,.65,.73,.13],[.81,.55,.65,.10],[.99,.39,.46,.06],
  [1.12,.12,.19,.02],[1.15,.01,.02,0],
];
const electrodes=[[.49,-.59],[.78,-.9],[1.01,-.51],[1.04,.45],[.71,.97],[.43,.58]];
const exp=Math.exp;
function position(y, angle){
  const index=rings.findIndex(row=>row[0]>=y);
  const upper=index<0?rings.length-1:index;
  const a=rings[Math.max(0,upper-1)],b=rings[Math.max(0,upper)];
  const t=a===b?0:Math.max(0,Math.min(1,(y-a[0])/(b[0]-a[0])));
  const radius=a[1]+(b[1]-a[1])*t, depth=a[2]+(b[2]-a[2])*t, rear=a[3]+(b[3]-a[3])*t;
  const front=Math.cos(angle);
  const nose=front>0?.25*exp(-(((y+.065)/.22)**2))*exp(-((angle/.21)**2)):0;
  const brow=front>0?.07*exp(-(((y-.22)/.085)**2))*exp(-((angle/.52)**2)):0;
  return [radius*Math.sin(angle),y,front*(depth+(front<0?rear:0))+nose+brow];
}

function Form({progress}){
  const {invalidate}=useThree();
  const pivot=useRef(null);
  const model=useMemo(()=>{
    const sectors=56,levels=56;
    const nodes=[],index=[],stripes=[];
    const face=(r,c)=>r*(sectors+1)+c;
    const point=(r,c)=>position(-1.4+2.55*r/levels,-Math.PI+2*Math.PI*c/sectors);
    for(let r=0;r<=levels;r++)for(let c=0;c<=sectors;c++){
      nodes.push(...point(r,c));
      if(r<levels&&c<sectors){
        index.push(face(r,c),face(r,c+1),face(r+1,c),face(r,c+1),face(r+1,c+1),face(r+1,c));
        if(r%4===0)stripes.push(...point(r,c),...point(r,c+1));
        if(c%7===0)stripes.push(...point(r,c),...point(r+1,c));
      }
    }
    const mesh=new BufferGeometry().setAttribute("position",new Float32BufferAttribute(nodes,3));
    mesh.setIndex(index);mesh.computeVertexNormals();
    const lattice=new BufferGeometry().setAttribute("position",new Float32BufferAttribute(stripes,3));
    const pads=electrodes.map(([y,a])=>{
      const p=new Vector3(...position(y,a));
      return p.add(new Vector3(Math.sin(a)*.022,.014,Math.cos(a)*.022));
    });
    const lines=[];
    for(const p of pads) {
      const lift=p.clone().multiplyScalar(1.13).add(new Vector3(0,.05,0));
      const port=new Vector3(-.75,1.36,-.15);
      lines.push(...p,...lift,...lift,...port);
    }
    const leads=new BufferGeometry().setAttribute("position",new Float32BufferAttribute(lines,3));
    return {mesh,lattice,leads,pads};
  },[]);
  useEffect(()=>()=>{model.mesh.dispose();model.lattice.dispose();model.leads.dispose();},[model]);
  useEffect(()=>{
    pivot.current.rotation.y=.48+progress*.73;
    invalidate();
  },[progress,invalidate]);
  return <group ref={pivot} position={[0,.12,0]} rotation={[.06,.57,-.08]}>
    <mesh geometry={model.mesh}><meshStandardMaterial color="#283956" roughness={.73} side={DoubleSide}/></mesh>
    <lineSegments geometry={model.lattice} scale={[1.002,1,1.002]}><lineBasicMaterial color="#8ca7df" opacity={.36} transparent/></lineSegments>
    <lineSegments geometry={model.leads}><lineBasicMaterial color="#8ae2d5" opacity={.67} transparent/></lineSegments>
    {model.pads.map((pad,i)=><mesh key={i} position={pad}><sphereGeometry args={[.039,12,8]}/><meshBasicMaterial color={i===2?"#ccfff2":"#81d8cd"}/></mesh>)}
  </group>;
}

export default function HeadModel({progress,onReady}){
  return <Canvas aria-hidden="true" frameloop="demand" dpr={1}
    camera={{position:[.11,.02,4.5],fov:38}} gl={{alpha:true,powerPreference:"low-power",antialias:true}}
    fallback={null} onCreated={({gl})=>onReady(gl.domElement)}>
    <ambientLight intensity={.9}/>
    <directionalLight color="#b7cdf9" intensity={2.4} position={[1.5,3,3]}/>
    <directionalLight color="#a582ec" intensity={1.55} position={[-2,1,-1]}/>
    <Form progress={progress}/>
  </Canvas>;
}

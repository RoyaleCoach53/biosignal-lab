import { Canvas, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BufferGeometry, Float32BufferAttribute } from "three";
import { filaments } from "./geometry.mjs";

function Sculpture({progress,reduced}) {
  const group = useRef();
  const drag = useRef(null);
  const { gl, invalidate, camera } = useThree();
  const geometry = useMemo(() => {
    const position = [], color = [];
    for (const line of filaments()) {
      for (let i = 1; i < line.points.length; i++) {
        for (const point of [line.points[i - 1], line.points[i]]) {
          const light = Math.max(.13, (point[2]+.9)/1.8);
          const contrast = (line.type === "tract" ? 1 : .58) * light;
          const tint = line.side < 0 ? [.24,.72,1] : [.66,.42,1];
          position.push(...point);
          color.push(...tint.map(c => c * contrast));
        }
      }
    }
    return new BufferGeometry().setAttribute("position", new Float32BufferAttribute(position,3))
      .setAttribute("color", new Float32BufferAttribute(color,3));
  }, []);
  useEffect(() => () => geometry.dispose(), [geometry]);
  useEffect(()=>{
    if(!progress||reduced) return;
    const shift=value=>{
      if (value>=.99) return;
      camera.position.set(value*.64, value*.24, 5.5-value*.53);
      camera.lookAt(0,0,0);
      invalidate();
    };
    shift(progress.get());
    return progress.on("change",shift);
  },[progress,reduced,camera,invalidate]);
  useEffect(() => {
    const canvas = gl.domElement;
    const rotate = (x, y) => {
      group.current.rotation.y += x;
      group.current.rotation.x = Math.max(-1.2, Math.min(1.2, group.current.rotation.x + y));
      invalidate();
    };
    const start = e => {
      if (e.button !== 0) return;
      drag.current = [e.clientX, e.clientY];
      canvas.setPointerCapture(e.pointerId);
    };
    const move = e => {
      if (!drag.current) return;
      rotate((e.clientX-drag.current[0])*.009, (e.clientY-drag.current[1])*.009);
      drag.current = [e.clientX,e.clientY];
    };
    const end = () => { drag.current = null; };
    const key = e => {
      const turn = {ArrowLeft:[-.15,0],ArrowRight:[.15,0],ArrowUp:[0,-.15],ArrowDown:[0,.15]}[e.key];
      if (!turn) return;
      e.preventDefault();
      rotate(...turn);
    };
    const events = {pointerdown:start,pointermove:move,pointerup:end,pointercancel:end,lostpointercapture:end,keydown:key};
    Object.entries(events).forEach(([name, fn]) => canvas.addEventListener(name, fn));
    canvas.tabIndex = 0;
    canvas.setAttribute("aria-label", "Interactive brain illustration. Use arrow keys to rotate.");
    return () => Object.entries(events).forEach(([name,fn]) => canvas.removeEventListener(name,fn));
  }, [gl, invalidate]);
  return <group ref={group} rotation={[-.30,-.37,-.33]}><lineSegments geometry={geometry}>
    <lineBasicMaterial vertexColors transparent opacity={.62} depthWrite={false} />
  </lineSegments></group>;
}
export default function Atlas({onFailure,onReady,progress,reduced}) {
  return <Canvas aria-label="Drag or use arrow keys to rotate the model" frameloop="demand"
    dpr={[1,1.4]} camera={{position:[0,0,5.7],fov:33}}
    gl={{alpha:true,antialias:true,powerPreference:"low-power"}}
    fallback={<p className="atlas-note">3D unavailable. Static illustration retained.</p>}
    onCreated={({gl}) => { gl.domElement.addEventListener("webglcontextlost", onFailure, {once:true}); onReady(); }}>
    <Sculpture progress={progress} reduced={reduced}/>
  </Canvas>;
}

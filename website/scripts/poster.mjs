import { writeFileSync } from "node:fs";
import { filaments } from "../src/geometry.mjs";

const palette = {"-1": "#719dff", "1": "#a38bff"};
const project = ([x,y,z]) => {
  const pitch = .22;
  const yaw = -.26;
  const longitudinal = y * Math.cos(pitch) - z * Math.sin(pitch);
  const depth = y * Math.sin(pitch) + z * Math.cos(pitch);
  const lateral = x * Math.cos(yaw) + depth * Math.sin(yaw);
  return [lateral * 133 + 260, -longitudinal * 133 + 225, depth * Math.cos(yaw) - x * Math.sin(yaw)];
};
const groups = new Map();
for (const {side,type,points} of filaments()) {
  const nodes = points.map(project);
  let previous;
  for (let i=0; i<nodes.length-1; i++) {
    const [x1,y1,z1]=nodes[i], [x2,y2,z2]=nodes[i+1];
    const d = Math.max(0, Math.min(1, ((z1+z2)/2+.25)/1.2));
    const alpha = type === "tract" ? .13 + d*.73 : .028+d*(type==="latitude"?.43:.25);
    const shade = type === "tract" ? "#c7deff" : palette[side];
    const key = [shade,(Math.max(1,Math.round(alpha*32))/32).toFixed(3),type==="tract"?1.1:.64].join(" ");
    const start = key === previous ? "" : "M"+x1.toFixed(1)+" "+y1.toFixed(1);
    groups.set(key,(groups.get(key)??"")+start+"L"+x2.toFixed(1)+" "+y2.toFixed(1));
    previous = key;
  }
}
const paths = [...groups].sort(([a],[b])=>+a.split(" ")[1]-+b.split(" ")[1]).map(([key,path])=>{
  const [color,opacity,width] = key.split(" ");
  return `<path d="${path}" stroke="${color}" opacity="${opacity}" stroke-width="${width}"/>`;
}).join("");
writeFileSync(new URL("../public/neural-atlas.svg", import.meta.url),
  `<svg xmlns="http://www.w3.org/2000/svg" width="520" height="450" viewBox="0 0 520 450"><g fill="none" stroke-linecap="round">${paths}</g></svg>`);

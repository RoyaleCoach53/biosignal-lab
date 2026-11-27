import {test,expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const route="/website/test/fixtures/studio-editor-harness.html";
const editor=page=>page.frameLocator("#editor");
async function latest(page){return page.evaluate(()=>window.bridgeEvents.at(-1));}
async function open(page){await page.goto(route);await expect(editor(page).getByRole("button",{name:"Move node demo",exact:true})).toBeVisible();}
async function output(frame,id,port,kind){await frame.getByRole("button",{name:new RegExp(`^Output ${port} ${kind}, ${id}\\.${port}`)}).click();}
async function input(frame,id,port,kind){await frame.getByRole("button",{name:new RegExp(`^Input ${port} ${kind}, ${id}\\.${port}`)}).click();}

test("loads typed graph, edits parameters and safely adds only registered nodes",async({page})=>{
  await open(page);const frame=editor(page);
  await expect(frame.getByRole("article")).toHaveCount(3);
  await frame.getByRole("button",{name:"Edit parameters for demo",exact:true}).click();
  await frame.getByLabel("Parameter object (JSON)").fill('{"sfreq":500,"duration_s":12,"n_channels":4}');
  await frame.getByRole("button",{name:"Apply parameters"}).click();
  expect((await latest(page)).workflow.nodes[0].parameters.sfreq).toBe(500);
  expect((await latest(page)).graph_digest).toBe("fixture-v1");
  await frame.getByLabel("Find a node").fill("processed");
  await expect(frame.getByLabel("Node type").locator("option")).toHaveCount(1);
  await frame.getByRole("button",{name:"Add node",exact:true}).click();
  expect((await latest(page)).workflow.nodes.at(-1)).toEqual({id:"processed",kind:"processed",parameters:{},inputs:{}});
  await expect(frame.getByRole("status",{name:"Editor status"})).toContainText("required inputs");
});

test("connects typed ports, rejects incompatible ports and cycles, and disconnects",async({page})=>{
  await open(page);const frame=editor(page);
  await frame.getByLabel("Node type").selectOption("processed");
  await frame.getByRole("button",{name:"Add node",exact:true}).click();
  // Fit avoids overlaps between the new node and the initial source.
  await frame.getByRole("button",{name:"Arrange",exact:true}).click();
  await output(frame,"analysis","out","analysis");await input(frame,"processed","analysis","analysis");
  expect((await latest(page)).workflow.nodes.at(-1).inputs).toEqual({analysis:{node:"analysis",port:"out"}});
  await output(frame,"report","out","json");await input(frame,"analysis","signal","recording");
  await expect(frame.getByRole("status",{name:"Editor status"})).toContainText("Incompatible");
  expect((await latest(page)).workflow.nodes[1].inputs.signal.node).toBe("demo");
  await output(frame,"processed","out","recording");await input(frame,"analysis","signal","recording");
  await expect(frame.getByRole("status",{name:"Editor status"})).toContainText("cycle");
  await frame.getByText("Connections and keyboard instructions",{exact:true}).click();
  await frame.getByRole("button",{name:"Disconnect analysis.out → processed.analysis",exact:true}).click();
  expect((await latest(page)).workflow.nodes.at(-1).inputs).toEqual({});
});

test("supports keyboard movement, node deletion, undo/redo and acknowledged revisions",async({page})=>{
  await open(page);const frame=editor(page);
  await frame.getByRole("button",{name:"Move node demo",exact:true}).focus();
  await page.keyboard.press("ArrowRight");
  expect((await latest(page)).positions.demo.x).toBe(10);
  await page.evaluate(()=>{window.autoAcknowledge=false;const event=window.bridgeEvents.at(-1);window.args={...window.args,...event,event_ack:event.event_id,graph_digest:"acknowledged-v2"};window.renderEditor();});
  await frame.getByRole("button",{name:"Undo",exact:true}).click();
  expect((await latest(page)).positions.demo.x).toBe(0);
  expect((await latest(page)).graph_digest).toBe("acknowledged-v2");
  await page.evaluate(()=>{const event=window.bridgeEvents.at(-1);window.args={...window.args,...event,event_ack:event.event_id};window.renderEditor();window.autoAcknowledge=true;});
  await frame.getByRole("button",{name:"Redo",exact:true}).click();
  expect((await latest(page)).positions.demo.x).toBe(10);
  await frame.getByRole("button",{name:"Move node report",exact:true}).focus();
  await page.keyboard.press("Delete");
  await expect.poll(async()=> (await latest(page))?.workflow.nodes.map(node=>node.id)).toEqual(["demo","analysis"]);
});

test("queues rapid edits until the parent acknowledges its revision",async({page})=>{
  await open(page);const frame=editor(page);
  await page.evaluate(()=>{window.autoAcknowledge=false;});
  await frame.getByRole("button",{name:"Move node demo",exact:true}).focus();
  await page.keyboard.press("ArrowRight");await page.keyboard.press("ArrowRight");await page.keyboard.press("ArrowRight");
  expect(await page.evaluate(()=>window.bridgeEvents.length)).toBe(1);
  expect((await latest(page)).positions.demo.x).toBe(10);
  await page.evaluate(()=>{const event=window.bridgeEvents[0];window.renderEditor({...window.args,...event,event_ack:event.event_id,graph_digest:"new-server-revision"});});
  await expect.poll(()=>page.evaluate(()=>window.bridgeEvents.length)).toBe(2);
  const buffered=await latest(page);
  expect(buffered.graph_digest).toBe("new-server-revision");expect(buffered.positions.demo.x).toBe(30);
});

test("drag changes persisted positions, zoom and pan change only viewport",async({page},info)=>{
  await open(page);const frame=editor(page);
  const title=frame.getByRole("button",{name:"Move node demo",exact:true});
  const before=await title.boundingBox();
  const x=before.x+before.width/2,y=before.y+before.height/2;
  await page.mouse.move(x,y);await page.mouse.down();
  await page.mouse.move(x+50,y+55,{steps:8});await page.mouse.up();
  await expect.poll(async()=> (await latest(page))?.positions.demo.x).toBeGreaterThan(0);
  const value=await latest(page);expect(value.positions.demo.x).toBeGreaterThan(0);expect(value.positions.demo.y).toBeGreaterThan(30);
  const count=await page.evaluate(()=>window.bridgeEvents.length);
  const zoom=await frame.getByLabel("Zoom level").innerText();
  await frame.getByRole("button",{name:"Zoom in",exact:true}).click();
  await expect(frame.getByLabel("Zoom level")).not.toHaveText(zoom);
  await frame.getByRole("region",{name:"Scientific workflow canvas"}).focus();
  await page.keyboard.press("ArrowRight");
  expect(await page.evaluate(()=>window.bridgeEvents.length)).toBe(count);
});

test("imports and exports data-only workflows; rejects unavailable algorithms and malformed parameters",async({page})=>{
  await open(page);const frame=editor(page);
  await frame.getByRole("button",{name:"Edit parameters for demo",exact:true}).click();
  await frame.getByLabel("Parameter object (JSON)").fill('[1,2,3]');
  await frame.getByRole("button",{name:"Apply parameters"}).click();
  await expect(frame.getByRole("alert").filter({hasText:"Parameters must be a JSON object"})).toBeVisible();
  await frame.getByRole("button",{name:"Cancel",exact:true}).click();
  const invalid={schema_version:1,name:"Unsafe",nodes:[{id:"unknown",kind:"untrusted-plugin",parameters:{},inputs:{}}]};
  await frame.locator("#file").setInputFiles({name:"bad.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(invalid))});
  await expect(frame.getByRole("status",{name:"Editor status"})).toContainText("Unavailable node type");
  const valid={schema_version:1,name:"Imported synthetic",nodes:[{id:"clean",kind:"simulate",parameters:{seed:7},inputs:{}}]};
  await frame.locator("#file").setInputFiles({name:"valid.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(valid))});
  await expect.poll(async()=> (await latest(page))?.workflow).toEqual(valid);
  const download=page.waitForEvent("download");await frame.getByRole("button",{name:"Export JSON",exact:true}).click();
  const result=await download;expect(result.suggestedFilename()).toBe("biosignal-workflow.json");
  const stream=await result.createReadStream();const chunks=[];for await(const chunk of stream)chunks.push(chunk);
  expect(JSON.parse(Buffer.concat(chunks).toString())).toEqual(valid);
  await frame.getByRole("button",{name:"Delete node clean",exact:true}).click();
  await expect(frame.getByRole("status",{name:"Editor status"})).toContainText("at least one node");
});

test("renders server errors as text and respects disabled editing",async({page})=>{
  await open(page);
  await page.evaluate(()=>window.renderEditor({...window.args,errors:['<img src=x onerror="alert(1)"> incompatible metadata'],disabled:true}));
  const frame=editor(page);
  await expect(frame.getByRole("alert")).toContainText('<img src=x onerror="alert(1)"> incompatible metadata');
  await expect(frame.locator("#errors img")).toHaveCount(0);
  await expect(frame.getByRole("button",{name:"Add node",exact:true})).toBeDisabled();
  await expect(frame.getByRole("button",{name:"Edit parameters for demo",exact:true})).toBeDisabled();
  const result=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]).analyze();
  expect(result.violations.map(item=>({id:item.id,nodes:item.nodes.map(node=>node.target)}))).toEqual([]);
});

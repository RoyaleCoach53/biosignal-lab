import {test,expect} from "@playwright/test";
const editor=page=>page.frameLocator('iframe[title$="biosignal_studio_editor"]');
async function open(page){
  await page.goto("");
  await expect(page.getByRole("button",{name:"Run workflow",exact:true})).toBeEnabled({timeout:45000});
  await expect(editor(page).getByRole("button",{name:"Edit parameters for demo",exact:true})).toBeVisible();
}
async function downloadJSON(page,label){
  const event=page.waitForEvent("download");await page.getByRole("button",{name:label,exact:true}).click();
  const download=await event,stream=await download.createReadStream(),chunks=[];
  for await(const chunk of stream)chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString());
}
async function synchronized(frame){await expect(frame.getByRole("status",{name:"Editor status"})).toContainText("synchronized with Python",{timeout:20000});}

test("visual parameter edits reach Python and execute a real six-node experiment",async({page})=>{
  await open(page);const frame=editor(page);
  await frame.getByRole("button",{name:"Edit parameters for demo",exact:true}).click();
  await frame.getByLabel("Parameter object (JSON)").fill('{"duration_s":12,"sfreq":500,"n_channels":3,"seed":7}');
  await frame.getByRole("button",{name:"Apply parameters",exact:true}).click();
  await synchronized(frame);
  const graph=await downloadJSON(page,"Download workflow");
  expect(graph.nodes.find(node=>node.id==="demo").parameters).toEqual({duration_s:12,sfreq:500,n_channels:3,seed:7});
  await page.getByRole("button",{name:"Run workflow",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Execution results",exact:true})).toBeVisible();
  await expect(page.getByText("3 channels · 500 Hz · 12 seconds · µV",{exact:true})).toBeVisible();
  const manifest=await downloadJSON(page,"Download execution manifest");
  expect(manifest.workflow).toEqual(graph);expect(manifest.nodes).toHaveLength(6);
  expect(manifest.nodes.every(node=>typeof node.seconds==="number" && node.seconds>=0)).toBe(true);
  expect(manifest.source_sha256).toMatch(/^[a-f0-9]{64}$/);expect(manifest.workflow_sha256).toMatch(/^[a-f0-9]{64}$/);
});

test("visual incomplete draft blocks execution until a real typed connection is made",async({page})=>{
  await open(page);const frame=editor(page);
  await frame.getByLabel("Node type").selectOption("analyze");
  await frame.getByRole("button",{name:"Add node",exact:true}).click();await synchronized(frame);
  await expect(page.getByRole("button",{name:"Run workflow",exact:true})).toBeDisabled();
  await expect(frame.locator("#errors")).toContainText("analyze");
  await frame.getByRole("button",{name:"Arrange",exact:true}).click();await synchronized(frame);
  await frame.locator('[data-node="demo"][data-direction="outputs"][data-port="out"]').click();
  await frame.locator('[data-node="analyze"][data-direction="inputs"][data-port="signal"]').click();await synchronized(frame);
  await expect(page.getByRole("button",{name:"Run workflow",exact:true})).toBeEnabled();
  const workflow=await downloadJSON(page,"Download workflow");
  expect(workflow.nodes.find(node=>node.id==="analyze").inputs.signal).toEqual({node:"demo",port:"out"});
  await page.getByRole("button",{name:"Run workflow",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Execution results",exact:true})).toBeVisible();
  expect((await downloadJSON(page,"Download execution manifest")).nodes).toHaveLength(7);
});

test("rapid visual edits retain the complete final graph after Python acknowledgement",async({page})=>{
  await open(page);const frame=editor(page);
  await frame.getByLabel("Node type").selectOption("simulate");
  // A single-flight bridge must retain edits made during Streamlit's rerun.
  await frame.getByRole("button",{name:"Add node",exact:true}).click();
  await frame.getByRole("button",{name:"Add node",exact:true}).click();
  await frame.getByRole("button",{name:"Add node",exact:true}).click();
  await synchronized(frame);
  await expect(frame.getByRole("article")).toHaveCount(9);
  const workflow=await downloadJSON(page,"Download workflow");
  expect(workflow.nodes).toHaveLength(9);
  expect(new Set(workflow.nodes.map(node=>node.id)).size).toBe(9);
});

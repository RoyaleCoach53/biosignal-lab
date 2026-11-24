import { chromium, devices } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const url=process.env.SITE_TEST_URL||"http://127.0.0.1:4173/";
const out=resolve(process.argv[2]||"test-results/screenshots");
await mkdir(out,{recursive:true});
const browser=await chromium.launch({
  channel:process.env.SITE_CHROME_CHANNEL||undefined,
  args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"],
});
try {
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  const failures=[];
  page.on("pageerror",err=>failures.push(err.message));
  await page.goto(url);
  await page.locator(".opening-poster").evaluate(img=>img.decode());
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:resolve(out,"desktop.jpg"),quality:88});
  await page.getByRole("button",{name:"Explore in 3D"}).click();
  const canvas=page.locator(".opening-art canvas");

  await canvas.waitFor({state:"visible",timeout:12000});
  await page.locator('canvas[tabindex="0"]').waitFor();
  await canvas.focus();
  const start=await canvas.screenshot();
  await page.keyboard.press("ArrowRight");
  if(start.equals(await canvas.screenshot())) throw new Error("3D did not update on keyboard rotation");
  await page.locator(".opening-art").screenshot({path:resolve(out,"brain-3d.jpg"),quality:88});
  await page.getByRole("button",{name:"Close 3D"}).click();
  await page.getByRole("link",{name:"Begin the journey"}).click();
  await page.getByRole("button",{name:"Trace the axon"}).waitFor();
  for(const [chapter,file,selector] of [
    ["Neural origins","neuron.jpg",".scientific-art"],
    ["Scalp acquisition","acquisition.jpg",".head-visual"],
    ["Filter response","filters.jpg",".scene-name:has-text('Filter response')"],
    ["Welch estimation","welch.jpg",".scene-name:has-text('Welch estimation')"],
    ["Surface EMG","emg.jpg",".muscle-scene"],
  ]){
    await page.getByRole("navigation",{name:"Jump to a chapter"}).getByRole("link",{name:new RegExp(chapter)}).click();
    await page.locator(".stage "+selector).waitFor();
    if(chapter==="Scalp acquisition"){
      await page.emulateMedia({reducedMotion:"no-preference"});
      await page.locator(".head-live canvas").waitFor({state:"visible",timeout:10000});
    }
    await page.locator(".stage-wrap").screenshot({path:resolve(out,file),quality:88});

  }
  await page.getByRole("navigation",{name:"Main navigation"}).getByRole("link",{name:"Workbench"}).click();
  await page.getByRole("heading",{name:"Channel overview"}).waitFor();
  await page.locator(".lab").screenshot({path:resolve(out,"workbench.jpg"),quality:88});
  await page.locator("#lab").getByRole("button",{name:"Spectrogram",exact:true}).click();
  await page.getByRole("heading",{name:"Processed spectrogram"}).waitFor();
  await page.locator(".spectrum-heat").screenshot({path:resolve(out,"spectrogram.jpg"),quality:88});
  if(failures.length)throw new Error(failures.join("\n"));
  const live=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:"no-preference"});
  await live.goto(url);
  await live.getByRole("link",{name:"Begin the journey"}).click();
  await live.getByRole("navigation",{name:"Jump to a chapter"}).getByRole("link",{name:/Scalp acquisition/}).click();
  await live.locator(".head-live canvas").waitFor({state:"visible",timeout:10000});
  await live.locator(".stage-wrap").screenshot({path:resolve(out,"acquisition-3d.jpg"),quality:88});
  await live.close();
  const phone=await browser.newPage({...devices["Pixel 7"],reducedMotion:"reduce"});
  await phone.goto(url);
  await phone.locator(".opening-poster").evaluate(img=>img.decode());
  await phone.evaluate(()=>document.fonts.ready);
  await phone.screenshot({path:resolve(out,"mobile.jpg"),quality:88,scale:"css"});
  const tablet=await browser.newPage({viewport:{width:900,height:1180},reducedMotion:"reduce"});
  await tablet.goto(url);
  if(await tablet.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error("Tablet horizontal overflow");
  if(process.env.SITE_RECORD==="1"){
    const context=await browser.newContext({viewport:{width:1280,height:800},recordVideo:{dir:out,size:{width:1280,height:800}}});
    const recording=await context.newPage();
    await recording.goto(url);
    await recording.locator(".opening-poster").evaluate(img=>img.decode());
    await recording.waitForTimeout(950);
    await recording.getByRole("link",{name:"Begin the journey"}).click();
    await recording.getByRole("button",{name:"Trace the axon"}).waitFor();
    for(const chapter of ["Scalp acquisition","Filter response","Welch estimation","Surface EMG"]){
      await recording.getByRole("navigation",{name:"Jump to a chapter"}).getByRole("link",{name:new RegExp(chapter)}).click();
      await recording.waitForTimeout(1450);
    }
    await recording.getByRole("navigation",{name:"Main navigation"}).getByRole("link",{name:"Workbench"}).click();
    await recording.getByRole("heading",{name:"Channel overview"}).waitFor();
    await recording.waitForTimeout(1600);
    await recording.locator("#lab").getByRole("button",{name:"Spectrogram",exact:true}).click();
    await recording.getByRole("heading",{name:"Processed spectrogram"}).waitFor();
    await recording.waitForTimeout(1300);
    const video=recording.video();
    await context.close();
    await video.saveAs(resolve(out,"scroll-journey.webm"));
    await video.delete();
  }
}finally{await browser.close();}

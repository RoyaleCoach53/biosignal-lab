import { chromium, devices } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const url = process.env.SITE_TEST_URL || "http://127.0.0.1:4173/";
const out = resolve(process.argv[2] || "test-results/screenshots");
await mkdir(out,{recursive:true});
const browser = await chromium.launch({channel:process.env.SITE_CHROME_CHANNEL || undefined,args:["--enable-unsafe-swiftshader"]});
try {
  const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:"reduce"});
  const failures=[];
  page.on("pageerror",err=>failures.push(err.message));
  await page.goto(url);
  await page.locator(".atlas-poster").evaluate(img=>img.decode());
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:resolve(out,"desktop.jpg"),quality:90});
  await page.getByRole("button",{name:"Interactive 3D"}).click();
  const canvas=page.locator("canvas");
  await canvas.waitFor({state:"visible",timeout:10000});
  await canvas.focus();
  const start=await canvas.screenshot();
  await page.keyboard.press("ArrowRight");
  const after=await canvas.screenshot();
  if(start.equals(after)) throw new Error("3D image did not update on keyboard rotation");
  await page.locator(".hero-visual").screenshot({path:resolve(out,"interactive-atlas.jpg"),quality:90});
  await page.getByRole("button",{name:"Close 3D"}).click();
  await page.getByRole("link",{name:"Enter the signal lab"}).click();
  await page.getByRole("heading",{name:"Welch spectrum"}).waitFor();
  await page.locator(".lab").screenshot({path:resolve(out,"synthetic-eeg.jpg"),quality:90});
  if(failures.length) throw new Error(failures.join("\n"));
  const phone=await browser.newPage({...devices["Pixel 7"],reducedMotion:"reduce"});
  await phone.goto(url);
  await phone.locator(".atlas-poster").evaluate(img=>img.decode());
  await phone.evaluate(()=>document.fonts.ready);
  await phone.screenshot({path:resolve(out,"mobile.jpg"),quality:90});
} finally {
  await browser.close();
}

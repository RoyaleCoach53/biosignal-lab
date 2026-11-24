import {test, expect} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("navigation, responsive layout, keyboard, Arabic and reduced motion", async ({page},info) => {
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link",{name:"Skip to content"})).toBeFocused();
  if (info.project.name==="mobile") await page.getByRole("button",{name:"Menu"}).click();
  await page.getByRole("navigation").getByRole("link",{name:"Methods",exact:true}).click();
  await expect(page).toHaveURL(/#methods$/);
  await page.getByRole("button",{name:/عرض بالعربية/}).click();
  await expect(page.locator("html")).toHaveAttribute("dir","rtl");
  await expect(page.locator("html")).toHaveAttribute("lang","ar");
  await expect(page.getByRole("heading",{level:1})).toContainText("الإشارة");
  await page.getByRole("button",{name:/Switch to English/}).click();
  await expect(page.locator("html")).toHaveAttribute("dir","ltr");
  await expect(page.locator(".scan")).toBeHidden();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.getByRole("link",{name:"Download v0.3.0"})).toHaveAttribute("href",/releases\/tag\/v0\.3\.0$/);
});

test("EEG and EMG scenario controls, inspection, download and scope",async({page})=>{
  await page.goto("#lab");
  await expect(page.getByLabel("Channel").locator("option")).toHaveCount(8);
  await page.getByLabel("Channel").selectOption("7");
  await expect(page.getByText("EEG / Ch8",{exact:false})).toBeVisible();
  const rms=page.getByLabel("Quality summaries").getByText("Raw RMS").locator("..").locator("strong");
  const transient=await rms.innerText();
  await page.getByLabel("Signal condition").selectOption("clean");
  await expect(rms).not.toHaveText(transient);
  await page.getByLabel("Filter preset").selectOption("high");
  await expect(page.getByRole("link",{name:/Download this synthetic/})).toHaveAttribute("href",/eeg-clean-high\.json$/);
  await page.getByRole("slider",{name:"Inspect time"}).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.locator(".readout").first()).toContainText("processed");
  await page.getByRole("button",{name:"Raw",exact:true}).first().click();
  await expect(page.getByRole("button",{name:"Raw",exact:true}).first()).toHaveAttribute("aria-pressed","false");
  await expect(page.getByRole("heading",{name:"Processed EEG band power"})).toBeVisible();
  await page.getByRole("button",{name:"EMG",exact:true}).click();
  await expect(page.getByText("EMG / Ch1",{exact:false})).toBeVisible();
  await expect(page.getByRole("heading",{name:"Processed EEG band power"})).toHaveCount(0);
  await page.getByLabel("Signal amplitude").selectOption("strong");
  await page.getByLabel("Filter preset").selectOption("low");
  await expect(page.getByRole("link",{name:/Download this synthetic/})).toHaveAttribute("href",/emg-strong-low\.json$/);
  await expect(page.locator("input[type=file], form")).toHaveCount(0);
});

test("scenario fetch error clears on retry", async ({page})=>{
  await page.route("**/scenarios/eeg-burst-standard.json",route=>route.abort(),{times:1});
  await page.goto("#lab");
  await expect(page.getByRole("alert")).toContainText("could not be loaded");
  await page.getByRole("button",{name:"Retry"}).click();
  await expect(page.getByText("EEG / Ch1",{exact:false})).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("poster remains when WebGL is unavailable",async({page})=>{
  await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext=function(type,...args){return type.startsWith("webgl")?null:original.call(this,type,...args);};});
  await page.goto("");
  await page.getByRole("button",{name:"Interactive 3D"}).click();
  await expect(page.getByText("Static atlas · WebGL unavailable")).toBeVisible();
  await expect(page.getByRole("img",{name:"Procedural illustration"})).toBeVisible();
  await expect(page.locator("canvas")).toHaveCount(0);
});

test("axe finds no WCAG A/AA violations",async({page})=>{
  await page.goto("#lab");
  await expect(page.getByRole("heading",{name:"Welch spectrum"})).toBeVisible();
  const result=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]).analyze();
  expect(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
});

import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("homepage, navigation, keyboard, Arabic and reduced motion", async ({page},info) => {
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link",{name:"Skip to content"})).toBeFocused();
  await expect(page.getByRole("heading",{level:1})).toContainText("a signal.");
  const intro=page.locator("header, .cinema-hero, footer");
  for (const phrase of ["Independent Beta","five-person pilot","Design preview","Research Alpha","Pre-release"]) {
    await expect(intro.getByText(phrase,{exact:false})).toHaveCount(0);
  }
  if (info.project.name==="mobile") await page.getByRole("button",{name:"Menu"}).click();
  await page.getByRole("navigation",{name:"Main navigation"}).getByRole("link",{name:"Methods",exact:true}).click();
  await expect(page).toHaveURL(/#methods$/);
  await page.getByRole("button",{name:/عرض بالعربية/}).click();
  await expect(page.locator("html")).toHaveAttribute("dir","rtl");
  await expect(page.getByRole("heading",{level:1})).toContainText("بإشارة");
  await page.getByRole("button",{name:/Switch to English/}).click();
  await expect(page.locator("html")).toHaveAttribute("dir","ltr");
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.getByRole("link",{name:"Release and downloads"})).toHaveAttribute("href",/releases\/tag\/v0\.3\.0$/);
});

test("scroll journey is reversible and showcases computed stages", async ({page}, info) => {
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("");
  await page.getByRole("link",{name:"Begin the journey"}).click();
  await expect(page.getByRole("heading",{name:"A field made by many."})).toBeVisible();
  const desktop=info.project.name==="desktop";
  const jump=async (label,id)=>{
    if(desktop){
      await page.getByRole("navigation",{name:"Jump to a chapter"}).getByRole("link",{name:new RegExp(label)}).click();
      await expect(page.getByRole("navigation",{name:"Jump to a chapter"}).getByRole("link",{name:new RegExp(label)})).toHaveAttribute("aria-current","location");
    } else await page.locator("#chapter-"+id).scrollIntoViewIfNeeded();
  };
  await page.getByRole("button",{name:"Trace the axon"}).click();
  await expect(page.locator(".axon-flash")).toHaveCount(1);
  await jump("Scalp acquisition","acquisition");
  await page.getByRole("button",{name:"Amplify",exact:true}).click();
  await expect(page.getByText(/differential amplifier boosts/)).toBeVisible();
  await jump("Filter response","processing");
  await page.getByRole("button",{name:"35 Hz low-pass",exact:true}).click();
  await expect(page.getByRole("button",{name:"35 Hz low-pass",exact:true})).toHaveAttribute("aria-pressed","true");
  await jump("Welch estimation","spectrum");
  await page.getByRole("button",{name:"Apply Hann"}).click();
  await expect(page.getByText(/periodic Hann taper/)).toBeVisible();
  await page.getByRole("button",{name:"Average"}).click();
  await page.getByLabel("Focus").selectOption("4");
  await expect(page.getByLabel("Focus")).toHaveValue("4");
  await jump("Surface EMG","emg");
  await expect(page.getByText(/computed synthetic EMG below/)).toBeVisible();
  await jump("Neural origins","origin");
  await expect(page.getByRole("button",{name:"Trace the axon"})).toBeVisible();
});

test("workbench dimensions, inspection and modality changes",async({page})=>{
  await page.goto("#lab");
  const lab=page.locator("#lab");
  await expect(lab.getByLabel("Channel").locator("option")).toHaveCount(8);
  await lab.getByRole("button",{name:"Ch8",exact:true}).click();
  await expect(lab.getByText("EEG / Ch8",{exact:false})).toBeVisible();
  const rms=lab.getByLabel("Quality summaries").getByText("Raw RMS").locator("..").locator("strong");
  const transient=await rms.innerText();
  await lab.getByLabel("Signal condition").selectOption("clean");
  await expect(rms).not.toHaveText(transient);
  await lab.getByLabel("Filter preset").selectOption("high");
  await lab.getByLabel("Sampling frequency").selectOption("128");
  await expect(lab.getByRole("link",{name:/Download this synthetic/})).toHaveAttribute("href",/eeg-clean-high-128\.json$/);
  await lab.getByRole("slider",{name:"Inspect time"}).focus();
  await page.keyboard.press("ArrowRight");
  await expect(lab.locator(".readout")).toContainText("processed");
  await lab.getByRole("button",{name:"Raw",exact:true}).click();
  await expect(lab.getByRole("button",{name:"Raw",exact:true})).toHaveAttribute("aria-pressed","false");
  await lab.getByRole("button",{name:"Spectrum",exact:true}).click();
  await expect(lab.getByRole("heading",{name:"Welch spectrum"})).toBeVisible();
  await expect(lab.getByRole("heading",{name:"Processed EEG band power"})).toBeVisible();
  await lab.getByRole("button",{name:"Spectrogram",exact:true}).click();
  await expect(lab.getByRole("heading",{name:"Processed spectrogram"})).toBeVisible();
  await lab.getByRole("slider",{name:"Frequency bin"}).focus();
  await page.keyboard.press("ArrowRight");
  await expect(lab.getByRole("slider",{name:"Frequency bin"})).toHaveAttribute("aria-valuetext","0.5 hertz");
  await expect(lab.locator(".readout")).toContainText("0.5 Hz");
  await lab.getByRole("button",{name:"EMG",exact:true}).click();
  await expect(lab.getByText("EMG / Ch1",{exact:false})).toBeVisible();
  await expect(lab.getByRole("heading",{name:"Processed EEG band power"})).toHaveCount(0);
  await lab.getByLabel("Signal amplitude").selectOption("strong");
  await lab.getByLabel("Sampling frequency").selectOption("2000");
  await lab.getByLabel("Filter preset").selectOption("low");
  await expect(lab.getByRole("link",{name:/Download this synthetic/})).toHaveAttribute("href",/emg-strong-low-2000\.json$/);
  await expect(lab.getByRole("link",{name:/Download spectrogram/})).toHaveAttribute("href",/emg-strong-low-2000-spectrogram\.json$/);
  await expect(page.locator("input[type=file], form")).toHaveCount(0);
});

test("synthetic request failure clears on retry", async ({page})=>{
  await page.route("**/scenarios/eeg-burst-standard-250.json",route=>route.abort(),{times:1});
  await page.goto("#lab");
  const lab=page.locator("#lab");
  await expect(lab.getByRole("alert")).toContainText("could not be loaded");
  await lab.getByRole("button",{name:"Retry",exact:true}).click();
  await expect(lab.getByText("EEG / Ch1",{exact:false})).toBeVisible();
  await expect(lab.getByRole("alert")).toHaveCount(0);
});

test("poster remains when WebGL is unavailable",async({page})=>{
  await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext=function(type,...args){return type.startsWith("webgl")?null:original.call(this,type,...args);};});
  await page.goto("");
  await page.getByRole("button",{name:"Explore in 3D"}).click();
  await expect(page.getByText("Static atlas · WebGL unavailable")).toBeVisible();
  await expect(page.getByRole("img",{name:"Procedural brain illustration"})).toBeVisible();
  await expect(page.locator("canvas")).toHaveCount(0);
});

test("axe finds no WCAG A/AA violations in the loaded workbench",async({page})=>{
  await page.goto("#lab");
  await expect(page.getByRole("heading",{name:"Signal trace"})).toBeVisible();
  const result=await new AxeBuilder({page}).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa"]).analyze();
  expect(result.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
});

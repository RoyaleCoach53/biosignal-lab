import {defineConfig,devices} from "@playwright/test";
if(!process.env.SITE_STUDIO_URL) throw new Error("Start the actual Studio app and set SITE_STUDIO_URL before running backend E2E checks.");
export default defineConfig({
  testDir:"./test",testMatch:"studio-backend.spec.mjs",fullyParallel:false,workers:1,
  timeout:60000,
  use:{...devices["Desktop Chrome"],baseURL:process.env.SITE_STUDIO_URL,viewport:{width:1440,height:1100},trace:"retain-on-failure",
    launchOptions:process.env.SITE_CHROME_EXECUTABLE?{executablePath:process.env.SITE_CHROME_EXECUTABLE}:undefined},
});

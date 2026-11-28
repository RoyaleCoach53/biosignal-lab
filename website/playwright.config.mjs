import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir:"./test",
  testMatch:"site.spec.mjs",
  outputDir:"test-results/site",
  fullyParallel:true,
  use:{baseURL:process.env.SITE_TEST_URL || "http://127.0.0.1:4173", trace:"retain-on-failure",
    launchOptions:process.env.SITE_CHROME_EXECUTABLE?{executablePath:process.env.SITE_CHROME_EXECUTABLE}:undefined},
  projects:[
    {name:"desktop",use:{...devices["Desktop Chrome"],viewport:{width:1440,height:900},channel:process.env.SITE_CHROME_CHANNEL || undefined}},
    {name:"mobile",use:{...devices["Pixel 7"],channel:process.env.SITE_CHROME_CHANNEL || undefined}},
  ],
  webServer:process.env.SITE_TEST_URL?undefined:{command:"npm run preview",url:"http://127.0.0.1:4173",reuseExistingServer:!process.env.CI},
});

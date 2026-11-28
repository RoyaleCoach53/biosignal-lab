import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir:"./test", testMatch:"studio-editor.spec.mjs", fullyParallel:true,
  outputDir:"test-results/studio-editor",
  use:{baseURL:"http://127.0.0.1:4174",trace:"retain-on-failure",
    launchOptions:process.env.SITE_CHROME_EXECUTABLE?{executablePath:process.env.SITE_CHROME_EXECUTABLE}:undefined},
  projects:[
    {name:"desktop",use:{...devices["Desktop Chrome"],viewport:{width:1440,height:1000}}},
    {name:"mobile",use:{...devices["Pixel 7"]}},
  ],
  webServer:{command:"python3 -m http.server 4174 --bind 127.0.0.1 --directory ..",url:"http://127.0.0.1:4174/website/test/fixtures/studio-editor-harness.html",reuseExistingServer:false},
});

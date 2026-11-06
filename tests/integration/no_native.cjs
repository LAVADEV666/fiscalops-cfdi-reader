/* Production HTML must never run legacy fiscal code when Qt is absent. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),modules=process.argv[2],base=process.argv[3];
const {chromium}=require(path.join(modules,'playwright'));
(async()=>{
 const browser=await chromium.launch({headless:true,chromiumSandbox:true,executablePath:'C:/Users/sin_s/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe'});
 const context=await browser.newContext({acceptDownloads:true});
 const page=await context.newPage(),errors=[],downloads=[];
 page.on('pageerror',error=>errors.push(String(error)));page.on('download',download=>downloads.push(download.suggestedFilename()));
 await page.goto(base+'/without-native/');await page.locator('#s2').waitFor({state:'visible'});
 await page.locator('#file').setInputFiles(path.join(root,'tests/fiscal/fixtures/p0_iva_ieps_40.xml'));
 await page.locator('#process').click();await page.waitForTimeout(300);
 const result={development_runtime_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'app/ui/legacy-runtime.js'))).digest('hex'),mode:await page.evaluate(()=>FiscalOpsRuntime.state.mode),reportOpened:await page.locator('#s3').evaluate(n=>n.classList.contains('on')),
  message:await page.locator('#status').innerText(),downloads,errors};
 await page.evaluate(()=>document.getElementById('csv').click());await page.waitForTimeout(100);
 result.success=result.mode==='unavailable'&&!result.reportOpened&&result.message.includes('aplicación de escritorio')&&!downloads.length&&!errors.length;
 fs.writeFileSync(path.join(root,'tests/integration/evidence/no-native.json'),JSON.stringify(result,null,2));
 await browser.close();console.log(JSON.stringify(result,null,2));if(!result.success)process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});

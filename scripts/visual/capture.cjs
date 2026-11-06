/* Real-browser baseline runner. No product source, fiscal state, timers, or CSS is patched. */
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..');
const args=process.argv.slice(2);
const option=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const modules=option('--modules',process.env.FISCALOPS_NODE_MODULES);
const {chromium}=require(modules?path.join(modules,'playwright'):'playwright');
const url=option('--url',JSON.parse(fs.readFileSync(path.join(root,'tests/visual/evidence/server.json'),'utf8')).url);
if(new URL(url).hostname!=='127.0.0.1')throw Error('Only literal 127.0.0.1 is allowed');
const executable=option('--browser',undefined);
const target=option('--target','reference');
const out=path.resolve(root,option('--output','tests/visual/baseline'));
if(!out.startsWith(root+path.sep))throw Error('Capture output must remain in this workspace');
if(fs.existsSync(path.join(out,'manifest.json')))throw Error('Baseline is frozen. Use --output tests/visual/candidate-NAME; do not overwrite reference.');
const evidence=out===path.join(root,'tests/visual/baseline')?path.join(root,'tests/visual/evidence'):path.join(out,'evidence');
const fixtures=path.join(root,'tests/visual/fixtures/AAA010101AAA');
const original=path.join(root,'FiscalOps_CFDI_READER_SSGT_V21_1_PRO.html');
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const sourceHash=hash(original);
if(sourceHash!=='33eeed2334a683b5360c2fc4f9cabc26885be66fef8714e4278f97235b8c373b')throw Error('Prototype changed');
if(hash(path.join(root,'legacy',path.basename(original)))!==sourceHash)throw Error('Legacy differs');
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(evidence,{recursive:true});
const report={date:new Date().toISOString(),prototype_sha256:sourceHash,target,method:target==='development'?'SPEC011 development copy; normal DOM/file-input interactions; no injected product state':'Unmodified original served on loopback; normal DOM/file-input interactions; no injected product state',system:{platform:os.platform(),release:os.release(),arch:os.arch()},browser:{},captures:[],checks:[],blocked:[],console:[],requests:[],buttonStates:[]};
if(target==='development')report.development_runtime_sha256=hash(path.join(root,'app/ui/legacy-runtime.js'));
function writeReport(){fs.writeFileSync(path.join(evidence,'navigation.json'),JSON.stringify(report,null,2));}
async function record(id,expected,action){try{const actual=await action();const pass=JSON.stringify(actual)===JSON.stringify(expected);report.checks.push({id,result:pass?'PASS':'FAIL',expected,actual});return actual}catch(e){report.checks.push({id,result:'ERROR',expected,error:String(e)});return null}finally{writeReport()}}
async function snapshot(page,scene,size){
  if(scene!=='19_processing_progress')await page.evaluate(async()=>{
    await Promise.all(document.getAnimations().filter(a=>a.effect?.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));
  });
  const name=`${scene}__${size.width}x${size.height}__dsf1.png`;
  const metadata=()=>page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight},deviceScaleFactor:devicePixelRatio,browserDefaultZoom:'100% in fresh automated context',cssZoom:getComputedStyle(document.documentElement).zoom,activeScreen:document.querySelector('.screen.on')?.id,modal:Array.from(document.querySelectorAll('.modal.on')).map(e=>e.id),status:document.querySelector('#status')?.textContent,progress:document.querySelector('#prog')?.value,font:getComputedStyle(document.body).fontFamily,v20Scale:getComputedStyle(document.documentElement).getPropertyValue('--v20-scale'),v21Scale:getComputedStyle(document.documentElement).getPropertyValue('--v21-scale')}));
  const before=await metadata();
  await page.screenshot({path:path.join(out,name),fullPage:false,animations:'allow'});
  const after=await metadata();
  const item={scene,file:name,sha256:hash(path.join(out,name)),before,after,capturedAt:new Date().toISOString(),animations:'original, running',windowsDesktopDPI:'NOT_MEASURED; DSF emulation does not prove Windows DPI'};
  report.captures.push(item);writeReport();return item;
}
async function buttonSnapshot(page,scene,size){
  const controls=await page.locator('button').evaluateAll(nodes=>nodes.map((n,index)=>({id:n.id||null,index,text:n.textContent.trim(),dataType:n.getAttribute('data-type'),dataOrigin:n.getAttribute('data-origin'),dataStatus:n.getAttribute('data-status'),dataMethod:n.getAttribute('data-metodo'),dataPreview:n.getAttribute('data-pv'),visible:!!(n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden'),disabled:n.disabled,active:n.classList.contains('on')})));
  report.buttonStates.push({scene,size,controls});writeReport();
}
async function run(){
  let browser;
  try{
    browser=await chromium.launch({executablePath:executable,headless:!args.includes('--headed'),chromiumSandbox:true,timeout:20000});
    report.browser={version:browser.version(),executable:executable||chromium.executablePath(),playwright:require(modules?path.join(modules,'playwright/package.json'):'playwright/package.json').version,headless:!args.includes('--headed')};writeReport();
    for(const size of [{width:1366,height:768},{width:1600,height:900},{width:1920,height:1080}]){
      console.log(`Capturing ${size.width}x${size.height}`);
      const context=await browser.newContext({viewport:size,deviceScaleFactor:1,acceptDownloads:true,locale:'es-MX',timezoneId:'America/Mexico_City'});
      await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(url).origin?route.continue():route.abort());
      const page=await context.newPage();page.setDefaultTimeout(8000);
      page.on('console',msg=>{if(['warning','error'].includes(msg.type()))report.console.push({size,type:msg.type(),text:msg.text()})});
      page.on('pageerror',e=>report.console.push({size,type:'pageerror',text:String(e)}));
      page.on('request',r=>report.requests.push({size,url:r.url(),method:r.method()}));
      report.browser.userAgent=await page.evaluate(()=>navigator.userAgent);
      await page.goto(url,{waitUntil:'load'});
      await snapshot(page,'01_initial',size);
      await record(`start-${size.width}`,true,async()=>{if(await page.locator('#s1').isVisible())await page.locator('#start').click();await page.locator('#s2').waitFor({state:'visible'});return true});
      await snapshot(page,'02_upload_empty',size);await buttonSnapshot(page,'upload',size);
      // Let the original 1600ms splash timer finish. It is NOT patched/canceled.
      // Attempt-01 records that a fast import can otherwise be sent back to s2.
      await page.waitForFunction(()=>performance.now()>1750);
      await record(`empty-process-disabled-${size.width}`,false,()=>page.locator('#process').isEnabled());
      await page.locator('#rfc').fill('AAA010101AAA');
      const files=fs.readdirSync(fixtures).filter(f=>/\.(xml|txt)$/.test(f)).map(f=>path.join(fixtures,f));
      await page.locator('#file').setInputFiles(files);
      await snapshot(page,'03_files_selected',size);
      await record(`selected-process-enabled-${size.width}`,true,()=>page.locator('#process').isEnabled());
      await page.locator('#process').click();await page.locator('#s3').waitFor({state:'visible'});
      await snapshot(page,'04_reports_table',size);await buttonSnapshot(page,'reports',size);
      await record(`table-has-rows-${size.width}`,true,async()=>await page.locator('#tbody tr[data-i]').count()>0);
      await record(`report-filter-single-click-${size.width}`,'I',async()=>{await page.locator('#typeTabs [data-type="I"]').click();return page.locator('#typeTabs').evaluate(n=>n.querySelector('button.on')?.getAttribute('data-type')||null)});
      await snapshot(page,'05_type_clicked',size);
      // SPEC011 fixes the click, so explicitly restore the unfiltered scope used
      // by all remaining historical cases. Keep the original click assertion.
      if(target==='development' && await page.locator('#typeTabs button.on').count())await page.locator('#typeTabs button.on').click();
      await page.locator('#q').fill('NOT-A-REAL-UUID');await page.waitForTimeout(250);
      await snapshot(page,'06_empty_filter',size);
      await record(`empty-filter-${size.width}`,0,()=>page.locator('#tbody tr[data-i]').count());
      await page.locator('#q').fill('');await page.waitForTimeout(250);
      await page.locator('#tbody tr[data-i]').first().click();await page.locator('#previewModal').waitFor({state:'visible'});
      await snapshot(page,'07_viewer_summary',size);await buttonSnapshot(page,'viewer',size);
      for(const [tab,scene] of [['impuestos','08_viewer_taxes'],['conceptos','09_viewer_concepts'],['datos','10_viewer_fields'],['xml','11_viewer_xml']]){
        await page.locator(`#previewBody [data-pv="${tab}"]`).click();
        await record(`viewer-tab-${tab}-${size.width}`,tab,()=>page.locator('#previewBody .pv-pane.on').getAttribute('data-pane'));
        await snapshot(page,scene,size);
      }
      await page.keyboard.press('Escape');await record(`viewer-escape-${size.width}`,false,()=>page.locator('#previewModal').isVisible());
      await page.locator('#editcols').click();await page.locator('#modal').waitFor({state:'visible'});
      await snapshot(page,'12_column_editor',size);await buttonSnapshot(page,'columns',size);
      await page.locator('#colSearch').fill('UUID');await snapshot(page,'13_column_search',size);
      const checkedBefore=await page.locator('#checks input:checked').count();
      await page.locator('#applycols').click();
      await record(`column-search-preserves-selection-${size.width}`,true,async()=>{const count=await page.locator('#thead th').count();return count>checkedBefore});
      await snapshot(page,'14_column_search_applied',size);
      await page.locator('#profileSel').selectOption('recommended');
      await page.locator('#excel').click();await page.locator('#exportModal').waitFor({state:'visible'});
      await snapshot(page,'15_excel_constructor',size);await buttonSnapshot(page,'export',size);
      await page.locator('#analysisChoices input[data-analysis="monedas"]').check();await page.locator('#analysisChoices input[data-analysis="impuestos"]').check();
      await snapshot(page,'16_excel_choices',size);
      const downloadPromise=page.waitForEvent('download');await page.locator('#exportGenerate').click();const download=await downloadPromise;
      const exported=path.join(evidence,`visual-export-${size.width}.xlsx`);await download.saveAs(exported);
      await record(`xlsx-download-${size.width}`,true,()=>Promise.resolve(fs.statSync(exported).size>0));
      await page.locator('#reportKind').selectOption('readErrors');await snapshot(page,'17_read_errors',size);
      await record(`corrupt-xml-visible-${size.width}`,true,async()=>(await page.locator('#tbody').innerText()).includes('error-deliberado.xml'));
      await page.locator('#more').click();await page.locator('#clear').click();await snapshot(page,'18_cleared',size);
      await record(`clear-disables-process-${size.width}`,false,()=>page.locator('#process').isEnabled());
      await page.locator('#file').setInputFiles(path.join(root,'tests/visual/.work/progress-synthetic.zip'));
      const clickPromise=page.locator('#process').click();
      try{await page.locator('#status').filter({hasText:/Procesados/}).waitFor({state:'visible',timeout:5000});const shot=await snapshot(page,'19_processing_progress',size);if(!/Procesados/.test(shot.before.status)||!/Procesados/.test(shot.after.status))report.blocked.push({scene:'stable_progress',size,reason:'Transient state changed during screenshot; before/after saved, not certified stable'});}catch(error){report.blocked.push({scene:'processing_progress',size,reason:String(error)})}
      await clickPromise;await page.locator('#s3').waitFor({state:'visible',timeout:30000});
      await record(`progress-completes-${size.width}`,true,()=>page.locator('#s3').isVisible());
      report.blocked.push({scene:'folder_connected_and_memory',size,reason:'Real showDirectoryPicker/native permission dialog cannot be automatically accepted in this headless baseline; no mocked folder state used. Manual Windows procedure provided.'});
      report.blocked.push({scene:'native_error_dialog',size,reason:'Native picker permission/error dialogs not manufactured; actual corrupt XML is captured in readErrors.'});
      await context.close();writeReport();
    }
  }catch(e){report.fatal=String(e);writeReport();throw e}
  finally{if(browser)await browser.close();if(hash(original)!==sourceHash)throw Error('Original changed during test');writeReport()}
  console.log(JSON.stringify({captures:report.captures.length,checks:report.checks.length,failed:report.checks.filter(x=>x.result!=='PASS'),blocked:report.blocked},null,2));
  if(args.includes('--strict') && report.checks.some(x=>x.result!=='PASS'))process.exitCode=1;
}
run().catch(e=>{console.error(e);process.exitCode=1});

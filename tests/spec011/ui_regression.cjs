/* Targeted before/after reproductions. Runs original and development separately. */
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const args=process.argv.slice(2),opt=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const modules=opt('--modules',process.env.FISCALOPS_NODE_MODULES);
const {chromium}=require(modules?path.join(modules,'playwright'):'playwright');
const base=opt('--url',JSON.parse(fs.readFileSync(path.join(root,'tests/spec011/evidence/server.json'),'utf8')).url);
const out=path.resolve(root,opt('--output','tests/spec011/targeted'));if(!out.startsWith(root+path.sep))throw Error('Evidence outside workspace');fs.mkdirSync(out,{recursive:true});
const report={before:[],after:[],console:[],export:null};
function save(){fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(report,null,2))}
async function record(list,id,expected,run){try{const actual=await run();list.push({id,expected,actual,result:JSON.stringify(expected)===JSON.stringify(actual)?'PASS':'FAIL'})}catch(error){list.push({id,expected,error:String(error),result:'ERROR'})}save()}
const files=fs.readdirSync(path.join(root,'tests/visual/fixtures/AAA010101AAA')).filter(f=>/\.(xml|txt)$/.test(f)).map(f=>path.join(root,'tests/visual/fixtures/AAA010101AAA',f));
const headers=p=>p.locator('#thead th').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('data-col')));
const checked=p=>p.locator('#checks input:checked').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('data-c')).sort());
const prefs=p=>p.evaluate(()=>JSON.stringify(Object.keys(localStorage).sort().map(key=>[key,localStorage.getItem(key)])));
async function load(page){await page.locator('#rfc').fill('AAA010101AAA');await page.locator('#file').setInputFiles(files);await page.locator('#process').click();await page.locator('#s3').waitFor({state:'visible'})}
async function variant(browser,reference){
 const list=reference?report.before:report.after;
 const context=await browser.newContext({viewport:{width:1366,height:768},deviceScaleFactor:1,acceptDownloads:true,locale:'es-MX',timezoneId:'America/Mexico_City'});
 await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 const page=await context.newPage();page.setDefaultTimeout(6000);
 page.on('pageerror',e=>report.console.push({reference,error:String(e)}));
 await page.goto(base+(reference?'/reference/':'/'));
 // Reproduce the timer race without changing the timer, clock, or app methods.
 await page.locator('#start').dispatchEvent('click');
 await page.locator('#file').setInputFiles([files[0]]);
 await page.locator('#process').dispatchEvent('click');
 await page.locator('#s3').waitFor({state:'visible'});
 const readyAt=await page.evaluate(()=>performance.now());
 await record(list,'initial-race-precondition',true,async()=>readyAt<1600);
 await page.waitForTimeout(Math.max(0,1850-readyAt));
 await record(list,'P1-E-no-late-navigation','s3',()=>page.locator('.screen.on').getAttribute('id'));
 // A new page's untouched timer must still show normal upload automatically.
 const automatic=await context.newPage();await automatic.goto(base+(reference?'/reference/':'/'));
 await automatic.locator('#s2').waitFor({state:'visible'});
 await record(list,'automatic-splash-preserved','s2',()=>automatic.locator('.screen.on').getAttribute('id'));await automatic.close();
 await page.reload();await page.locator('#s2').waitFor({state:'visible'});await load(page);
 await page.locator('[data-metodo="PUE"]').click();
 await page.locator('#typeTabs [data-type="I"]').click();
 await record(list,'P0-A-single-transition','I',()=>page.locator('#typeTabs').evaluate(n=>n.querySelector('button.on')?.dataset.type||null));
 await record(list,'other-filter-preserved','PUE',()=>page.locator('.method-seg button.on').getAttribute('data-metodo'));
 if(await page.locator('#typeTabs button.on').count())await page.locator('#typeTabs button.on').click();
 await page.locator('[data-metodo=""]').click();
 const initial=await headers(page);
 await page.locator('#editcols').click();await page.locator('#colSearch').fill('UUID');await page.locator('#applycols').click();
 await record(list,'P0-B-search-apply-keeps-selection',true,async()=>JSON.stringify((await headers(page)).slice().sort())===JSON.stringify(initial.slice().sort()));
 await page.locator('#editcolsTop').click();await page.locator('#closecols').press('Shift+Tab');
 await record(list,'P0-C-focus-contained',true,()=>page.evaluate(()=>!!document.activeElement.closest('#modal')));
 await page.keyboard.press('Escape');
 await record(list,'P0-D-invoker-restored','editcolsTop',()=>page.evaluate(()=>document.activeElement.id));
 if(reference){await context.close();return}
 // Additional regression cases use normal DOM controls, with no fiscal values asserted.
 await record(list,'apply-without-reordering',initial,()=>headers(page));
 const applied=await headers(page),saved=await prefs(page),profile=await page.locator('#profileSel').inputValue();
 await page.locator('#editcols').click();await page.locator('#colSearch').fill('CondicionesDePago');
 await page.locator('#checks input[data-c="CondicionesDePago"]').check();
 await record(list,'draft-does-not-change-applied',applied,()=>headers(page));
 await record(list,'draft-does-not-save-preferences',saved,()=>prefs(page));
 await record(list,'draft-does-not-change-profile',profile,()=>page.locator('#profileSel').inputValue());
 const count=await page.locator('#columnSelectionCount b').innerText();
 for(const query of ['UUID','RFC','NOT-A-COLUMN','']){
   await page.locator('#colSearch').fill(query);
   await record(list,'successive-search-'+(query||'empty'),count,()=>page.locator('#columnSelectionCount b').innerText());
 }
 await record(list,'clearing-search-restores-selected-option',true,()=>page.locator('#checks input[data-c="CondicionesDePago"]').isChecked());
 await page.locator('#closecols').click();
 await record(list,'cancel-keeps-applied',applied,()=>headers(page));
 await record(list,'cancel-keeps-preferences',saved,()=>prefs(page));
 await page.locator('#editcols').click();await page.locator('#colSearch').fill('CondicionesDePago');
 await record(list,'cancel-discards-uncommitted-option',false,()=>page.locator('#checks input[data-c="CondicionesDePago"]').isChecked());
 await page.locator('#checks input[data-c="CondicionesDePago"]').check();await page.locator('#colSearch').fill('UUID');await page.locator('#applycols').click();
 await record(list,'apply-keeps-hidden-new-option',true,async()=>(await headers(page)).includes('CondicionesDePago'));
 await record(list,'manual-selection-is-custom','custom',()=>page.locator('#profileSel').inputValue());
 const exportedHeaders=await page.locator('#thead th .th-label').allTextContents();
 await page.locator('#excel').click();const pending=page.waitForEvent('download');await page.locator('#exportGenerate').click();const book=await pending;const bookPath=path.join(out,'applied-columns.xlsx');await book.saveAs(bookPath);report.export={file:'applied-columns.xlsx',expectedHeaders:exportedHeaders};save();
 const custom=await headers(page);
 await record(list,'saved-profile-survives-reload',custom,async()=>{await page.reload();await page.locator('#s2').waitFor({state:'visible'});await load(page);await page.locator('#profileSel').selectOption('custom');return headers(page)});
 await page.locator('#editcolsTop').click();await page.locator('#allcols').click();await page.locator('#corecols').click();
 const recommended=await checked(page);
 await record(list,'profile-replaces-not-merges',initial.slice().sort(),async()=>recommended);
 await record(list,'profile-draft-is-not-applied','custom',()=>page.locator('#profileSel').inputValue());
 await page.locator('#invoicecols').click();await page.locator('#applycols').click();
 await record(list,'profile-applied-explicitly','fiscal',()=>page.locator('#profileSel').inputValue());
 await page.locator('#profileSel').selectOption('recommended');
 await record(list,'profile-preferences-isolated',initial,()=>headers(page));
 await page.locator('#editcols').click();await page.locator('#nocols').click();await page.locator('#colSearch').fill('UUID');await page.locator('#colSearch').fill('');
 await record(list,'empty-search-does-not-select-all',0,()=>page.locator('#checks input:checked').count());
 page.once('dialog',d=>d.dismiss());await page.locator('#applycols').click();
 await record(list,'empty-apply-does-not-commit',initial,()=>headers(page));await page.keyboard.press('Escape');
 for(const invoker of ['editcols','editcolsTop'])for(let cycle=0;cycle<3;cycle++){
   await page.locator('#'+invoker).click();
   await record(list,`initial-focus-${invoker}-${cycle}`,'colSearch',()=>page.evaluate(()=>document.activeElement.id));
   await page.locator('#applycols').press('Tab');
   await record(list,`tab-wrap-${invoker}-${cycle}`,'closecols',()=>page.evaluate(()=>document.activeElement.id));
   await page.locator('#closecols').press('Shift+Tab');
   await record(list,`shift-tab-wrap-${invoker}-${cycle}`,'applycols',()=>page.evaluate(()=>document.activeElement.id));
   await record(list,`background-inert-${invoker}-${cycle}`,true,()=>page.locator('#s3').evaluate(n=>n.inert));
   await page.keyboard.press('Escape');
   await record(list,`restore-${invoker}-${cycle}`,invoker,()=>page.evaluate(()=>document.activeElement.id));
 }
 await page.locator('#editcols').click();
 for(const size of [{width:1366,height:768},{width:1600,height:900},{width:1920,height:1080}]){
   await page.setViewportSize(size);await page.waitForTimeout(300);
   await record(list,'resize-editor-'+size.width,true,()=>page.locator('#modal .modalbox').evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight}));
   await page.screenshot({path:path.join(out,`editor-resize-${size.width}.png`)});
 }
 await page.keyboard.press('Escape');
 await context.close();
}
(async()=>{const browser=await chromium.launch({executablePath:opt('--browser'),headless:true,chromiumSandbox:true});try{await variant(browser,true);await variant(browser,false)}catch(error){report.fatal=String(error);save();throw error}finally{await browser.close();save()}console.log(JSON.stringify({before:report.before,afterChecks:report.after.length,afterFailures:report.after.filter(c=>c.result!=='PASS')},null,2));if(report.after.some(c=>c.result!=='PASS'))process.exitCode=1})().catch(e=>{console.error(e);process.exitCode=1});

const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),args=process.argv.slice(2);
const opt=(key,fallback)=>args.includes(key)?args[args.indexOf(key)+1]:fallback;
const modules=opt('--modules',process.env.FISCALOPS_NODE_MODULES);
const {chromium}=require(path.join(modules,'playwright'));
const {compareImages}=require('../../scripts/spec011/visual_tools.cjs');
const base=opt('--url',JSON.parse(fs.readFileSync(path.join(root,'tests/spec011/evidence/server.json'),'utf8')).url);
const out=path.join(root,'tests/spec011/visual');fs.mkdirSync(out,{recursive:true});
const fixtureRoot=path.join(root,'tests/visual/fixtures/AAA010101AAA');
const files=fs.readdirSync(fixtureRoot).filter(f=>/\.(xml|txt)$/.test(f)).map(f=>path.join(fixtureRoot,f));
const existingOnly=args.includes('--compare-existing-only');
const report=existingOnly?JSON.parse(fs.readFileSync(path.join(out,'comparison.json'),'utf8')):{method:'Paired actual screenshots, original vs development. Finite animations finish; infinite animations paused at time0 ONLY in QA on both pages.',pairs:[],baselineComparisons:[]};
report.baselineComparisons=[];
function save(){fs.writeFileSync(path.join(out,'comparison.json'),JSON.stringify(report,null,2))}
async function snap(page,name,variant,size){
 await page.evaluate(async()=>{await Promise.all(document.getAnimations().filter(a=>a.effect?.getComputedTiming().iterations!==Infinity).map(a=>a.finished.catch(()=>{})));document.getAnimations().filter(a=>a.effect?.getComputedTiming().iterations===Infinity).forEach(a=>{a.pause();a.currentTime=0})});
 await page.screenshot({path:path.join(out,`${name}_${variant}_${size.width}.png`)});
}
async function scenes(browser,variant,size){
 const context=await browser.newContext({viewport:size,deviceScaleFactor:1,locale:'es-MX',timezoneId:'America/Mexico_City'});
 await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 const page=await context.newPage();
 await page.goto(base+(variant==='reference'?'/reference/':'/'));
 await snap(page,'initial',variant,size);
 await page.locator('#s2').waitFor({state:'visible'});await snap(page,'upload',variant,size);
 await page.locator('#rfc').fill('AAA010101AAA');await page.locator('#file').setInputFiles(files);await page.locator('#process').click();await page.locator('#s3').waitFor({state:'visible'});
 await snap(page,'reports',variant,size);
 await page.locator('#editcols').click();await snap(page,'editor',variant,size);await page.locator('#closecols').click();
 await page.locator('#tbody tr[data-i]').first().click();await snap(page,'viewer',variant,size);await page.keyboard.press('Escape');
 await page.locator('#excel').click();await snap(page,'excel',variant,size);
 await context.close();
}
(async()=>{
 if(!existingOnly){
 const browser=await chromium.launch({executablePath:opt('--browser'),headless:true,chromiumSandbox:true});
 try{
 for(const size of [{width:1366,height:768},{width:1600,height:900},{width:1920,height:1080}]){
  await scenes(browser,'reference',size);await scenes(browser,'development',size);
  for(const scene of ['initial','upload','reports','editor','viewer','excel']){
   const diff=await compareImages(modules,path.join(out,`${scene}_reference_${size.width}.png`),path.join(out,`${scene}_development_${size.width}.png`),path.join(out,`diff_${scene}_${size.width}.png`));
   report.pairs.push({scene,viewport:size,...diff});save();
  }
 }
 }finally{await browser.close()}
 }
 // Compare ALL existing stable screenshots as well, without rewriting baseline.
 const nav=JSON.parse(fs.readFileSync(path.join(root,'tests/spec011/browser/evidence/navigation.json'),'utf8'));
 for(const capture of nav.captures.filter(c=>c.scene!=='19_processing_progress')){
  const original=path.join(root,'tests/visual/baseline',capture.file),candidate=path.join(root,'tests/spec011/browser',capture.file);
  const diff=await compareImages(modules,original,candidate,path.join(out,'baseline-diffs',capture.file));
  report.baselineComparisons.push({scene:capture.scene,viewport:capture.before.viewport,intentionalStateChange:['05_type_clicked','14_column_search_applied'].includes(capture.scene),animationsInHistoricalBaseline:'running, exact phase not recorded',...diff});
 }
 save();console.log(JSON.stringify({paired:report.pairs.length,maxPairedDifference:Math.max(...report.pairs.map(p=>p.changedPercent)),historicalComparisons:report.baselineComparisons.length},null,2));
})().catch(error=>{report.fatal=String(error);save();console.error(error);process.exitCode=1});

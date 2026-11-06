const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),args=process.argv.slice(2);
const opt=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const modules=opt('--modules',process.env.FISCALOPS_NODE_MODULES);
const {chromium}=require(modules?path.join(modules,'playwright'):'playwright');
const evidence=path.resolve(root,opt('--evidence','tests/visual/evidence'));
if(!evidence.startsWith(root+path.sep))throw Error('Evidence must remain in workspace');
fs.mkdirSync(evidence,{recursive:true});
const url=opt('--url',JSON.parse(fs.readFileSync(path.join(root,'tests/visual/evidence/server.json'),'utf8')).url);
if(new URL(url).hostname!=='127.0.0.1')throw Error('Loopback only');
const report={viewport:{width:1366,height:768},checks:[],dialogs:[],notes:['Synthetic data; navigation checks do not certify fiscal values.']};
function save(){fs.writeFileSync(path.join(evidence,'controls.json'),JSON.stringify(report,null,2))}
async function check(id,controls,expected,run){try{const actual=await run();report.checks.push({id,controls,expected,actual,result:JSON.stringify(actual)===JSON.stringify(expected)?'PASS':'FAIL'})}catch(error){report.checks.push({id,controls,expected,result:'ERROR',error:String(error)})}save()}
(async()=>{
  const browser=await chromium.launch({executablePath:opt('--browser'),headless:true,chromiumSandbox:true});
  const context=await browser.newContext({viewport:report.viewport,deviceScaleFactor:1,acceptDownloads:true,locale:'es-MX',timezoneId:'America/Mexico_City'});
  try{
    await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(url).origin?r.continue():r.abort());
    await context.tracing.start({screenshots:true,snapshots:true,sources:false});
    const page=await context.newPage();page.setDefaultTimeout(8000);
    await page.goto(url);await page.locator('#s2').waitFor({state:'visible'});
    await page.locator('#rfc').fill('AAA010101AAA');
    await check('filechooser',['select'],true,async()=>{const chosen=page.waitForEvent('filechooser');await page.locator('#select').click();const chooser=await chosen;await chooser.setFiles(fs.readdirSync(path.join(root,'tests/visual/fixtures/AAA010101AAA')).filter(f=>/\.(xml|txt)$/.test(f)).map(f=>path.join(root,'tests/visual/fixtures/AAA010101AAA',f)));return page.locator('#process').isEnabled()});
    await page.locator('#process').click();await page.locator('#s3').waitFor({state:'visible'});
    await check('next-page',['next'],'Página 2 / 2',async()=>{await page.locator('#next').click();return page.locator('#page').innerText()});
    await check('previous-page',['prev'],'Página 1 / 2',async()=>{await page.locator('#prev').click();return page.locator('#page').innerText()});
    await check('density',['densityBtn'],true,async()=>{await page.locator('#densityBtn').click();return page.locator('.tablebox').evaluate(n=>n.classList.contains('compact'))});await page.locator('#densityBtn').click();
    await check('received-origin',['origin:RECIBIDOS'],true,async()=>{await page.locator('[data-origin="RECIBIDOS"]').click();return (await page.locator('#sub').innerText()).includes('8 CFDI')});await page.locator('[data-origin="EMITIDOS"]').click();
    await check('cancelled-status',['status:CANCELADO'],true,async()=>{await page.locator('[data-status="CANCELADO"]').click();return (await page.locator('#tbody').innerText()).includes('CANCELADO')});await page.locator('[data-status=""]').click();
    await check('vigente-status',['status:VIGENTE'],false,async()=>{await page.locator('[data-status="VIGENTE"]').click();return (await page.locator('#tbody').innerText()).includes('CANCELADO')});await page.locator('[data-status=""]').click();
    for(const method of ['PUE','PPD'])await check(`method-${method}`,[`method:${method}`],method,async()=>{await page.locator(`[data-metodo="${method}"]`).click();return page.locator('.method-seg button.on').getAttribute('data-metodo')});await page.locator('[data-metodo=""]').click();
    await check('page-size',['ps'],40,async()=>{await page.locator('#ps').selectOption('50');return page.locator('#tbody tr[data-i]').count()});
    await check('year-month',['year','month'],true,async()=>{await page.locator('#year').selectOption('2026');await page.locator('#month').selectOption('10');return await page.locator('#tbody tr[data-i]').count()>0});
    await check('sort-header',['thead:Fecha'],'asc',async()=>{await page.locator('#thead th[data-col="Fecha"]').click();return page.locator('#thead th[data-col="Fecha"]').getAttribute('data-sort')});
    await check('row-enter',['tbody:Enter'],true,async()=>{await page.locator('#tbody tr[data-i]').first().press('Enter');return page.locator('#previewModal').isVisible()});
    await check('preview-close',['previewClose'],false,async()=>{await page.locator('#previewClose').click();return page.locator('#previewModal').isVisible()});
    await page.locator('#editcolsTop').click();await page.locator('#colSearch').waitFor({state:'visible'});await page.waitForTimeout(50);
    await check('column-initial-focus',['editcolsTop'],'colSearch',()=>page.evaluate(()=>document.activeElement.id));
    await check('modal-keyboard-containment',['modal:ShiftTab'],true,async()=>{await page.locator('#closecols').press('Shift+Tab');return page.evaluate(()=>!!document.activeElement.closest('#modal'))});
    for(const [id,label] of [['corecols','recommended'],['invoicecols','fiscal'],['auditcols','audit'],['taxcols','taxes'],['allcols','all']])await check(`preset-${label}`,[id],true,async()=>{await page.locator('#'+id).click();return await page.locator('#checks input:checked').count()>0});
    await check('preset-none',['nocols'],0,async()=>{await page.locator('#nocols').click();return page.locator('#checks input:checked').count()});
    page.once('dialog',async dialog=>{report.dialogs.push({type:dialog.type(),message:dialog.message(),trigger:'apply empty columns'});await dialog.dismiss();save()});
    await check('empty-columns-alert',['applycols'],true,async()=>{await page.locator('#applycols').click();return page.locator('#modal').isVisible()});
    await page.locator('#corecols').click();
    await check('columns-close',['closecols'],false,async()=>{await page.locator('#closecols').click();return page.locator('#modal').isVisible()});
    await check('columns-focus-restored',['closecols'],'editcolsTop',()=>page.evaluate(()=>document.activeElement.id));
    await page.locator('#excel').click();
    await check('export-close',['exportClose'],false,async()=>{await page.locator('#exportClose').click();return page.locator('#exportModal').isVisible()});
    await page.locator('#excel').click();await check('export-cancel',['exportCancel'],false,async()=>{await page.locator('#exportCancel').click();return page.locator('#exportModal').isVisible()});
    await page.locator('#excel').click();await check('export-escape',['Escape:export'],false,async()=>{await page.keyboard.press('Escape');return page.locator('#exportModal').isVisible()});
    for(const [id,extension] of [['csv','csv'],['txt','txt']])await check(`download-${id}`,[id],true,async()=>{const received=page.waitForEvent('download');await page.locator('#'+id).click();const download=await received;const file=path.join(evidence,'controls-export.'+extension);await download.saveAs(file);return fs.statSync(file).size>0});
    await page.screenshot({path:path.join(evidence,'controls-final.png')});
    await context.tracing.stop({path:path.join(evidence,'controls-trace.zip')});
  }catch(error){report.fatal=String(error);save();throw error}
  finally{await context.close();await browser.close();save()}
  console.log(JSON.stringify({checks:report.checks.length,failures:report.checks.filter(x=>x.result!=='PASS')},null,2));
})().catch(error=>{console.error(error);process.exitCode=1});

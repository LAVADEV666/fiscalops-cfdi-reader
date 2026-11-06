const fs=require('node:fs'),path=require('node:path');
const args=process.argv.slice(2),opt=(name,fallback)=>args.includes(name)?args[args.indexOf(name)+1]:fallback;
const modules=opt('--modules',process.env.FISCALOPS_NODE_MODULES),root=path.resolve(__dirname,'../..');
const {compareImages}=require('./visual_tools.cjs');
const out=path.join(root,'tests/spec011/qt-visual');
const data=JSON.parse(fs.readFileSync(path.join(out,'captures.json'),'utf8'));
const baselineScene={initial:'01_initial',upload:'02_upload_empty',reports:'04_reports_table',editor:'12_column_editor',viewer:'07_viewer_summary',excel:'15_excel_constructor'};
(async()=>{
 const pairs=[],crossRenderer=[];
 for(const c of data.captures.filter(c=>c.variant==='development')){
   const width=c.viewport[0],height=c.viewport[1];
   pairs.push({scene:c.scene,viewport:c.viewport,...await compareImages(modules,path.join(out,`${c.scene}_reference_${width}.png`),path.join(out,c.file),path.join(out,`diff_${c.scene}_${width}.png`))});
   crossRenderer.push({scene:c.scene,viewport:c.viewport,engines:'Frozen Chromium151 vs real Windows QtWebEngine140',...await compareImages(modules,path.join(root,'tests/visual/baseline',`${baselineScene[c.scene]}__${width}x${height}__dsf1.png`),path.join(out,c.file),path.join(out,`cross_${c.scene}_${width}.png`))});
 }
 const report={pairs,crossRenderer};fs.writeFileSync(path.join(out,'comparison.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({paired:pairs.length,maxSameQtDifference:Math.max(...pairs.map(x=>x.changedPercent)),crossRendererMax:Math.max(...crossRenderer.map(x=>x.changedPercent))},null,2));
})().catch(error=>{console.error(error);process.exitCode=1});

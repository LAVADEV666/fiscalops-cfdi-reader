/* Compare the current native report with the preceding worker milestone, never overwrite baseline. */
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const {compareImages}=require('../spec011/visual_tools.cjs');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'tests/persistence/visual');
const previous='0b19884ea75875eb7c0208d18c18d62d86d89093';
(async()=>{
 fs.mkdirSync(out,{recursive:true});const pairs=[];
 for(const width of [1366,1600,1920]){
  const height=width===1366?768:width===1600?900:1080;
  const source=`tests/integration/qt/report_${width}x${height}.png`;
  const before=path.join(out,`before_${width}.png`),after=path.join(out,`after_${width}.png`);
  fs.writeFileSync(before,cp.execFileSync('git',['show',`${previous}:${source}`],{cwd:root,maxBuffer:10*1024*1024}));
  fs.copyFileSync(path.join(root,source),after);
  pairs.push({width,height,...await compareImages(process.argv[2],before,after,path.join(out,`diff_${width}.png`))});
 }
 const smoke=JSON.parse(fs.readFileSync(path.join(root,'tests/integration/qt/smoke.json'),'utf8'));
 const result={previous_commit:previous,source_sha256:smoke.source_sha256,pairs};
 fs.writeFileSync(path.join(out,'comparison.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result.pairs,null,2));
 if(pairs.some(p=>!p.comparable||p.changedPercent>=1))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});

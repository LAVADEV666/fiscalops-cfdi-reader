const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),modules=process.argv[2]||process.env.FISCALOPS_NODE_MODULES;
const {compareImages}=require('../spec011/visual_tools.cjs');
const folder=path.join(root,'tests/integration/visual');
(async()=>{
 const captures=JSON.parse(fs.readFileSync(path.join(folder,'captures.json'),'utf8'));
 const pairs=[];
 for(const item of captures.captures.filter(c=>c.role==='after')){
  const before=captures.captures.find(c=>c.role==='before'&&c.scene===item.scene&&c.width===item.width);
  const diff=path.join(folder,`diff_${item.scene}_${item.width}.png`);
  const result=await compareImages(modules,path.join(root,before.file),path.join(root,item.file),diff);
  pairs.push({scene:item.scene,width:item.width,height:item.height,...result,diff:path.relative(root,diff).replaceAll('\\','/')});
 }
 fs.writeFileSync(path.join(folder,'comparison.json'),JSON.stringify({source_sha256:captures.source_sha256,pairs},null,2));
 console.log(JSON.stringify({pairs:pairs.length,maximumPercent:Math.max(...pairs.map(p=>p.changedPercent)),byScene:pairs.map(p=>({scene:p.scene,width:p.width,percent:p.changedPercent}))},null,2));
 if(pairs.length!==18||pairs.some(p=>!p.comparable))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1;});

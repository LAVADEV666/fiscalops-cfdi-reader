const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
async function compareImages(modules,left,right,diffPath){
 const {PNG}=require(path.join(modules,'pngjs'));
 const pixelmatch=(await import(pathToFileURL(path.join(modules,'pixelmatch/index.js')).href)).default;
 const a=PNG.sync.read(fs.readFileSync(left)),b=PNG.sync.read(fs.readFileSync(right));
 if(a.width!==b.width||a.height!==b.height)return {comparable:false,leftSize:[a.width,a.height],rightSize:[b.width,b.height]};
 const diff=new PNG({width:a.width,height:a.height});
 const changed=pixelmatch(a.data,b.data,diff.data,a.width,a.height,{threshold:0.1,includeAA:false});
 fs.mkdirSync(path.dirname(diffPath),{recursive:true});fs.writeFileSync(diffPath,PNG.sync.write(diff));
 return {comparable:true,width:a.width,height:a.height,changedPixels:changed,totalPixels:a.width*a.height,changedPercent:100*changed/(a.width*a.height),threshold:0.1,antialiasExcluded:true,diff:diffPath};
}
module.exports={compareImages};

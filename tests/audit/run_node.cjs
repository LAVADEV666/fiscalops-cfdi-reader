/* Domain diagnostics using unmodified legacy functions and test doubles.
 * UI is stubbed; XML nodes come from Python ElementTree, NOT browser DOMParser.
 * No results from this runner establish browser compatibility or fiscal compliance.
 */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const dir = path.join(__dirname, 'evidence');
const inventory = JSON.parse(fs.readFileSync(path.join(dir,'inventory.json'),'utf8'));
const source = fs.readFileSync(path.join(dir,'script-01.js'),'utf8');
const elements = new Map();
function ui() {return {value:'',innerHTML:'',textContent:'',style:{setProperty(){}},classList:{toggle(){},add(){},remove(){}},addEventListener(){},querySelectorAll(){return []},querySelector(){return null},closest(){return ui()},setAttribute(){},getAttribute(){return ''}};}
const document = {getElementById(id){if(!elements.has(id))elements.set(id,ui());return elements.get(id)},querySelectorAll(){return []},querySelector(){return null},documentElement:ui(),body:ui(),addEventListener(){}};
function adapt(data) {
  const node={...data,nodeName:data.localName,nodeType:1,attributes:Object.entries(data.attrs).map(([name,value])=>({name,localName:name,value})),children:data.children.map(adapt)};
  node.getAttribute=name=>Object.hasOwn(data.attrs,name)?data.attrs[name]:null;
  node.getElementsByTagNameNS=(namespace,name)=>node.children.flatMap(child=>[...(child.localName===name?[child]:[]),...child.getElementsByTagNameNS(namespace,name)]);
  return node;
}
class TestDOMParser {
  parseFromString(text) {
    const p=spawnSync('python',[path.join(root,'scripts/xml_audit_adapter.py')],{input:text,encoding:'utf8',windowsHide:true,maxBuffer:10*1024*1024});
    if(p.status!==0)throw Error(p.stderr);
    const data=JSON.parse(p.stdout);
    if(data.error)return {getElementsByTagName:()=>[{}]};
    const node=adapt(data.root);
    return {documentElement:node,getElementsByTagName:()=>[],getElementsByTagNameNS:(ns,name)=>[...(node.localName===name?[node]:[]),...node.getElementsByTagNameNS(ns,name)]};
  }
}
const warnings=[];
const context={document,window:{innerWidth:1366,innerHeight:768,addEventListener(){}},console:{warn(...v){warnings.push(v.map(String).join(' '))},error(){}},setTimeout(){},clearTimeout(){},TextEncoder,TextDecoder,Uint8Array,Uint32Array,DataView,Map,Set,Intl,Date,Number,JSON,DOMParser:TestDOMParser,localStorage:{getItem(){return null},setItem(){}}};
vm.createContext(context);
const marker='/* ================= END V21 PATCH ================= */';
const expose=`globalThis.audit={parseCFDI,addTaxAnalysis,nval,num,sum,sameSig,parseMeta,compareValues,v21CellXml,v21SheetXml,v21BuildXlsx,v21Zip,unzipFile,spreadsheetSafe,buildLines,fmtDate,process,renderChecks,allRows,reportOptionsForType,metaMap,detect,normalize,getiva,getret,
reset(){seen=new Set()}, versions(){return {parser:PARSER_VERSION,schema:APP_SCHEMA_VERSION,reports:Object.keys(REPORT_DEFS),columns:Object.keys(COLUMN_REGISTRY).length,domParser:parseCFDI.toString().includes('parseXmlDocument'),xlsxHandler:el('excel').onclick.name}}, column(id){return COLUMN_REGISTRY[id]}, metadata(rows){meta=rows;return metaMap().get('X')}, state(){return {readErrors,cfd,meta}}, cachedErrors(){return Object.keys(memory.files)}, declarations:parseCFDI.toString().slice(0,100)};`;
vm.runInContext(source.replace(marker,marker+'\n'+expose),context,{timeout:10000});
const a=context.audit;
const results=[];
function check(id,expected,run){const value=run();assert.deepEqual(JSON.parse(JSON.stringify(value)),expected);results.push({id,status:'REPRODUCED',value});}
const uuid='11111111-1111-4111-8111-111111111111';
const transfer='<cfdi:Traslado Base="100" Impuesto="002" TipoFactor="Tasa" TasaOCuota="0.160000" Importe="16"/>';
const global=`<cfdi:Impuestos TotalImpuestosTrasladados="16"><cfdi:Traslados>${transfer}</cfdi:Traslados></cfdi:Impuestos>`;
function xml({taxes='',local='',conceptTax='',extra='',total='116',namespace='http://www.sat.gob.mx/cfd/4',type='I'}={}){return `<cfdi:Comprobante xmlns:cfdi="${namespace}" xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" xmlns:implocal="http://www.sat.gob.mx/implocal" xmlns:pago20="http://www.sat.gob.mx/Pagos20" Version="4.0" Fecha="2026-11-06T12:34:56" TipoDeComprobante="${type}" Moneda="MXN" SubTotal="100" Total="${total}" Exportacion="01"><cfdi:Emisor Rfc="AAA010101AAA" RegimenFiscal="601"/><cfdi:Receptor Rfc="BBB010101BBB" UsoCFDI="G03" RegimenFiscalReceptor="601"/><cfdi:Conceptos><cfdi:Concepto Cantidad="1" ValorUnitario="100" Importe="100" ObjetoImp="02">${conceptTax}</cfdi:Concepto></cfdi:Conceptos>${taxes}<cfdi:Complemento><tfd:TimbreFiscalDigital UUID="${uuid}"/>${local}${extra}</cfdi:Complemento></cfdi:Comprobante>`;}
function parse(opts){a.reset();const r=a.parseCFDI(xml(opts),'AAA010101AAA');assert.equal(r.ok,true,r.error);return r.o;}
check('N01-runtime',true,()=>a.versions().domParser&&a.versions().xlsxHandler==='v21OpenExport');
check('N02-iva-ieps',{IVA:'24',ivaDetail:'16.00',IEPS:'8.00'},()=>{const o=parse({taxes:'<cfdi:Impuestos TotalImpuestosTrasladados="24"><cfdi:Traslados>'+transfer+'<cfdi:Traslado Base="100" Impuesto="003" TipoFactor="Tasa" TasaOCuota="0.080000" Importe="8"/></cfdi:Traslados></cfdi:Impuestos>',total:'124'});return {IVA:o.IVA,ivaDetail:o.IVA16,IEPS:o.IEPSTrasladado}});
check('N03-retention-label',{reported:'10',ISR:'0.00',nature:'Retención'},()=>{const o=parse({taxes:'<cfdi:Impuestos TotalImpuestosRetenidos="10"><cfdi:Retenciones><cfdi:Retencion Impuesto="001" Importe="10"/></cfdi:Retenciones></cfdi:Impuestos>',total:'90'});return {reported:o.Retenciones,ISR:o.ISRRetenido,nature:o._details.globalTaxes[0].Naturaleza}});
check('N04-local-double',-3,()=>parse({taxes:global,local:'<implocal:ImpuestosLocales TotaldeTraslados="3" TotaldeRetenciones="0"><implocal:TrasladosLocales ImpLocTrasladado="ISH" TasadeTraslado="3" Importe="3"/></implocal:ImpuestosLocales>',total:'119'}).DiferenciaCalculada);
check('N05-namespace',true,()=>a.parseCFDI(xml({namespace:'urn:not-sat'}),'').ok);
check('N06-exempt-zero',{zero:'100.00',exempt:'100.00'},()=>{const o=parse({total:'100',conceptTax:'<cfdi:Impuestos><cfdi:Traslados><cfdi:Traslado Base="100" Impuesto="002" TipoFactor="Exento"/></cfdi:Traslados></cfdi:Impuestos>'});return {zero:o.BaseTasa0,exempt:o.BaseExenta}});
check('N07-fallback-double','32',()=>parse({taxes:`<cfdi:Impuestos><cfdi:Traslados>${transfer}</cfdi:Traslados></cfdi:Impuestos>`,conceptTax:`<cfdi:Impuestos><cfdi:Traslados>${transfer}</cfdi:Traslados></cfdi:Impuestos>`}).IVA);
check('N08-decimals',{sum:0.30000000000000004,missing:0,invalid:0,rounded:'1.00'},()=>({sum:a.sum([{x:'.1'},{x:'.2'}],'x'),missing:a.nval(null),invalid:a.nval('INVALID'),rounded:(1.005).toFixed(2)}));
check('N09-signature',true,()=>a.sameSig({path:'a.xml',size:1,lastModified:1},{path:'a.xml',size:1,lastModified:1}));
check('N10-metadata-invalid','INVALID',()=>a.parseMeta('Uuid~RfcEmisor~NombreEmisor~RfcReceptor~NombreReceptor~Estatus\nINVALID~AAA~A~BBB~B~1')[0].Uuid);
check('N11-multiple-payments',{payments:2,docs:2,total:100,cfdi:'0'},()=>{const o=parse({type:'P',total:'0',extra:'<pago20:Pagos Version="2.0"><pago20:Totales MontoTotalPagos="100"/><pago20:Pago MonedaP="MXN" Monto="40"><pago20:DoctoRelacionado IdDocumento="A" ImpSaldoAnt="100" ImpPagado="40" ImpSaldoInsoluto="60"/></pago20:Pago><pago20:Pago MonedaP="MXN" Monto="60"><pago20:DoctoRelacionado IdDocumento="B" ImpSaldoAnt="60" ImpPagado="60" ImpSaldoInsoluto="0"/></pago20:Pago></pago20:Pagos>'});return {payments:o._details.payments.length,docs:o._details.paymentDocs.length,total:o.PagoMontoCalculadoMXN,cfdi:o.Total}});
check('N12-dtd',false,()=>a.parseCFDI('<!DOCTYPE a><a/>','').ok);
check('N13-date-sort',1,()=>a.compareValues({Fecha:'31/01/2026'},{Fecha:'01/02/2026'},a.column('Fecha')));
check('N14-xlsx-date-text',true,()=>a.v21CellXml('2026-11-06',0,2,{dataType:'date'}).includes('inlineStr'));
check('N15-xlsx-control',true,()=>a.v21CellXml('a\u0001b',0,2,{dataType:'text'}).includes('\u0001'));
check('N16-xlsx-limit',{start:0,end:1048575},()=>{let sliced;const fake={length:1048576,slice(start,end){sliced={start,end};return []}};a.v21SheetXml(fake,[{id:'UUID'}]);return sliced});
check('N17-formula-protection',"'=1+1",()=>a.spreadsheetSafe('=1+1'));
check('N18-txt-zero','',()=>a.buildLines([{Total:0}],['Total'])[1]);
check('N19-findings-report',false,()=>a.versions().reports.includes('findings'));
check('N20-report-type-scope',true,()=>a.reportOptionsForType('I').includes('payments'));
check('N21-metadata-conflict','CANCELADO',()=>a.metadata([{Uuid:'X',EstatusTexto:'VIGENTE'},{Uuid:'X',EstatusTexto:'CANCELADO'}]).EstatusTexto);
check('N22-time-loss','06/11/2026',()=>a.fmtDate('2026-11-06T12:34:56'));
check('N25-normalize-removes-dtd',false,()=>a.normalize('<!DOCTYPE cfdi:Comprobante>'+xml()).includes('<!DOCTYPE'));
check('N26-legacy-tax-helpers-unused',false,()=>a.parseCFDI.toString().includes('getiva(')||a.parseCFDI.toString().includes('getret('));
fs.writeFileSync(path.join(dir,'invalid-control-cell.xml'),a.v21SheetXml([{text:'a\u0001b'}],[{id:'text',label:'text',dataType:'text'}]));
const bytes=a.v21BuildXlsx([{name:'Reporte',cols:[{id:'UUID',label:'UUID',dataType:'text'},{id:'Total',label:'Total',dataType:'currency'}],rows:[{UUID:uuid,Total:'116.25'}]},{name:'Vacía',cols:[{id:'UUID',label:'UUID'}],rows:[]}]);
fs.writeFileSync(path.join(dir,'synthetic-export.xlsx'),bytes);
(async()=>{
  const zip=a.v21Zip([{name:'test.xml',data:'<x/>'}]);const v=new DataView(zip.buffer);zip[30+v.getUint16(26,true)]=33;
  const out=await a.unzipFile({arrayBuffer:async()=>zip.buffer});check('N23-zip-corrupt-crc',true,()=>out.length===1&&out[0].text==='!x/>');
  const central=zip.findIndex((b,i)=>b===0x50&&zip[i+1]===0x4b&&zip[i+2]===1&&zip[i+3]===2);v.setUint16(central+10,99,true);
  const unsupported=await a.unzipFile({arrayBuffer:async()=>zip.buffer});check('N24-zip-unsupported-silent',0,()=>unsupported.length);
  const report={method:'Node VM; UI stubbed; XML DOM adapted from Python ElementTree. No browser/visual validation.',node:process.version,prototype_sha256:inventory.sha256,versions:a.versions(),results,warnings};
  fs.writeFileSync(path.join(dir,'node-results.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify({checks:results.length,status:'All diagnostic observations reproduced',versions:report.versions,results},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});


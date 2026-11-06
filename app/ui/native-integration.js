/* Inlined inside the preserved V21 closure. Native mode has no fiscal JavaScript fallback. */
(function(){
  'use strict';
  var hasNative=typeof qt!=='undefined'&&!!qt.webChannelTransport;
  if(!hasNative&&window.FiscalOpsVisualReference===true)return; // Explicit QA server only, never the shipped HTML.
  // Install the barrier first: a later initialization error must never run the legacy parser/exporter.
  function unavailable(){setStatus('Para procesar y exportar, abre la aplicación de escritorio FiscalOps.');}
  process=unavailable;
  ['excel','excelf','csv','csvQuick','txt','exportPack','exportGenerate','cancel','sinmeta'].forEach(function(id){if(el(id))el(id).onclick=unavailable;});
  if(!hasNative){allRows=function(){return[];};nextScreen=connectFolder=reconnectFolder=refreshConnectedFolder=unavailable;window.FiscalOpsRuntime=Object.freeze({state:Object.freeze({mode:'unavailable',busy:false})});return;}
  var datasetId=null,busy=false,currentJob=null,cancelRequested=false,committing=false,epoch=0,totalFiles=0;
  var moneyCache=Object.assign(Object.create(null),{'0':'$0.00'}),totalsEpoch=0,totalsPending=false,totalsDesired=null;
  var state={mode:'decimal-worker',busy:false,dataset_id:null,documents:0,totals:'empty',last_export:null,persistence:'starting'};
  window.FiscalOpsRuntime=Object.freeze({get state(){return Object.assign({},state);},captureSession:function(){return datasetId?{dataset_id:datasetId,view:viewState()}:null;}});
  [['SHA256','SHA256 del original','text'],['MotorFiscal','Motor fiscal','text'],['ReglasFiscales','Versión de reglas','text'],['ValidacionXSD','Validación XSD local','status'],['ValidacionFirma','Validación de firma','status'],['ValidacionSATOficial','Consulta SAT oficial','status'],['TotalRecalculado','Total recalculado por detalle','currency'],['TotalRecalculadoConceptos','Total recalculado desde conceptos','currency']].forEach(function(def){if(!COLUMN_REGISTRY[def[0]])reg(cd(def[0],def[1],'Validación',def[2],['I','E','T','N','P'],['summary'],{defaultVisible:false}));});
  var eventsConnected=false;
  function connectNativeEvents(){if(eventsConnected||!window.FiscalOpsDesktop)return;eventsConnected=true;api().ready.then(function(){api().onDownload(function(status){state.download=status;setStatus(status==='saved'?'Exportación guardada.':status==='cancelled'?'Guardado cancelado.':'No se pudo guardar la exportación.');});api().onProgress(function(job,progress){if(job!==currentJob||!busy)return;state.progress=progress;setStatus('Procesados '+int(progress.processed)+' / '+int(totalFiles)+' archivos · XML: '+int(progress.documents)+' · Errores: '+int(progress.errors));});return resumeSession();});}
  window.addEventListener('fiscalops:desktop-ready',connectNativeEvents,{once:true});connectNativeEvents();
  function api(){if(!window.FiscalOpsDesktop)throw new Error('FISCAL_BRIDGE_UNAVAILABLE');return window.FiscalOpsDesktop;}
  function errorText(error){return{'DATABASE_BUSY':'La base local está ocupada. Reintenta la operación.','DATABASE_UNAVAILABLE':'No se pudo abrir o guardar la base local. Revisa el espacio y los permisos.','DATABASE_SCHEMA_NEWER':'La base local requiere una versión más reciente de FiscalOps.','DATABASE_IDENTITY_INVALID':'El archivo de datos no es una base FiscalOps compatible.','DATABASE_INTEGRITY_FAILED':'La base local no pasó la comprobación de integridad.','DOCUMENT_INTEGRITY_FAILED':'Un documento o resultado guardado no pasó la comprobación de integridad.','SESSION_ENGINE_MISMATCH':'La sesión usa otra versión del motor. Vuelve a seleccionar y procesar los originales.','SESSION_CONFLICT_REOPEN':'Otra ventana cambió la sesión activa. Reabre FiscalOps antes de guardar.','IMPORT_SESSION_BYTE_LIMIT':'La carga supera 64 MiB de documentos. Divide el lote.','IMPORT_DOCUMENT_LIMIT':'La carga supera 10.000 documentos. Divide el lote.','EXPORT_BYTE_LIMIT':'La exportación supera el límite de 64 MiB. Reduce la selección.','EXPORT_WORKSHEET_BYTE_LIMIT':'La hoja es demasiado grande. Reduce filas o columnas.','EXPORT_EXCEL_ROW_LIMIT':'La selección supera el límite de filas de Excel. Divide el reporte.','FISCAL_BRIDGE_UNAVAILABLE':'El motor nativo no está disponible. Abre la aplicación de escritorio.'}[error.message]||error.message;}
  function failLegacy(){throw new Error('LEGACY_FISCAL_DISABLED_IN_QT');}
  parseCFDI=addTaxAnalysis=unzipFile=parseMeta=nval=num=sum=getiva=getret=normalize=failLegacy;
  v21Agg=v21AnalysisSheet=v21BuildXlsx=v21CellXml=failLegacy;
  allRows=function(){return cfd;};
  money=function(value){if(value==null||value==='')return'—';return moneyCache[String(value)]||'—';};
  function decimalCompare(a,b){
    if(a==null||a==='')return b==null||b===''?0:1;if(b==null||b==='')return-1;
    var re=/^([+-]?)(\d+)(?:\.(\d+))?$/,x=String(a).match(re),y=String(b).match(re);
    if(!x||!y)return String(a).localeCompare(String(b));
    var xi=x[2].replace(/^0+(?=\d)/,''),yi=y[2].replace(/^0+(?=\d)/,''),xf=x[3]||'',yf=y[3]||'';
    var xn=x[1]==='-'&&/[1-9]/.test(xi+xf),yn=y[1]==='-'&&/[1-9]/.test(yi+yf);if(xn!==yn)return xn?-1:1;
    var result=xi.length===yi.length?(xi===yi?0:xi<yi?-1:1):xi.length<yi.length?-1:1;
    if(!result){var width=Math.max(xf.length,yf.length),xx=xf.padEnd(width,'0'),yy=yf.padEnd(width,'0');result=xx===yy?0:xx<yy?-1:1;}
    return xn?-result:result;
  }
  compareValues=function(a,b,c){if(c.dataType==='currency'||c.dataType==='number')return decimalCompare(a[c.id],b[c.id]);
    function iso(v){var s=String(v||''),m=s.match(/^(\d{2})\/(\d{2})\/(\d{4})/);return m?m[3]+'-'+m[2]+'-'+m[1]+s.slice(10):s;}
    return(c.dataType==='date'||c.dataType==='datetime')?iso(a[c.id]).localeCompare(iso(b[c.id])):String(a[c.id]||'').localeCompare(String(b[c.id]||''),'es',{numeric:true,sensitivity:'base'});};
  conceptRows=function(xml){var parent=cfd.find(function(r){return r.XMLRaw===xml;}),rows=parent&&parent._details.concepts||[];
    if(!rows.length)return'<div class="empty-v16">Sin conceptos.</div>';
    return rows.map(function(row,i){return'<details class="concept-card" '+(i===0?'open':'')+'><summary>Concepto '+(i+1)+' · '+safe(row.Descripcion||row.ClaveProdServ)+'</summary><div class="concept-grid">'+[['ClaveProdServ','ClaveProdServ'],['NoIdentificación','NoIdentificacion'],['Cantidad','Cantidad'],['Clave unidad','ClaveUnidad'],['Unidad','Unidad'],['Valor unitario','ValorUnitario'],['Importe','Importe'],['Descuento','DescuentoConcepto'],['Objeto del impuesto','ObjetoImp']].map(function(pair){return previewRow(pair[0],row[pair[1]],catalogHintFor(pair[1],row[pair[1]]));}).join('')+'</div></details>';}).join('');};
  detailTaxRows=function(r){var rows=r._details&&r._details.globalTaxes||[];if(!rows.length)return'<div class="empty-v16">Sin nodos de traslados o retenciones.</div>';
    return'<div class="tax-table-wrap"><table class="tax-table"><thead><tr><th>Naturaleza</th><th>Impuesto</th><th>Factor</th><th>Tasa/Cuota</th><th>Base</th><th>Importe</th></tr></thead><tbody>'+rows.map(function(x){return'<tr><td>'+safe(x.Naturaleza+(x.NivelImpuesto==='LOCAL'?' local':''))+'</td><td>'+safe(x.Impuesto+(x.NivelImpuesto==='LOCAL'?'':' · '+cat('Impuesto',x.Impuesto)))+'</td><td>'+safe(x.TipoFactor||'')+'</td><td>'+safe(x.TasaOCuota==null?'':x.TasaOCuota)+'</td><td class="num">'+money(x.Base)+'</td><td class="num">'+money(x.Importe)+'</td></tr>';}).join('')+'</tbody></table></div>';};
  function mergeMoney(values){Object.assign(moneyCache,values||{});}
  function scopedSummary(){var summary=filtered();return REPORT_DEFS[activeReport]&&REPORT_DEFS[activeReport].baseReport==='summary'?currentReportRows(summary):summary;}
  function paintTotals(groups,count){var html='<div class="currency-groups">';groups.forEach(function(g){html+='<div class="currency-card"><h4>'+safe(g.Moneda)+' · '+safe(cat('Moneda',g.Moneda))+' · '+int(g.CFDI)+' CFDI</h4><table><thead><tr><th>Subtotal</th><th>Descuento</th><th>IVA</th><th>Retenciones</th><th>Total CFDI</th><th>Filas reporte</th></tr></thead><tbody><tr>'+['Subtotal','Descuento','IVA','Retenciones','Total'].map(function(key){return'<td>'+money(g[key])+'</td>';}).join('')+'<td>'+int(count)+'</td></tr></tbody></table></div>';});html+='</div>';if(groups.length>1)html+='<p class="currency-warning">Los importes se separan por moneda. No se presenta una suma global entre monedas distintas sin una conversión válida.</p>';el('totalsBox').innerHTML=html;}
  async function nextTotals(){if(totalsPending||!totalsDesired)return;var request=totalsDesired;totalsDesired=null;totalsPending=true;
    try{var result=await api().call('report.aggregate',{dataset_id:request.dataset,document_ids:request.ids});if(request.sequence===totalsEpoch&&request.dataset===datasetId){mergeMoney(result.money_formats);paintTotals(result.groups,request.count);state.totals='ready';}}
    catch(error){if(request.sequence===totalsEpoch){el('totalsBox').textContent='No se pudieron calcular los importes: '+error.message;state.totals='error';}}
    finally{totalsPending=false;if(totalsDesired)nextTotals();}}
  renderTotals=function(summary,rows){var sequence=++totalsEpoch;if(!datasetId||!summary.length){totalsDesired=null;state.totals='empty';el('totalsBox').innerHTML='<div class="empty-report"><b>Sin importes para totalizar</b></div>';return;}
    var chosen=REPORT_DEFS[activeReport]&&REPORT_DEFS[activeReport].baseReport==='summary'?rows:summary;
    state.totals='pending';el('totalsBox').innerHTML='<div class="empty-report"><b>Calculando importes…</b></div>';totalsDesired={sequence:sequence,dataset:datasetId,ids:chosen.map(function(r){return r._docId;}),count:rows.length};nextTotals();};
  function setBusy(value,label){busy=value;state.busy=value;['select','folder','changeFolder','refreshFolder','process','reprocessAll','forgetMemory','more','excel','excelf','csv','csvQuick','txt','exportPack'].forEach(function(id){var button=el(id);if(button){if(value){button.dataset.nativeDisabled=button.disabled?'1':'0';button.disabled=true;}else{button.disabled=button.dataset.nativeDisabled==='1';delete button.dataset.nativeDisabled;}}});
    if(el('clear'))el('clear').textContent=value?'Cancelar':originalClearText;if(label)setStatus(label);}
  var originalClear=el('clear').onclick,originalClearText=el('clear').textContent;
  var viewTimer=null,viewPending=false,viewWanted=null,lastSavedView='',restoring=false;
  function viewState(){var filters={};['q','year','month','tipo','estatus','ps'].forEach(function(id){filters[id]=el(id).value;});
    var widths={},pinned={};Object.keys(columnState.widths||{}).forEach(function(id){if(COLUMN_REGISTRY[id])widths[id]=Math.round(columnState.widths[id]);});Object.keys(columnState.pinned||{}).forEach(function(id){if(COLUMN_REGISTRY[id])pinned[id]=!!columnState.pinned[id];});
    return{report:activeReport,type:activeType,profile:activeProfile,method:activeMetodo,origin:activeOrigen,sort:sortState,density:densityMode,columns:visibleCols.slice(),widths:widths,pinned:pinned,filters:filters,page:page};}
  function scheduleView(){if(restoring||busy||!datasetId)return;clearTimeout(viewTimer);state.view_saved=false;viewTimer=setTimeout(function(){viewWanted={id:datasetId,value:viewState()};saveView();},180);}
  async function saveView(){if(viewPending||!viewWanted)return;var request=viewWanted;viewWanted=null;var key=JSON.stringify(request);if(key===lastSavedView){state.view_saved=true;return;}viewPending=true;
    try{await api().call('session.save',{dataset_id:request.id,view:request.value});lastSavedView=key;if(request.id===datasetId)state.view_saved=true;}
    catch(error){state.view_saved=false;state.persistence_error=error.message;setStatus('No se guardó el estado de sesión: '+errorText(error));}
    finally{viewPending=false;if(viewWanted)saveView();}}
  function restoreView(value){var v=value||{};activeType=['','I','E','T','N','P'].indexOf(v.type)>=0?v.type:'';activeReport=REPORT_DEFS[v.report]?v.report:'summary';if(reportOptionsForType(activeType).indexOf(activeReport)<0)activeReport='summary';activeProfile=PROFILE_DEFS[v.profile]?v.profile:'recommended';activeMetodo=['','PUE','PPD'].indexOf(v.method)>=0?v.method:'';activeOrigen=['','EMITIDOS','RECIBIDOS','OTROS'].indexOf(v.origin)>=0?v.origin:'';
    loadColumns(true);var allowed=applicableColumns(activeReport,activeType).map(function(c){return c.id;});if(Array.isArray(v.columns)){var chosen=v.columns.filter(function(id,i,a){return allowed.indexOf(id)>=0&&a.indexOf(id)===i;});if(chosen.length)visibleCols=chosen;}
    columnState.widths={};columnState.pinned={};Object.keys(v.widths||{}).forEach(function(id){var n=v.widths[id];if(COLUMN_REGISTRY[id]&&Number.isInteger(n)&&n>=40&&n<=2000)columnState.widths[id]=n;});Object.keys(v.pinned||{}).forEach(function(id){if(COLUMN_REGISTRY[id]&&typeof v.pinned[id]==='boolean')columnState.pinned[id]=v.pinned[id];});
    if(v.sort&&COLUMN_REGISTRY[v.sort.id]&&['asc','desc'].indexOf(v.sort.dir)>=0)sortState={id:v.sort.id,dir:v.sort.dir};densityMode=v.density==='compact'?'compact':'comfortable';
    ['q','year','month','tipo','estatus','ps'].forEach(function(id){var val=(v.filters||{})[id],control=el(id);if(typeof val!=='string')return;if(id==='q'||Array.from(control.options).some(function(o){return o.value===val;}))control.value=val;});page=Number.isInteger(v.page)&&v.page>0?v.page:1;
    Array.from(document.querySelectorAll('.method-seg button')).forEach(function(b){b.classList.toggle('on',(b.getAttribute('data-metodo')||'')===activeMetodo);});Array.from(document.querySelectorAll('.origin-seg button')).forEach(function(b){b.classList.toggle('on',(b.getAttribute('data-origin')||'')===activeOrigen);});}
  function memoryPanel(){var p=el('memoryPanel');if(!p)return;p.classList.toggle('on',!!datasetId);p.innerHTML=datasetId?'<b>🧠 Sesión SQLite '+safe(empresaRFC())+'</b><span>'+int(cfd.length)+' documentos guardados · Se recupera al abrir FiscalOps. Limpiar cierra la sesión; doble clic en Borrar memoria elimina el historial local.</span>':'';if(el('forgetMemory'))el('forgetMemory').disabled=!datasetId;}
  updateMemoryPanel=memoryPanel;
  var renderNative=render;render=function(){renderNative();scheduleView();};
  document.addEventListener('change',scheduleView);document.addEventListener('input',scheduleView);
  async function resumeSession(){restoring=true;committing=true;setBusy(true,'Recuperando sesión local…');el('clear').disabled=true;state.persistence='recovering';
    try{var saved=await api().call('session.resume',{});if(saved.dataset_id){var rows=[],errors=[],formats={},offset=0;for(;;){var batch=await api().call('dataset.page',{dataset_id:saved.dataset_id,offset:offset});batch.rows.forEach(function(row){row._XMLRaw=row.XMLRaw;});rows.push.apply(rows,batch.rows);errors.push.apply(errors,batch.errors);Object.assign(formats,batch.money_formats);if(batch.done)break;offset=batch.next;}
        datasetId=saved.dataset_id;cfd=rows;readErrors=errors;meta=[];rowCache=null;rowCacheKey='';moneyCache=formats;mergeMoney({'0':'$0.00'});el('rfc').value=saved.rfc||'';state.dataset_id=datasetId;state.documents=cfd.length;setupFilters();restoreView(saved.view);render();pg(3);memoryPanel();setStatus('Sesión recuperada · '+int(cfd.length)+' documentos · '+int(readErrors.length)+' incidente(s).');}
      if(!saved.dataset_id)setStatus('Esperando archivos. Las cargas confirmadas se guardan en SQLite.');state.persistence='ready';}
    catch(error){state.persistence='error';state.persistence_error=error.message;setStatus('No se pudo recuperar la sesión: '+errorText(error));}
    finally{restoring=false;committing=false;el('clear').disabled=false;setBusy(false);scheduleView();}}
  async function clearSession(purge){if(busy)return;clearTimeout(viewTimer);viewWanted=null;var cleared=false;setBusy(true,purge?'Borrando memoria local…':'Cerrando sesión…');
    try{await api().call(purge?'session.purge':'dataset.clear',{});++epoch;datasetId=null;state.dataset_id=null;state.documents=0;readErrors=[];cleared=true;pg(2);}
    catch(error){setStatus('No se pudo limpiar: '+errorText(error));}finally{setBusy(false);if(cleared){originalClear();memoryPanel();setStatus(purge?'Memoria SQLite borrada.':'Sesión cerrada. Puedes procesar otra carga.');}}}
  if(el('forgetMemory'))el('forgetMemory').ondblclick=function(){return clearSession(true);};
  // Chromium/Qt directory input retains the browser's user selection boundary; no path-reading slot.
  var nativeFolder=document.createElement('input');nativeFolder.type='file';nativeFolder.multiple=true;nativeFolder.webkitdirectory=true;nativeFolder.hidden=true;document.body.appendChild(nativeFolder);
  nativeFolder.onchange=function(){if(busy)return;var files=Array.from(nativeFolder.files||[]).filter(function(f){return/\.(xml|zip|txt|html|htm)$/i.test(f.name);});if(!files.length)return;selected=files;var name=(files[0].webkitRelativePath||'Carpeta').split('/')[0];folderInfo={name:name,rfc:detectRFCFromFolder(name),xml:files.filter(function(f){return/\.xml$/i.test(f.name);}).length,zip:files.filter(function(f){return/\.zip$/i.test(f.name);}).length,meta:files.filter(function(f){return/\.(txt|html|htm)$/i.test(f.name);}).length,total:files.length};if(folderInfo.rfc)el('rfc').value=folderInfo.rfc;renderFileList();updateFolderPanel();el('process').disabled=false;el('reprocessAll').disabled=false;el('refreshFolder').disabled=false;setStatus('Carpeta seleccionada · '+int(files.length)+' archivos. Presiona Procesar archivos.');};
  function chooseNativeFolder(){if(busy)return;nativeFolder.value='';nativeFolder.click();}
  connectFolder=reconnectFolder=refreshConnectedFolder=chooseNativeFolder;
  ['folder','changeFolder','refreshFolder'].forEach(function(id){if(el(id))el(id).onclick=chooseNativeFolder;});
  el('clear').onclick=async function(){if(busy){if(committing)return;cancelRequested=true;if(currentJob)await api().cancel(currentJob);setStatus('Cancelando operación…');return;}
    return clearSession(false);};
  function binary(file){return new Promise(function(resolve,reject){if(file.size>32*1024*1024){reject(new Error('IMPORT_FILE_LIMIT'));return;}var reader=new FileReader();reader.onload=function(){resolve(String(reader.result).split(',',2)[1]);};reader.onerror=function(){reject(new Error('FILE_READ_FAILED'));};reader.readAsDataURL(file);});}
  process=async function(files){if(busy)return;files=Array.from(files||[]);if(!files.length)return;var token=++epoch,staged=[],errors=[],formats=Object.create(null);cancelRequested=false;totalFiles=files.length;state.progress=null;
    setBusy(true,'Preparando archivos…');el('prog').value=0;
    try{currentJob=await api().openJob('import');if(cancelRequested){await api().cancel(currentJob);throw new Error('CANCELLED');}await api().call('import.begin',{rfc:empresaRFC()},currentJob);
      for(var i=0;i<files.length;i++){if(cancelRequested)throw new Error('CANCELLED');var progress;if(files[i].size>32*1024*1024){progress=await api().call('import.reject',{name:files[i].name},currentJob);}else{var encoded=await binary(files[i]);if(cancelRequested)throw new Error('CANCELLED');progress=await api().call('import.file',{name:files[i].name,base64:encoded},currentJob);}el('prog').value=Math.round((i+1)/files.length*100);setStatus('Procesados '+int(progress.processed)+' / '+int(files.length)+' · XML: '+int(progress.documents)+' · Metadata: '+int(progress.metadata)+' · Errores: '+int(progress.errors));}
      if(cancelRequested)throw new Error('CANCELLED');var prepared=await api().call('import.prepare',{},currentJob),offset=0;
      for(;;){if(cancelRequested)throw new Error('CANCELLED');var batch=await api().call('import.page',{offset:offset},currentJob);batch.rows.forEach(function(row){row._XMLRaw=row.XMLRaw;});staged.push.apply(staged,batch.rows);errors.push.apply(errors,batch.errors);Object.assign(formats,batch.money_formats);if(batch.done)break;offset=batch.next;}
      if(cancelRequested||token!==epoch)throw new Error('CANCELLED');committing=true;el('clear').disabled=true;var committed=await api().call('import.commit',{},currentJob);
      datasetId=committed.dataset_id;cfd=staged;readErrors=errors;meta=[];rowCache=null;rowCacheKey='';memoryKey='';moneyCache=formats;mergeMoney({'0':'$0.00'});state.dataset_id=datasetId;state.documents=cfd.length;setupFilters();page=1;render();pg(3);setStatus('Proceso terminado. Reporte listo · '+int(readErrors.length)+' incidente(s) de lectura.');
    }catch(error){if(currentJob)await api().cancel(currentJob);setStatus(cancelRequested||error.message==='CANCELLED'?'Operación cancelada. Se conserva el reporte anterior.':'No se pudo procesar: '+errorText(error));}
    finally{currentJob=null;committing=false;el('clear').disabled=false;setBusy(false);memoryPanel();scheduleView();}};
  function exportContext(summary){var context={report_label:REPORT_DEFS[activeReport].label,type_label:typeLabel(activeType),currency_labels:{},form_labels:{},method_labels:{}};summary.forEach(function(r){context.currency_labels[r.Moneda]=cat('Moneda',r.Moneda);context.form_labels[r.FormaPago]=cat('FormaPago',r.FormaPago);context.method_labels[r.MetodoPago]=cat('MetodoPago',r.MetodoPago);});return context;}
  function download(file){var binary=atob(file.base64),bytes=new Uint8Array(binary.length);for(var i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);var blob=new Blob([bytes],{type:file.mime}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=file.name;document.body.appendChild(link);link.click();link.remove();setTimeout(function(){URL.revokeObjectURL(url);},1500);}
  async function exportReport(kind,analyses,report,cols){if(busy||!datasetId)return;var rp=report||activeReport,summary=scopedSummary(),rows=sortedRows(currentReportRowsFor(rp,summary));cancelRequested=false;setBusy(true,'Preparando exportación…');var button=el('exportGenerate'),text=button.textContent;button.disabled=true;button.textContent='Generando Excel…';
    try{currentJob=await api().openJob('export');if(cancelRequested){await api().cancel(currentJob);throw new Error('CANCELLED');}var result=await api().call('report.export',{dataset_id:datasetId,document_ids:summary.map(function(r){return r._docId;}),row_ids:rows.map(function(r){return r._rowId;}),report:rp,format:kind,analyses:analyses||[],columns:v21Cols(cols||exportColumns()),concept_columns:v21Cols(REPORT_DEFAULTS.concepts),rfc:empresaRFC(),context:exportContext(summary)},currentJob);
      if(!cancelRequested){state.last_export={report:rp,format:kind,rows:result.rows,sheets:result.sheets,document_ids:result.document_ids,row_ids:result.row_ids};download(result);v21CloseExport();setStatus('Exportación terminada.');}}
    catch(error){if(currentJob)await api().cancel(currentJob);setStatus(cancelRequested?'Exportación cancelada.':'No se pudo exportar: '+errorText(error));}
    finally{currentJob=null;setBusy(false);button.disabled=false;button.textContent=text;}}
  v21DownloadWorkbook=function(){var ids=v21SelectedAnalyses();try{localStorage.setItem('FiscalOpsV21ExportTabs',JSON.stringify(ids));}catch(error){}return exportReport('xlsx',ids);};
  el('excel').onclick=v21OpenExport;
  el('exportGenerate').onclick=v21DownloadWorkbook;
  el('csv').onclick=function(){return exportReport('csv');};if(el('csvQuick'))el('csvQuick').onclick=el('csv').onclick;
  el('txt').onclick=function(){return exportReport('txt');};el('excelf').onclick=function(){return exportReport('xlsx');};
  exportPackage=async function(){for(var rp of reportOptionsForType(activeType)){var summary=scopedSummary();if(currentReportRowsFor(rp,summary).length)await exportReport('xlsx',[],rp,profileColumns('export',rp,activeType));if(cancelRequested)break;}};
  if(el('exportPack'))el('exportPack').onclick=exportPackage;
  if(el('cancel'))el('cancel').onclick=function(){return exportReport('txt',[],'canceled',REPORT_DEFAULTS.canceled);};
  if(el('sinmeta'))el('sinmeta').onclick=function(){return exportReport('txt',[],'missingMetadata',REPORT_DEFAULTS.missingMetadata);};
  var closeExport=el('exportCancel').onclick;el('exportCancel').onclick=function(){if(busy){cancelRequested=true;if(currentJob)api().cancel(currentJob);}closeExport();};
  if(el('reprocessAll'))el('reprocessAll').onclick=function(){if(selected.length)return process(selected,true);nextScreen();};
})();

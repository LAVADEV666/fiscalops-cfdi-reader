/* SPEC 011: one owner for the column editor; state is committed only by Apply.
 * Inlined into the legacy closure by scripts/spec011/build_ui.py.
 * Markup/classes/text mirror the final V21 editor. No tax logic belongs here.
 */
var columnEditor = {open:false, available:[], selected:[], search:'', profile:'', invoker:null, background:[]};

function editorFocusable() {
  return Array.from(el('modal').querySelectorAll('button,input,select,textarea,a[href],[tabindex]'))
    .filter(function(node) { return !node.disabled && node.tabIndex >= 0 && node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden'; });
}
function setEditorBackgroundInert(inert) {
  if (!inert) {
    columnEditor.background.forEach(function(saved) { saved.node.inert=saved.inert; });
    columnEditor.background=[];
    return;
  }
  var branch=el('modal');
  while (branch && branch!==document.body) {
    Array.from(branch.parentElement.children).forEach(function(sibling) {
      if (sibling===branch || /^(SCRIPT|STYLE|LINK)$/.test(sibling.tagName)) return;
      columnEditor.background.push({node:sibling,inert:sibling.inert});
      sibling.inert=true;
    });
    branch=branch.parentElement;
  }
}
function containEditorFocus(event) {
  if (columnEditor.open && !el('modal').contains(event.target)) {
    (editorFocusable()[0] || el('modal')).focus();
  }
}
function openColumnEditor(invoker) {
  if (columnEditor.open) return;
  columnEditor.available=applicableColumns(activeReport,activeType).slice();
  columnEditor.selected=visibleCols.slice();
  columnEditor.search='';
  columnEditor.profile=activeProfile;
  columnEditor.invoker=invoker || document.activeElement;
  columnEditor.open=true;
  el('colSearch').value='';
  renderChecks();
  el('modal').classList.add('on');
  setEditorBackgroundInert(true);
  document.addEventListener('focusin',containEditorFocus);
  el('colSearch').focus();
}
function closeColumnEditor() {
  if (!columnEditor.open) return;
  var invoker=columnEditor.invoker;
  columnEditor.open=false;
  el('modal').classList.remove('on');
  document.removeEventListener('focusin',containEditorFocus);
  setEditorBackgroundInert(false);
  columnEditor.selected=[];
  columnEditor.available=[];
  columnEditor.search='';
  columnEditor.profile='';
  columnEditor.invoker=null;
  if (invoker && invoker.isConnected && !invoker.disabled && invoker.getClientRects().length) invoker.focus();
}
updateColumnSelectionCount=function() {
  var node=el('columnSelectionCount');
  if (!node) return;
  var columns=columnEditor.open ? columnEditor.available : applicableColumns(activeReport,activeType);
  var selected=columnEditor.open ? columnEditor.selected : visibleCols;
  node.innerHTML='<b>'+int(selected.filter(function(id){return !!COLUMN_REGISTRY[id]}).length)+'</b> columnas elegidas para el reporte final <span>· '+int(columns.length)+' campos disponibles en este tipo de reporte.</span>';
};
renderChecks=function() {
  var q=columnEditor.search.trim().toLowerCase(), rows=v21RowsForEditor(), areas={};
  columnEditor.available.forEach(function(c) {
    if(q && (c.label+' '+c.id+' '+c.group+' '+c.description).toLowerCase().indexOf(q)<0)return;
    var area=v21Area(c),key=area[0];
    if(!areas[key])areas[key]={desc:area[1],cols:[]};
    areas[key].cols.push(c);
  });
  var keys=Object.keys(areas), html='<div class="v21-editor-intro"><div><b>Diseña la hoja 1 del Excel</b><span>Activa únicamente la información que necesitas. La tabla visible se actualizará con la misma selección.</span></div><span>'+int(rows.length)+' filas en el reporte actual</span></div><div class="v21-column-quadrants">';
  keys.forEach(function(key) {
    var area=areas[key];
    html+='<section class="v21-col-quadrant"><header><h3>'+safe(key)+'</h3><p>'+safe(area.desc)+'</p></header><div class="v21-col-items">';
    area.cols.forEach(function(c) {
      var checked=columnEditor.selected.indexOf(c.id)>=0, info=v21ColumnInfo(c.id,rows);
      var availability=info.limit ? int(info.count)+' de '+int(info.limit)+(info.total>info.limit?' muestras':' filas') : 'sin filas cargadas';
      var sample=info.sample?' · Ejemplo: '+v21Short(info.sample,46):'';
      html+='<label class="v21-column-card '+(checked?'selected':'')+'"><input class="column-visible-check" type="checkbox" data-c="'+safe(c.id)+'" '+(checked?'checked':'')+'><span><b>'+safe(c.label)+'</b><span class="v21-col-desc">'+safe(c.description||c.label)+'</span><small><strong>En el Excel:</strong> '+safe(c.label)+' · Datos: '+safe(availability)+safe(sample)+'</small></span></label>';
    });
    html+='</div></section>';
  });
  html+='</div>';
  if(!keys.length)html='<div class="empty-report"><b>No se encontraron columnas</b>Prueba otra palabra de búsqueda.</div>';
  el('checks').innerHTML=html;
  Array.from(el('checks').querySelectorAll('input[data-c]')).forEach(function(check) {
    check.onchange=function() {
      var id=check.getAttribute('data-c');
      if(check.checked){if(columnEditor.selected.indexOf(id)<0)columnEditor.selected.push(id);}
      else columnEditor.selected=columnEditor.selected.filter(function(value){return value!==id});
      columnEditor.profile='custom';
      check.closest('.v21-column-card').classList.toggle('selected',check.checked);
      updateColumnSelectionCount();
    };
  });
  updateColumnSelectionCount();
};
var v21Preset=function(profile) {
  columnEditor.profile=profile;
  var allowed=columnEditor.available.map(function(c){return c.id});
  columnEditor.selected=profileColumns(profile,activeReport,activeType).filter(function(id){return allowed.indexOf(id)>=0});
  renderChecks();
};
applyColumnEditor=function() {
  if (!columnEditor.open) return;
  var allowed=columnEditor.available.map(function(c){return c.id});
  var selected=columnEditor.selected.filter(function(id,index,array){return allowed.indexOf(id)>=0 && array.indexOf(id)===index});
  if (!selected.length) { alert('Selecciona al menos una columna para construir el reporte.'); return; }
  visibleCols=selected;
  activeProfile=columnEditor.profile;
  saveColumns();
  closeColumnEditor();
  refreshReportSelectors();
  render();
};
['editcols','editcolsTop'].forEach(function(id){el(id).onclick=function(event){openColumnEditor(event.currentTarget)};});
el('colSearch').oninput=function(){columnEditor.search=this.value;renderChecks();};
el('closecols').onclick=closeColumnEditor;
el('modal').onclick=function(event){if(event.target===el('modal'))closeColumnEditor();};
el('modal').addEventListener('keydown',function(event) {
  if (!columnEditor.open) return;
  if (event.key==='Escape') { event.preventDefault(); event.stopPropagation(); closeColumnEditor(); return; }
  if (event.key!=='Tab') return;
  var nodes=editorFocusable(),first=nodes[0],last=nodes[nodes.length-1];
  if (!first) { event.preventDefault(); return; }
  if (event.shiftKey && document.activeElement===first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement===last) { event.preventDefault(); first.focus(); }
});
[['corecols','recommended'],['invoicecols','fiscal'],['auditcols','audit'],['taxcols','taxes']].forEach(function(pair){el(pair[0]).onclick=function(){v21Preset(pair[1])};});
el('allcols').onclick=function(){columnEditor.selected=columnEditor.available.map(function(c){return c.id});columnEditor.profile='custom';renderChecks();};
el('nocols').onclick=function(){columnEditor.selected=[];columnEditor.profile='custom';renderChecks();};
el('applycols').onclick=applyColumnEditor;

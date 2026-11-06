/* Correlated asynchronous transport; fiscal data remains decimal strings. */
(function(){
  'use strict';
  if (typeof qt==='undefined' || !qt.webChannelTransport || typeof QWebChannel==='undefined') return;
  var nativeObject,fiscalObject,pending=new Map(),listeners=new Set(),downloadListeners=new Set(),serial=0;
  var ready=new Promise(function(resolve,reject){
    new QWebChannel(qt.webChannelTransport,function(channel){
      nativeObject=channel.objects.desktop;
      fiscalObject=channel.objects.fiscal;
      if (!nativeObject) { reject(new Error('Missing desktop diagnostics object')); return; }
      if(fiscalObject){
        fiscalObject.response.connect(function(json){var reply=JSON.parse(json),request=pending.get(reply.request_id);if(!request)return;pending.delete(reply.request_id);clearTimeout(request.timer);if(reply.ok)request.resolve(reply.result);else request.reject(Object.assign(new Error(reply.code),{code:reply.code}));});
        fiscalObject.progress.connect(function(job,json){var value=JSON.parse(json);listeners.forEach(function(fn){fn(job,value);});});
        fiscalObject.downloadStatus.connect(function(status){downloadListeners.forEach(function(fn){fn(status);});});
      }
      nativeObject.describe(function(json){resolve(JSON.parse(json));});
    });
  });
  window.FiscalOpsDesktop=Object.freeze({
    ready:ready,
    openJob:function(kind){return ready.then(function(){if(!fiscalObject)throw new Error('FISCAL_BRIDGE_UNAVAILABLE');return new Promise(function(resolve,reject){fiscalObject.openJob(kind,function(json){var reply=JSON.parse(json);if(reply.ok)resolve(reply.job_id);else reject(new Error(reply.code));});});});},
    call:function(operation,payload,job){return ready.then(function(){if(!fiscalObject)throw new Error('FISCAL_BRIDGE_UNAVAILABLE');return new Promise(function(resolve,reject){var id='request-'+(++serial),timer=setTimeout(function(){pending.delete(id);reject(new Error('FISCAL_REQUEST_TIMEOUT'));},180000);pending.set(id,{resolve:resolve,reject:reject,timer:timer});fiscalObject.request(id,job||'',operation,JSON.stringify(payload||{}),function(json){var ack=JSON.parse(json);if(!ack.ok){var item=pending.get(id);if(item){pending.delete(id);clearTimeout(item.timer);item.reject(new Error(ack.code));}}});});});},
    cancel:function(job){return ready.then(function(){return new Promise(function(resolve){fiscalObject.cancel(job,function(json){resolve(JSON.parse(json));});});});},
    onProgress:function(fn){listeners.add(fn);return function(){listeners.delete(fn);};},
    onDownload:function(fn){downloadListeners.add(fn);return function(){downloadListeners.delete(fn);};},
    ping:function(requestId){
      return ready.then(function(){return new Promise(function(resolve){
        nativeObject.ping(String(requestId).slice(0,128),function(json){resolve(JSON.parse(json));});
      });});
    }
  });
  window.dispatchEvent(new Event('fiscalops:desktop-ready'));
})();

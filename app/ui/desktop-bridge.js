/* Native diagnostics only. Browser file/fiscal flows stay unchanged. */
(function(){
  'use strict';
  if (typeof qt==='undefined' || !qt.webChannelTransport || typeof QWebChannel==='undefined') return;
  var nativeObject;
  var ready=new Promise(function(resolve,reject){
    new QWebChannel(qt.webChannelTransport,function(channel){
      nativeObject=channel.objects.desktop;
      if (!nativeObject) { reject(new Error('Missing desktop diagnostics object')); return; }
      nativeObject.describe(function(json){resolve(JSON.parse(json));});
    });
  });
  window.FiscalOpsDesktop=Object.freeze({
    ready:ready,
    ping:function(requestId){
      return ready.then(function(){return new Promise(function(resolve){
        nativeObject.ping(String(requestId).slice(0,128),function(json){resolve(JSON.parse(json));});
      });});
    }
  });
})();

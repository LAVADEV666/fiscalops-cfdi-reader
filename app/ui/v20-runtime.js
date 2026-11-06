
(function(){'use strict';
 function applyV20Scale(){var w=window.innerWidth||1366,h=window.innerHeight||768,ratio=Math.min(w/1366,h/768),scale=Math.max(.94,Math.min(1.16,ratio));document.documentElement.style.setProperty('--v20-scale',scale.toFixed(3));document.body.classList.toggle('v20-short',h<700);}
 applyV20Scale();window.addEventListener('resize',applyV20Scale,{passive:true});
 var reportLabel=document.querySelector('.pro-field span');if(reportLabel&&reportLabel.textContent.trim()==='Reporte normalizado')reportLabel.textContent='Tipo de reporte';
})();

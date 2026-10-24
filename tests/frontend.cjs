const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {parseHTML}=require('linkedom');
const source=fs.readFileSync('assets/telemetry.js','utf8').replace('  refresh();\n','  globalThis.testing={refresh,refreshHistory,validate,render};\n  refresh();\n');
const stamp=new Date().toISOString();
const snapshot={connected:true,updatedAt:stamp,source:'Test fixture',host:{cpuPercent:2,memoryPercent:30,diskPercent:5,uptimeSeconds:90000,networkBytesPerSecond:1024},website:{healthy:true,responseMs:3},dockerServiceActive:true,
containerMonitor:{connected:true,updatedAt:stamp,containers:[{name:'pardo-web',running:true,state:'running',health:'healthy',restartCount:0,startedAt:stamp}]},github:{connected:true,updatedAt:stamp,runs:[{id:123,number:1,status:'completed',conclusion:'success',branch:'main',commit:'a'.repeat(40),createdAt:stamp}]}};
const history={samples:[{timestamp:Math.floor(Date.now()/1000),cpuPercent:2,memoryPercent:30,diskPercent:5,websiteHealthy:true}]};
(async()=>{
 for(const route of ['index.html','infrastructure/index.html','journal/index.html']){
  const {document}=parseHTML(fs.readFileSync('website/'+route,'utf8'));
  const context={document,Date,AbortSignal,console,setInterval:()=>0,fetch:async url=>({ok:true,json:async()=>structuredClone(url.includes('history.json')?history:snapshot)})};
  vm.createContext(context);vm.runInContext(source,context);await context.testing.refresh();await context.testing.refreshHistory();
  if(route==='index.html'){
   assert.match(document.querySelector('.statusbar').textContent,/Telemetry connected/);
   assert.throws(()=>context.testing.validate({...snapshot,updatedAt:new Date(Date.now()-60000).toISOString()}),/Stale/);
  }else if(route.startsWith('infrastructure')){
   assert.match(document.querySelector('#container-live').textContent,/healthy/);
   assert.ok(document.querySelector('#telemetry-history svg path'));
   document.querySelectorAll('#ranges button')[2].onclick();assert.match(document.querySelector('#range-label').textContent,/7 DAYS/);
   context.fetch=async()=>{throw Error('offline')};await context.testing.refresh();assert.match(document.querySelector('#container-live').textContent,/unavailable/);
  }else{
   const region=document.querySelector('#deployment-empty').parentElement;assert.equal(region.querySelectorAll('a').length,1);
   document.querySelectorAll('#deployment-filters button')[2].onclick();assert.match(region.textContent,/No matching/);
   document.querySelectorAll('#deployment-filters button')[0].onclick();
   const malicious=structuredClone(snapshot);malicious.github.runs[0].branch='<img src=x onerror=alert(1)>';context.testing.render(malicious);assert.equal(region.querySelectorAll('img').length,0);
  }
  console.log('PASS',route);
 }
})().catch(error=>{console.error(error);process.exitCode=1});

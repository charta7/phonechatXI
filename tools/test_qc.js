const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(require('path').join(__dirname, '../bridge/index.html'),'utf8');
function extract(a,b) { return html.slice(html.indexOf(a), html.indexOf(b,html.indexOf(a))); }
let c = {lsMotd:{ls1:'A'.repeat(80)+' old'}}; vm.createContext(c);
vm.runInContext(extract('function motdKey(', 'function renderMotd('),c);
const old = c.motdKey('ls1'); c.lsMotd.ls1='A'.repeat(80)+' NEW';
assert.notEqual(old,c.motdKey('ls1')); console.log('PASS: changed MOTD gets a different dismissal key');
let resolve;
c={sending:false, compTarget:()=>({ch:'ls1'}), sjisLen:s=>s.length,lineRoom:()=>127,
 api:()=>new Promise(r=>resolve=r),pend:{},pendOrder:[],nowSec:()=>123,myName:()=> 'Tester',seenCount:{},schedule:()=>{},Event:class{},toast:console.log};
vm.createContext(c); vm.runInContext(extract('function submit(', 'document.addEventListener("click", function (e) {\n  var r ='),c);
const inp={value:'first message',dispatchEvent:()=>{}}; c.submit('chat',inp); inp.value='next draft'; resolve({ok:true,parts:[{pid:'123',text:'first message'}]});
setImmediate(()=>{assert.equal(inp.value,'next draft'); console.log('PASS: pending send preserves edited draft');});
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1]; new vm.Script(script); console.log('PASS: inline JavaScript syntax');
let v={};vm.createContext(v); vm.runInContext(extract('var VNM_LEN =', 'function renderAlerts('),v);
const zones=[{zone:'Meriphataud Mountains',grid:'H-11'},{zone:'Valkurm Dunes',grid:'E-8'}];
const first={zones,ts:1000,teaser:'Something is interrupting ventures in these zones...'};
const warning={zones,ts:1308,teaser:"Whatever’s stirring is about to reveal itself..."};
let events=v.vnmBuild([first,warning]);assert.equal(events.length,1);assert.equal(events[0].start,1000);
events=v.vnmBuild([warning]);assert.equal(events[0].start,1000);
events=v.vnmBuild([first,{...first,zones:[{zone:'Qufim Island',grid:'F-7'}],ts:1010},warning]);assert.equal(events.length,2);
console.log('PASS: VNM warning preserves countdown, missed start backdates, concurrent zone pairs stay separate');

let h={lsMotd:{},lsName:{},byId:{},msgs:[],pend:{},S:{},lastCmdAt:0,isMention:()=>false,schedule:()=>{}};
vm.createContext(h);vm.runInContext(extract('function onMsg(', 'function onAck('),h);
h.onMsg({id:1,ch:'venture',name:'Populox',ts:1000,body:'Hmm... Something really dangerous has appeared at (I-7) in Qufim Island...'});
h.onMsg({id:2,ch:'venture',name:'Populox',ts:1308,body:'Hmm... The danger at (I-7) in Qufim Island is about to reveal itself...'});
assert.equal(h.msgs[0].zones[0].zone,'Qufim Island');assert.equal(h.msgs[1].zones[0].zone,'Qufim Island');
const hv=v.vnmBuild(h.msgs);assert.equal(hv.length,1);assert.equal(hv[0].start,1000);assert.equal(hv[0].tier,'HVNM');
assert.equal(v.vnmBuild([first,{...first,tier:'HVNM'}]).length,2);
console.log('PASS: screenshot HVNM first/warning share timer; tiers remain separate');

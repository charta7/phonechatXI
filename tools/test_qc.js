const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(require('path').join(__dirname, '../bridge/index.html'),'utf8');
function extract(a,b) { return html.slice(html.indexOf(a), html.indexOf(b,html.indexOf(a))); }
let c = {lsMotd:{ls1:'A'.repeat(80)+' old'}}; vm.createContext(c);
vm.runInContext(extract('function motdKey(', 'function renderMotd('),c);
const old = c.motdKey('ls1'); c.lsMotd.ls1='A'.repeat(80)+' NEW';
assert.notEqual(old,c.motdKey('ls1')); console.log('PASS: changed MOTD gets a different dismissal key');
let resolve;
c={sending:false, compTarget:()=>({ch:'ls1'}), sjisLen:s=>s.length,lineRoom:()=>127,
 api:()=>new Promise(r=>resolve=r),$:()=>null,leaveWindow:()=>{},NO_ANSWER:'x',pend:{},pendOrder:[],nowSec:()=>123,myName:()=> 'Tester',seenCount:{},schedule:()=>{},Event:class{},toast:console.log};
vm.createContext(c); vm.runInContext(extract("var drafts =", "function buildComposers("),c); vm.runInContext(extract('function submit(', '// Retry keeps the failed line'),c);
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

let d={};vm.createContext(d);vm.runInContext(extract('var drafts =','function buildComposers('),d);
let box={value:'',dispatchEvent:()=>{}};
d.syncDraft(box,'thread',{ch:'tell',peer:'Alice'});box.value='For Alice';d.stashDraft(box);
d.syncDraft(box,'thread',{ch:'tell',peer:'Bob'});assert.equal(box.value,'');box.value='For Bob';
d.syncDraft(box,'thread',{ch:'tell',peer:'Alice'});assert.equal(box.value,'For Alice');
d.finishDraft(box,'thread:tell:bob','For Bob');assert.equal(box.value,'For Alice');
d.syncDraft(box,'thread',{ch:'tell',peer:'Bob'});assert.equal(box.value,'');
console.log('PASS: recipient-specific drafts restore and successful sends clear only their draft');
vm.runInContext(extract('function readableColor(', 'function bodyHtml('),d);
assert.notEqual(d.readableColor('#000000'),'#000000');assert.equal(d.readableColor('#ffffff'),'#ffffff');
console.log('PASS: dark message colors lighten; white is preserved');

// Retry: the failed line stays until the bridge accepts the new send, and comes back as failed if it doesn't.
(async()=>{
  let answer; const mk=()=>{const r={pend:{},pendOrder:[],nowSec:()=>1,myName:()=>'T',schedule:()=>{},toast:()=>{},NO_ANSWER:'x',api:()=>answer()};vm.createContext(r);
    vm.runInContext(extract('function retrySend(', 'document.addEventListener("click", function (e) {\n  var r ='),r);
    r.pend.p1={pid:'p1',pending:true,ch:'ls1',peer:'',body:'hi',state:'failed',reason:'Not in a linkshell',retry:{target:'ls1',peer:'',text:'hi'}};return r;};
  let r=mk(); answer=()=>Promise.reject(new Error('down')); r.retrySend('p1'); assert.equal(r.pend.p1.state,'sending');
  await new Promise(s=>setImmediate(s)); assert.equal(r.pend.p1.state,'failed'); assert.equal(r.pend.p1.reason,'Not in a linkshell');
  r=mk(); answer=()=>Promise.resolve({ok:false,error:'Paused'}); r.retrySend('p1'); await new Promise(s=>setImmediate(s));
  assert.equal(r.pend.p1.state,'failed'); assert.equal(r.pend.p1.reason,'Paused');
  r=mk(); answer=()=>Promise.resolve({ok:true,parts:[{pid:'p2',text:'hi'}]}); r.retrySend('p1'); r.retrySend('p1'); await new Promise(s=>setImmediate(s));
  assert.equal(r.pend.p1,undefined); assert.equal(r.pend.p2.state,'sending'); assert.equal(r.pendOrder.length,1);
  console.log('PASS: Retry keeps the line until the bridge accepts it, restores it on failure, ignores a double tap');
})();

// Search: every channel at once, newest first, hidden channels left out, capped; and the pane window around a hit.
{
  const f={CHAT_CH:['ls1','ls2','party','tell','say'],S:{master:{ls1:true,ls2:false,party:true,tell:true,say:true}},esc:s=>String(s).replace(/</g,'&lt;')};
  vm.createContext(f); vm.runInContext(extract('function findHits(', 'function findWho('),f);
  const L=[{id:1,ch:'ls1',name:'Wren',dir:'in',body:'anyone seen a Kraken Club?'},{id:2,ch:'system',body:'kraken'},{id:3,ch:'ls2',name:'A',dir:'in',body:'kraken'},
    {id:4,ch:'tell',name:'Kraken',dir:'out',body:'hello'},{id:5,ch:'party',name:'Me',dir:'out',body:'no match'},{id:6,ch:'party',name:'Bo',dir:'in',body:'KRAKEN pls'}];
  let r=f.findHits(' kraken ',L,10); assert.deepEqual(r.hits.map(h=>h.m.id),[6,4,1]); assert.equal(r.hits[0].at,0); assert.equal(r.hits[1].at,-1); assert.equal(r.more,false);
  assert.equal(f.findHits('k',L,10).hits.length,0);
  r=f.findHits('kraken',L,2); assert.equal(r.hits.length,2); assert.equal(r.more,true);
  assert.equal(f.findHits('me',L,10).hits.length,0);   // your own name on your own lines doesn't count
  assert.equal(f.findSnippet('a <b> kraken',6,6),'a &lt;b> <mark class="fh">kraken</mark>');
  console.log('PASS: search finds across channels newest first, skips hidden channels and system lines, caps results, escapes snippets');
  const w={}; vm.createContext(w); vm.runInContext(extract('function paneWindow(', 'function leaveWindow('),w);
  const items=[...Array(1000)].map((_,i)=>({id:i+1})).concat([{pid:'p'}]);
  let win=w.paneWindow(items,500,350); assert.equal(win.length,350); assert.ok(win.some(x=>x.id===500)); assert.equal(win[0].id,325);
  win=w.paneWindow(items,3,350); assert.equal(win[0].id,1); assert.equal(win.length,350);
  win=w.paneWindow(items,'999',350); assert.equal(win[win.length-1].pid,'p');
  assert.equal(w.paneWindow(items,5000,350),null);
  console.log('PASS: jump window holds the picked line, clamps at both ends, gives up when the line is gone');
}

// Compact layout: a line in the same minute as the one above it hides its time; a new minute or a divider shows it again.
{
  const r={CH:{ls1:{icon:'ls1',c:'x'}},S:{},esc:s=>String(s),hhmm:ts=>'T'+ts,ico:()=>'',compactPrefix:()=>'',bodyHtml:m=>m.body,stateHtml:()=>'',failHtml:()=>'',replyAttr:()=>'',lineAttr:()=>'',runHead:()=>''};
  vm.createContext(r); vm.runInContext(extract('function renderBlocks(', 'var seenCount = {};'),r);
  const run=ts=>({type:'run',ch:'ls1',dir:'in',ms:[{ch:'ls1',ts,body:'b'}]});
  const out=r.renderBlocks([run(600),run(630),run(659),run(660),{type:'div',text:'x'},run(661)],'compact');
  const cls=[...out.matchAll(/<span class="(t(?: rep)?)">/g)].map(m=>m[1]);
  assert.deepEqual(cls,['t','t rep','t rep','t','t']);
  console.log('PASS: compact layout shows the time once per minute and again after a divider');
}

// Update note: shown once per new build on a phone that already had settings; never on a new phone or with storage blocked.
{
  const u={}; vm.createContext(u); vm.runInContext(extract('function seenBuild(', 'function ackBuild('),u);
  const mk=v=>{const d={pcxi_build:v};return {getItem:k=>k in d&&d[k]!==undefined?d[k]:null,setItem:(k,x)=>{d[k]=x},d};};
  let st=mk(undefined); assert.equal(u.seenBuild('b2',true,st),false); assert.equal(st.d.pcxi_build,'b2');
  st=mk(undefined); assert.equal(u.seenBuild('b2',false,st),true); assert.equal(st.d.pcxi_build,undefined);
  assert.equal(u.seenBuild('b2',false,mk('b1')),true); assert.equal(u.seenBuild('b2',false,mk('b2')),false);
  assert.equal(u.seenBuild('b2',false,{getItem(){throw new Error('blocked')}}),false);
  console.log('PASS: update note shows once per new build, not on a new phone or when storage is blocked');
}
// Settings from 1.1.0 load into this page with nothing lost, and new options get their defaults.
{
  const s={localStorage:{getItem:()=>null},CHAT_CH:['ls1','ls2','party','tell','say','shout','unity','yell','emote','finder'],SENDABLE:['ls1','ls2','party','tell','say','shout'],MAX_VIEWS:5};
  vm.createContext(s); vm.runInContext(extract('var DEFAULTS =', 'var saveTimer ='),s);
  const old={density:'compact',size:'L',calls:'badge',clock:'24',skin:'onyx',font:'classic',view:'v1',
    views:[{id:'all',name:'All',ch:{ls1:true,ls2:true,party:true,tell:true}},{id:'v1',name:'Mine',ch:{ls1:true}}],
    master:{ls1:true,ls2:false,party:true,tell:true,say:false,shout:false},colors:{ls1:'#123456'},favs:['!mog'],watch:'Charta',savedAt:5};
  const m=s.merged(JSON.parse(JSON.stringify(old)));
  for (const k of ['density','size','calls','clock','skin','font','view','watch','savedAt']) assert.equal(m[k],old[k],k);
  assert.equal(m.views.length,2); assert.equal(m.views[1].name,'Mine'); assert.equal(m.master.ls2,false); assert.equal(m.colors.ls1,'#123456'); assert.deepEqual(Array.from(m.favs),['!mog']);
  for (const k of Object.keys(s.DEFAULTS)) assert.notEqual(m[k],undefined,'default for '+k);
  assert.equal(m.master.finder,s.DEFAULTS.master.finder);
  const fresh=s.merged(null); assert.equal(fresh.skin,'classic');
  console.log('PASS: 1.1.0-era settings load with nothing lost; options added since get their defaults');
}

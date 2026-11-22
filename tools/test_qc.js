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
  const r={CH:{ls1:{icon:'ls1',c:'x'}},S:{},esc:s=>String(s),hhmm:ts=>'T'+ts,ico:()=>'',rowIco:()=>'',compactPrefix:()=>'',bodyHtml:m=>m.body,stateHtml:()=>'',failHtml:()=>'',replyAttr:()=>'',lineAttr:()=>'',runHead:()=>''};
  vm.createContext(r); vm.runInContext(extract('function renderBlocks(', 'var seenCount = {};'),r);
  const run=ts=>({type:'run',ch:'ls1',dir:'in',ms:[{ch:'ls1',ts,body:'b'}]});
  const out=r.renderBlocks([run(600),run(630),run(659),run(660),{type:'div',text:'x'},run(661)],'compact');
  const cls=[...out.matchAll(/<span class="(t(?: rep)?)">/g)].map(m=>m[1]);
  assert.deepEqual(cls,['t','t rep','t rep','t','t']);
  console.log('PASS: compact layout shows the time once per minute and again after a divider');
}
// Linkshell marks: [1] / [2] in compact, the pixel pearl in comfortable, other channels keep their icon.
{
  const r={CH:{party:{icon:'party'},ls2:{icon:'ls2'}},ico:n=>'ICO:'+n};
  vm.createContext(r); vm.runInContext(extract('function rowIco(', 'function ico('),r);
  assert.equal(r.rowIco('ls1',13,true),'<span class="lstag">[1]</span>');
  assert.equal(r.rowIco('ls2',13,true),'<span class="lstag">[2]</span>');
  assert.equal(r.rowIco('ls2',14,false),'ICO:ls2');
  assert.equal(r.rowIco('party',13,true),'ICO:party');
  console.log('PASS: linkshell marks are [1]/[2] in compact and the linkpearl in comfortable');
}
// Hidden Alerts cards: the key ignores the bridge's message number, which starts over when the bridge restarts.
{
  const r={}; vm.createContext(r); vm.runInContext(extract('function noticeKey(', '// A linkshell with no MOTD'),r);
  assert.equal(r.noticeKey({id:5,ts:100,body:'Your Ridill has sold.'}), r.noticeKey({id:9,ts:100,body:'Your Ridill has sold.'}));
  assert.notEqual(r.noticeKey({id:5,ts:100,body:'Your Ridill has sold.'}), r.noticeKey({id:5,ts:200,body:'Your Fire Crystal has sold.'}));
  console.log('PASS: hidden Alerts cards stay matched to the same message across bridge restarts');
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
  assert.equal(m.views.length,2); assert.equal(m.views[1].name,'Mine'); assert.equal(m.master.ls2,true); assert.equal(m.views[0].ch.ls2,false); assert.equal(m.views[0].ch.say,false); assert.equal(m.views[1].ch.ls2,false); assert.equal(m.colors.ls1,'#123456'); assert.deepEqual(Array.from(m.favs),['!mog']);
  for (const k of Object.keys(s.DEFAULTS)) assert.notEqual(m[k],undefined,'default for '+k);
  assert.equal(m.master.finder,s.DEFAULTS.master.finder);
  const fresh=s.merged(null); assert.equal(fresh.skin,'classic'); assert.equal(fresh.quickFilters,false); assert.equal(fresh.views[0].ch.yell,true); assert.equal(fresh.master.yell,true);
  console.log('PASS: 1.1.0-era settings load with nothing lost; options added since get their defaults');
}
// Looks per skin: older settings become changes to the skin you had on; other skins ship as they are;
// switching skins brings back each skin's own changes; reset drops them.
{
  const s={localStorage:{getItem:()=>null},CHAT_CH:['ls1','ls2','party','tell','say','shout','unity','yell','emote','finder'],SENDABLE:['ls1','ls2','party','tell','say','shout'],MAX_VIEWS:5};
  vm.createContext(s); vm.runInContext(extract('var DEFAULTS =', 'var saveTimer ='),s);
  const m=s.merged({skin:'onyx',density:'compact',font:'classic',colors:{ls1:'#123456'},channelText:false});
  assert.deepEqual(m.looks,{onyx:{font:'classic',density:'compact',colors:{ls1:'#123456'}}});
  assert.equal(m.density,'compact'); assert.equal(m.colors.ls1,'#123456');
  m.skin='game'; s.lookLoad(m); assert.equal(m.density,'compact'); assert.equal(m.times,'inline'); assert.equal(m.channelText,true); assert.deepEqual(m.colors,{});
  m.channelText=false; s.lookSave(m); assert.deepEqual(m.looks.game,{channelText:false});
  m.skin='classic'; s.lookLoad(m); assert.equal(m.density,'comfortable'); assert.equal(m.font,'readable');
  m.skin='onyx'; s.lookLoad(m); assert.equal(m.font,'classic'); assert.equal(m.colors.ls1,'#123456');
  delete m.looks.onyx; s.lookLoad(m); assert.equal(m.font,'readable'); assert.deepEqual(m.colors,{});
  const again=s.merged(JSON.parse(JSON.stringify(m))); assert.deepEqual(again.looks,{game:{channelText:false}}); assert.equal(again.skin,'onyx');
  const gc=s.merged({skin:'game',looks:{game:{density:'comfortable'}}}); assert.deepEqual(gc.looks,{}); assert.equal(gc.density,'compact');
  const g=s.merged({skin:'game',size:'L'}); assert.deepEqual(g.looks,{}); assert.equal(g.density,'compact'); assert.equal(g.size,'L');
  assert.deepEqual(s.merged({skin:'classic',looks:{classic:{times:'dividers'}}}).looks,{classic:{times:'inline'}});
  const bad=s.merged({skin:'game',looks:{game:{names:'x',times:'off',colors:{ls1:'red'}},nope:{font:'classic'}}}); assert.deepEqual(bad.looks,{game:{times:'off'}});
  console.log('PASS: each skin keeps only its own changes, older settings carry over, reset goes back to how it shipped');
}

// "New" line: above the first message from someone else after you last looked, only with older chat above it.
{
  const r={CHAT_CH:['ls1','tell'],dayLabel:()=>'D',senderOf:m=>m.name,isCallOnly:()=>false,S:{calls:'off'}};
  vm.createContext(r); vm.runInContext(extract('function isNewFor(', 'function runHead('),r);
  const L=[{id:1,ts:100,ch:'ls1',name:'A',dir:'in'},{id:2,ts:200,ch:'ls1',name:'Me',dir:'out'},{id:3,ts:300,ch:'ls1',name:'B',dir:'in'},{id:4,ts:310,ch:'ls1',name:'B',dir:'in'}];
  const kinds=b=>b.map(x=>x.cls||x.type);
  assert.deepEqual(kinds(r.blocks(L,'chat',150)),['div','run','run','newdiv','run']);   // own line after the mark isn't "new"
  assert.deepEqual(kinds(r.blocks(L,'chat',0)),['div','run','run','run']);
  assert.deepEqual(kinds(r.blocks(L,'chat',50)),['div','run','run','run']);              // everything new: no line at the very top
  assert.deepEqual(kinds(r.blocks(L,'chat',400)),['div','run','run','run']);
  console.log('PASS: New line sits above the first unread message from someone else, not at the top or after your own lines');
}
// Search chips: counts cover every match; picking a channel narrows the list.
{
  const f={CHAT_CH:['ls1','party','tell'],S:{master:{ls1:true,party:true,tell:true}}};
  vm.createContext(f); vm.runInContext(extract('function findHits(', 'function findSnippet('),f);
  const L=[{id:1,ch:'ls1',name:'A',dir:'in',body:'kraken'},{id:2,ch:'party',name:'B',dir:'in',body:'kraken'},{id:3,ch:'party',name:'C',dir:'in',body:'Kraken'}];
  let r=f.findHits('kraken',L,1,'party'); assert.equal(r.counts.ls1,1); assert.equal(r.counts.party,2); assert.deepEqual(r.hits.map(h=>h.m.id),[3]); assert.equal(r.more,true);
  r=f.findHits('kraken',L,10,''); assert.equal(r.hits.length,3);
  console.log('PASS: search channel chips count every match and narrow the list');
}

// Long-press menu items: each {{Item}} once, at most 3, and plain text without the braces.
{
  const r={S:{wikiAll:false}}; vm.createContext(r); vm.runInContext(extract('function lineItems(', 'function copyText('),r);
  assert.deepEqual(Array.from(r.lineItems('WTB {{Kraken Club}} and {{kraken club}} or {{Ridill}} {{A}} {{B}}')),['Kraken Club','Ridill','A']);
  assert.deepEqual(Array.from(r.lineItems('{Savage Blade} at {Port Windurst}? {{Ridill}}')),['Ridill']);   // off: items only
  r.S.wikiAll=true;
  assert.deepEqual(Array.from(r.lineItems('{Savage Blade} at {Port Windurst}? {{Ridill}} {Popotato}')),['Savage Blade','Port Windurst','Ridill']);
  assert.deepEqual(Array.from(r.lineItems('{Thank you.} {thank you.}')),['Thank you.']);
  r.S.wikiAll=false;
  assert.equal(r.plainBody('WTB {{Kraken Club}} {Pull}'),'WTB Kraken Club {Pull}');
  console.log('PASS: long-press menu lists each item once (max 3) and copies text without {{ }}');
}

// Links for the long-press menu: http(s) and www. only, trailing punctuation trimmed, no logins in the address, max 3.
{
  const r={URL}; vm.createContext(r); vm.runInContext(extract('function lineLinks(', 'function askOpenLink('),r);
  const L=r.lineLinks('see https://www.bg-wiki.com/ffxi/Kraken_Club. or www.catseyexi.com/db, and https://user:pw@evil.example/x javascript:alert(1) ftp://x.org http://localhost:8080 https://a.io https://b.io https://c.io');
  assert.deepEqual(L.map(l=>l.host),['bg-wiki.com','catseyexi.com','a.io']);
  assert.equal(L[0].href,'https://www.bg-wiki.com/ffxi/Kraken_Club');
  assert.equal(L[1].href,'https://www.catseyexi.com/db');
  assert.equal(r.lineLinks('nothing here {{Ridill}}').length,0);
  assert.equal(r.lineLinks('https://xn--ctseyexi-6ya.com/login')[0].host,'xn--ctseyexi-6ya.com');   // look-alike names show in their raw form
  console.log('PASS: chat links: http(s)/www only, punctuation trimmed, no logins, no localhost, max 3, raw host shown');
}

// The whole page script must parse (a stray quote in a string breaks everything).
{
  const code=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
  new vm.Script(code);
  console.log('PASS: page script parses');
}

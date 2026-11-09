import sys, tempfile, pathlib, importlib.util, json, ast
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('replay',ROOT/'tools/replay.py'); replay=importlib.util.module_from_spec(spec);spec.loader.exec_module(replay)
from lupa.lua51 import LuaRuntime
with tempfile.TemporaryDirectory(prefix='phonechat-qc-') as tmp:
    path=pathlib.Path(tmp); (path/'dir.txt').write_text(tmp+'/')
    lua=LuaRuntime(unpack_returned_tuples=True); g=lua.globals()
    g.SAY=lambda s:None;g.MKDIR=lambda p:pathlib.Path(p.replace('\\','/')).mkdir(parents=True,exist_ok=True)
    g.EXISTS=lambda p:pathlib.Path(p.replace('\\','/')).exists();g.ADDON_DIR=tmp+'/';g.CHAR_NAME='Tester'
    lua.execute(replay.FAKE_ASHITA)
    # Lua 5.1 fallback in the supplied replay lacks LuaJIT's bit global; emulate this one operation.
    g.BAND=lambda a,b:int(a)&int(b);lua.execute('bit={band=BAND}')
    lua.execute((ROOT/'addon/phonechat/phonechat.lua').read_bytes());g.EVENTS['load']()
    def line(mode,text):g.EVENTS['text_in'](lua.table_from(dict(mode=mode,message=text,injected=False,blocked=False)))
    line(205,'[1]< TestShell: set by Tester >')
    line(205,'An unrelated server announcement')
    line(205,'Raid tonight (2026, Nov. 9 12:00:00)')
    feed=(path/'feed-Tester.log').read_text();assert '\tls1\tRaid tonight' in feed
    assert '\tserver\tin\t\tRaid tonight' not in feed
    print('PASS: interleaved server notice preserves pending MOTD')
    line(205,'[1]< TestShell: set by Tester >')
    line(205,'Raid tonight (2026, Nov. 9 12:00:00)')
    assert '\tls1\tRaid tonight' in (path/'feed-Tester.log').read_text()
    print('PASS: consecutive MOTD header/body parsed')
    line(123,'You can only place a single item or a set of 12 such items on auction.')
    line(123,'There are no party members.')
    feed=(path/'feed-Tester.log').read_text();assert 'single item' not in feed and 'no party members' in feed
    print('PASS: system failure allowlist')
for file in ROOT.rglob('*.py'):ast.parse(file.read_text())
print('PASS: Python syntax')
spec=importlib.util.spec_from_file_location('bridge',ROOT/'bridge/bridge.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
with tempfile.TemporaryDirectory(prefix='phonechat-bridge-qc-') as folder:
    sender=bridge.Sender(folder);sender.char='Tester'
    parts=sender.chat('party','','hello');item=sender.queue.popleft();sender.write(item)
    assert (pathlib.Path(folder)/'outbox-Tester.log').read_text().endswith('/p hello\n')
    assert sender.match_echo('party','Tester','hello')==parts[0]['pid']
    assert sender.match_failure('There are no party members.') is True
    assert sender.pending[parts[0]['pid']]['state']=='failed'
    assert sender.match_failure('Unrelated message') is False
    print('PASS: bridge queues a single send, matches echo, and changes sent to failed on party error')

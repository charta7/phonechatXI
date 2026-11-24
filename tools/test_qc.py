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
    line(121,"Your 'Bird feather' has sold to Charta for 7000 gil!")   # the real line, captured Nov 22
    line(121,'You buy the 12 bird feathers for 7,000 gil.')            # your own purchase: not a sale
    line(121,'Some other notice from the server.')
    line(205,'The event has sold out.')                                 # "has sold" alone isn't a sale
    feed=(path/'feed-Tester.log').read_text()
    assert "\tsale\tin\t\tYour 'Bird feather' has sold to Charta for 7000 gil!" in feed
    assert 'You buy the 12' not in feed and 'Some other notice' not in feed
    assert '\tsale\tin\t\tThe event has sold out.' not in feed and '\tserver\tin\t\tThe event has sold out.' in feed   # stays a server notice
    line(14,'[1]<Marlow> my bow has sold out lol')
    assert '\tsale\t' not in (path/'feed-Tester.log').read_text().split('my bow')[0].split('\n')[-1]
    assert '\tls1\tin\tMarlow\tmy bow has sold out lol' in (path/'feed-Tester.log').read_text() or 'my bow has sold out lol' in (path/'feed-Tester.log').read_text()
    print('PASS: AH sales from notice modes go to sale; other notices and chat are untouched')
    line(121,'\u2192 A new Summit of the Stars perk is now active: Reraise')
    feed=(path/'feed-Tester.log').read_text(encoding='utf-8',errors='replace')
    assert '\tserver\tin\t\t' in feed and 'Summit of the Stars perk is now active: Reraise' in feed.split('\tserver\tin\t\t')[-1]
    line(121,'Quixy of Fun has selected a new universal bonus.')
    line(121,'Active Bonus: Synth. H.Q. Rate\u2191')
    feed=(path/'feed-Tester.log').read_text(encoding='utf-8',errors='replace')
    assert '\tserver\tin\t\tQuixy of Fun has selected a new universal bonus.' in feed
    assert '\tserver\tin\t\tActive Bonus: Synth. H.Q. Rate' in feed
    print('PASS: Summit of the Stars perks go to server notices')
    # Auto-translate: each block keeps its own type even when a block before it can't be parsed.
    lua.execute(r'''
      local q = AshitaCore:GetChatManager().QueueCommand
      AshitaCore.GetChatManager = function() return {
        ParseAutoTranslate = function(self, s, b)
          local n = ({['\7RID'] = 'Ridill', ['\2HEL'] = 'Hello!'})[s:sub(2, -2)]
          if n then return '\239\39' .. n .. '\239(' end
          return s
        end, QueueCommand = q } end''')
    line(14, b'[1]<Marlow> \xfd\x02BAD\xfd then \xfd\x07RID\xfd')
    line(14, b'[1]<Quenby> \xfd\x02HEL\xfd and \xfd\x07RID\xfd')
    feed=(path/'feed-Tester.log').read_bytes()
    assert b'[auto-translate] then {{Ridill}}' in feed, feed[-200:]
    assert b'{Hello!} and {{Ridill}}' in feed, feed[-200:]
    print('PASS: auto-translate items stay items after an unparsed block')
    # The addon's own ! command list must match the bridge's commands.json exactly.
    cj=json.loads((ROOT/'bridge/commands.json').read_text())
    bridge_cmds=set(cj['info'])|set(cj['action'])
    import re as _re
    src=(ROOT/'addon/phonechat/phonechat.lua').read_text(encoding='latin-1')
    blk=_re.search(r"local SERVER = \{\}\s*for c in \(\[\[(.*?)\]\]\)", src, _re.S)
    assert blk, 'SERVER list not found in phonechat.lua'
    lua_cmds=set(blk.group(1).split())
    assert lua_cmds==bridge_cmds, (sorted(bridge_cmds-lua_cmds), sorted(lua_cmds-bridge_cmds))
    print('PASS: addon and bridge allow exactly the same ! commands')
    # Every ! command needs the phone's confirmation, info commands included; emotes don't.
    bspec=importlib.util.spec_from_file_location('bridge_mod',ROOT/'bridge/bridge.py'); bm=importlib.util.module_from_spec(bspec); bspec.loader.exec_module(bm)
    cmds=bm.Commands(str(ROOT/'bridge/commands.json'))
    for name in ('!bond','!moolix'):
        try: cmds.check(name, False); raise AssertionError(name+' sent without confirmation')
        except bm.SendError as e: assert str(e)=='needs_confirm', e
        assert cmds.check(name, True)[0]=='/say '+name
    assert cmds.check('/wave', False)[0]=='/wave'
    print('PASS: every ! command asks first, typed or tapped; emotes send directly')
    before = (path/'feed-Tester.log').read_bytes()
    for mode in (20, 21, 22, 23, 30, 999):
        line(mode, 'Tester hits the Goblin for 50 points of damage.')
    line(123, 'You cannot perform that action.')
    line(9, 'Unrelated game status')
    g.EVENTS['text_in'](lua.table_from(dict(mode=14, message='[1]<Tester> injected test', injected=True, blocked=False)))
    assert (path/'feed-Tester.log').read_bytes() == before
    print('PASS: combat, unknown modes, unrelated system status and injected chat stay excluded')
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

with tempfile.TemporaryDirectory(prefix='phonechat-prefs-qc-') as folder:
    f=pathlib.Path(folder)
    assert bridge.keep_previous_prefs(folder,'b1') is False and (f/'phone-settings.build').read_text()=='b1'   # nothing saved yet: no copy
    bridge.save_prefs(folder,{'skin':'onyx','watch':'Name','views':[]})
    assert bridge.keep_previous_prefs(folder,'b1') is False and not (f/bridge.PREFS_PREVIOUS).exists()          # same build: no copy
    assert bridge.keep_previous_prefs(folder,'b2') is True
    bridge.save_prefs(folder,{'skin':'yuna','views':[]})
    assert bridge.keep_previous_prefs(folder,'b2') is False                                                    # once per update
    prev=bridge.load_prefs(folder,bridge.PREFS_PREVIOUS)
    assert prev['skin']=='onyx' and 'watch' not in prev and bridge.load_prefs(folder)['skin']=='yuna'
    assert bridge.keep_previous_prefs(folder,'unknown') is False
    print('PASS: bridge keeps one copy of the phone settings per update, without names, and leaves the current ones alone')

# The same file loaded as a native VanaCore addon: no AshitaCore, no ashita, only vana.*.
FAKE_VANA = r'''
FAKE_CLOCK = 0
os.clock = function() return FAKE_CLOCK end
os.execute = function(c) return false end
io.popen = nil
addon = {}
print = function(s) SAY(tostring(s)) end
EVENTS, RUN, PARSED = {}, {}, {}
vana = {
  paths = { addon = ADDON_DIR, install = ADDON_DIR },
  fs = { exists = function(p) return EXISTS(p) end, create_dir = function(p) MKDIR(p) return true end },
  events = { on = function(name, fn, key) EVENTS[name] = fn end },
  chat = { run = function(line, mode) RUN[#RUN + 1] = tostring(mode) .. ' ' .. line end },
  game = { party = function() return { members = { { name = CHAR_NAME } } } end },
  ashita = { parse_auto_translate = function(s, brackets)
    PARSED[#PARSED + 1] = tostring(brackets)
    if s:sub(2, -2) == '\7RID' then return '\239\39Ridill\239(' end
    return s end },
}
local real_open = io.open
io.open = function(p, m) return real_open((p:gsub('\\', '/')), m) end
'''
with tempfile.TemporaryDirectory(prefix='phonechat-vana-qc-') as tmp:
    path=pathlib.Path(tmp); (path/'dir.txt').write_text(tmp+'/')
    said=[]
    lua=LuaRuntime(unpack_returned_tuples=True); g=lua.globals()
    g.SAY=said.append;g.MKDIR=lambda p:pathlib.Path(p.replace('\\','/')).mkdir(parents=True,exist_ok=True)
    g.EXISTS=lambda p:pathlib.Path(p.replace('\\','/')).exists();g.ADDON_DIR=tmp+'/';g.CHAR_NAME='Tester'
    g.BAND=lambda a,b:int(a)&int(b);lua.execute('bit={band=BAND}')
    lua.execute(FAKE_VANA)
    lua.execute((ROOT/'addon/phonechat/phonechat.lua').read_bytes())
    ev=set(g.EVENTS.keys())
    assert ev=={'load','text_in','packet_in','present','command'}, sorted(ev)   # d3d_present is VanaCore's present
    g.EVENTS['load']()
    g.EVENTS['text_in'](lua.table_from(dict(mode=14,message=b'[1]<Marlow> got \xfd\x07RID\xfd',injected=False,blocked=False)))
    feed=(path/'feed-Tester.log').read_bytes()
    assert b'\tls1\tin\tMarlow\tgot {{Ridill}}' in feed, feed[-200:]
    assert list(g.PARSED.values())==['true'], list(g.PARSED.values())          # brackets on, as under Ashita
    e=lua.table_from(dict(command='/pchat url',blocked=False))
    assert g.EVENTS['command'](e) is True and e['blocked'] is True               # handled either way VanaCore reads it
    e=lua.table_from(dict(command='/echo hi',blocked=False))
    assert g.EVENTS['command'](e) is None and e['blocked'] is False              # other commands left alone
    assert any('[phonechat]' in s for s in said), said
    # A line from the phone goes out through vana.chat.run as typed (mode 1).
    import time as _t
    lua.execute('FAKE_CLOCK=1'); g.EVENTS['present']()                            # opens the outbox (nothing old is typed)
    (path/'outbox-Tester.log').write_text('id1\t%d\t/l hello\n'%int(_t.time()))
    for i in range(2,40):
        lua.execute('FAKE_CLOCK=%d'%i); g.EVENTS['present']()
    assert '1 /l hello' in list(g.RUN.values()), list(g.RUN.values())
    print('PASS: native VanaCore: same file loads on vana.* only, reads chat, types the phone\'s lines, handles /pchat')

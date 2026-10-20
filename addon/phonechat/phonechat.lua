--[[
    phonechat v1.1.0 (phonechatXI)

    Mirrors chat to a feed file that the phonechatXI bridge serves to your phone,
    and types the replies you send from the phone, one line at a time.

    What it will type (anything else is dropped, even if the bridge asks):
        /l  /l2  /p  /s  /sh  /t Name   followed by your message
        /say !command [simple arguments]     CatsEye server commands (only those in commands.json)
        /wave, /bow ... [motion|text]       stock emotes (and /sitchair 1-4, /jobemote job)
    It never types anything on its own: no auto replies, triggers, timers or repeats.
    Each line comes from one tap on the phone.

    Commands (/pchat, /pcxi and /phonechat all work):
        /pchat            status, phone link and the list of options
        /pchat            the phonechatXI window: start/stop, QR code, settings
        /pchat qr         the same window
        /pchat start      start the bridge
        /pchat stop       stop the bridge
        /pchat url        print the phone link
        /pchat newlink    make a new phone link (the old one stops working)
        /pchat debug      toggle debug logging (every chat line with its mode number)

    Shared folder (feed, outbox, bridge, settings):
        dir.txt next to this file if present, else on Steam Deck / Linux <home>/phonechat/,
        else <Ashita>\config\addons\phonechat\
    The addon carries the bridge in its bridge\ folder and copies it into the shared folder
    when that copy is missing or older (your link in bridge\config.json is kept).

    Feed line: time <TAB> channel <TAB> in|out <TAB> name <TAB> body   (line breaks as 0x0B)
    Outbox line: id <TAB> unix time <TAB> command
]]

addon.name    = 'phonechat'
addon.author  = 'Charta'
addon.version = '1.1.0'
addon.desc    = 'phonechatXI: mirrors chat to your phone and types the replies you send from it.'
addon.link    = ''

require('common')
local chat = require('chat')
local has_imgui, imgui = pcall(require, 'imgui')

local PENDING_MAX   = 300   -- lines kept while we wait to learn the character name
local STATUS_FRESH  = 10    -- seconds; bridge heartbeat older than this = OFF
local CHECK_EVERY   = 5     -- seconds between bridge status checks
local PANEL_CHECK   = 1     -- seconds between status checks while the window is open
local OUTBOX_EVERY  = 0.5   -- seconds between outbox reads
local SEND_GAP      = 1.0   -- seconds between lines typed into the game
local STALE_SECONDS = 15    -- outbox lines older than this are dropped, never typed late
local SENDQ_MAX     = 8
local START_WAIT    = 20    -- seconds to wait for a started bridge before calling it a failure
local DEBUG_MAX     = 2 * 1024 * 1024

local S = {
    dir     = nil,
    name    = nil,
    path    = nil,
    ready   = false,
    pending = {},
    debug   = false,
    debug_bytes = 0,
    bridge  = nil,
    url     = nil,
    bver    = nil,
    next_check = 0,
    next_name  = 0,
    next_out   = 0,
    next_send  = 0,
    out_off    = nil,      -- read position in the outbox (nil = not opened yet)
    sendq      = {},
    errors  = 0,
    lines   = 0,
    sent    = 0,
    dropped = 0,
    hinted  = false,
    show_config = { false },
    cfg = { autostart = false, showlink = false, qrseen = false },
    link_shown = false,
    starting_at = nil,     -- os.time() when we asked the bridge to start
    start_error = nil,
    newlink_armed = 0,
    qr = nil, qr_url = nil, qr_broken = false,
}

-- Chat modes (low byte of e.mode) -> channel, direction. This list is an allowlist:
-- anything not here is ignored. Combat and battle modes are not here and must never be added.
local MODES = {
    [4]   = { 'tell',   'out' },
    [12]  = { 'tell',   'in'  },
    [5]   = { 'party',  'out' },
    [13]  = { 'party',  'in'  },
    [6]   = { 'ls1',    'out' },
    [14]  = { 'ls1',    'in'  },
    [213] = { 'ls2',    'out' },
    [214] = { 'ls2',    'in'  },
    [211] = { 'unity',  'out' },
    [212] = { 'unity',  'in'  },
    [10]  = { 'shout',  'in'  },
    [11]  = { 'yell',   'in'  },
    [7]   = { 'emote',  'in'  },
    [208] = { 'emote',  'in'  },   -- "X examines you."
    [123] = { 'system', 'in'  },
    [200] = { 'server', 'in'  },
    [205] = { 'server', 'in'  },
}

-- Plain system-message modes that can carry Party Finder ads and bazaar
-- visits. Combat modes are never on this list.
local NOTICE_MODES = { [9] = true, [121] = true, [127] = true, [131] = true, [142] = true }

----------------------------------------------------------------------------------------------------
-- Helpers
----------------------------------------------------------------------------------------------------

local function note(text)
    print(chat.header(addon.name):append(chat.message(text)))
end

local function read_file(path)
    local f = io.open(path, 'rb')
    if f == nil then return nil end
    local s = f:read('*a')
    f:close()
    return s
end

local function write_file(path, data)
    local f = io.open(path, 'wb')
    if f == nil then return false end
    f:write(data)
    f:close()
    return true
end

local function exists(path)
    local f = io.open(path, 'rb')
    if f then f:close() return true end
    return false
end

local function dir_exists(path)
    local ok, res = pcall(function () return ashita.fs.exists(path) end)
    if ok then return res == true end
    return false
end

local function mkdir(path)
    pcall(function () ashita.fs.create_dir(path) end)
end

local function with_sep(p)
    p = tostring(p or '')
    if p ~= '' and not p:match('[\\/]$') then p = p .. '\\' end
    return p
end

-- Z:\home\deck\phonechat\ -> /home/deck/phonechat/   (nil when it isn't a Z: path)
local function unix_path(win)
    local p = tostring(win or ''):match('^[Zz]:(\\.*)$')
    if not p then return nil end
    return (p:gsub('\\', '/'))
end

-- Shared folder: dir.txt next to the addon, else <home>/phonechat on Linux (Wine), else
-- <Ashita>\config\addons\phonechat\ on Windows.
local function resolve_dir()
    local here = ''
    pcall(function () here = with_sep(addon.path) end)
    local txt = here ~= '' and read_file(here .. 'dir.txt') or nil
    if txt then
        txt = txt:gsub('^\239\187\191', ''):match('^%s*(.-)%s*$')
        if txt ~= '' then return with_sep(txt) end
    end
    -- Under Wine/Proton the Unix HOME is passed through; Windows never has a /-style HOME.
    local home = os.getenv('HOME')
    if home and home:sub(1, 1) == '/' then
        local zhome = 'Z:' .. home:gsub('/', '\\')
        if dir_exists(zhome) then return with_sep(zhome) .. 'phonechat\\' end
    end
    if dir_exists('Z:\\home\\deck') then return 'Z:\\home\\deck\\phonechat\\' end
    local install = ''
    pcall(function () install = with_sep(AshitaCore:GetInstallPath()) end)
    return install .. 'config\\addons\\phonechat\\'
end

local function on_linux()
    return unix_path(S.dir) ~= nil
end

-- Escape control bytes so they are visible in the debug log (0x80-0x9F too, for item IDs).
local function esc(s)
    return (tostring(s or ''):gsub('[%z\1-\31\127-\159\253]', function (c)
        return ('\\x%02X'):format(c:byte())
    end))
end

-- Turn a raw chat line into clean text. Output stays in Shift-JIS; the bridge converts it.
-- Auto-translate: items (type 0x07) come out as {{Name}}, phrases and zones as {Phrase},
-- so the phone can link items only.
local function clean(s)
    s = tostring(s or '')
    local types = {}
    for inner in s:gmatch('\253(.-)\253') do types[#types + 1] = inner:byte(1) end
    local ok, res = pcall(function ()
        return AshitaCore:GetChatManager():ParseAutoTranslate(s, true)
    end)
    if ok and type(res) == 'string' then
        s = res
    end
    s = (s:gsub('\253(.-)\253', function (inner)
        local t = inner:byte(1)
        if t == 2 then return '[auto-translate]' end
        if t == 7 then return '[item]' end
        return '[?]'
    end))
    s = (s:gsub('[\r\n]+$', ''))
    s = (s:gsub('[\30\31\127].', ''))
    local k = 0
    s = (s:gsub('\239\39(.-)\239%(', function (x)
        k = k + 1
        if types[k] == 7 then return '{{' .. x .. '}}' end
        return '{' .. x .. '}'
    end))
    s = (s:gsub('\239\39', '{'))
    s = (s:gsub('\239%(', '}'))
    s = (s:gsub('\7', '\n'))
    s = (s:gsub('[\1-\9\11-\31]', ''))
    s = (s:gsub('^%s+', ''):gsub('%s+$', ''))
    return s
end

local function field(s)
    s = tostring(s or '')
    s = s:gsub('\t', ' ')
    s = s:gsub('\r', '')
    s = s:gsub('\n', '\11')
    return s
end

local function append_file(path, line)
    local f = io.open(path, 'ab')
    if f == nil then
        S.errors = S.errors + 1
        return false
    end
    f:write(line)
    f:close()
    return true
end

local function emit(channel, dir, name, body)
    local line = table.concat({
        tostring(os.time()), channel, dir, field(name), field(body),
    }, '\t') .. '\n'
    S.lines = S.lines + 1
    if S.ready then
        append_file(S.path, line)
    else
        S.pending[#S.pending + 1] = line
        if #S.pending > PENDING_MAX then
            table.remove(S.pending, 1)
        end
    end
end

local function file_size(path)
    local f = io.open(path, 'rb')
    if f == nil then return 0 end
    local n = f:seek('end') or 0
    f:close()
    return n
end

local function debug_log(raw_mode, mode, message, injected)
    if not S.debug then return end
    local path = S.dir .. 'debug-' .. (S.name or 'unknown') .. '.log'
    if S.debug_for ~= path then
        -- Count what's already in the file (from earlier sessions) toward the 2 MB cap.
        S.debug_for = path
        S.debug_bytes = file_size(path)
    end
    -- Never write the phone link token: our own "Phone link: ...?t=..." lines come back here.
    local text = (tostring(message or ''):gsub('([?&]t=)[%w_%-]+', '%1(removed)'))
    local line = ('%s\t%d\t%d\t%s%s\n'):format(os.date('%H:%M:%S'), raw_mode, mode,
        injected and '[addon] ' or '', esc(text))
    if S.debug_bytes + #line > DEBUG_MAX then
        write_file(path, '')          -- start over instead of growing forever
        S.debug_bytes = 0
    end
    S.debug_bytes = S.debug_bytes + #line
    append_file(path, line)
end

----------------------------------------------------------------------------------------------------
-- Settings (stored in the shared folder so launcher updates can't wipe them)
----------------------------------------------------------------------------------------------------

local function cfg_path() return S.dir .. 'addon-settings.txt' end

local function load_cfg()
    local s = read_file(cfg_path())
    if not s then return end
    for k, v in s:gmatch('(%w+)%s*=%s*(%w+)') do
        if S.cfg[k] ~= nil then S.cfg[k] = (v == 'true') end
    end
end

local function save_cfg()
    mkdir(S.dir)
    local f = io.open(cfg_path(), 'wb')
    if f == nil then return end
    for k, v in pairs(S.cfg) do f:write(k .. '=' .. tostring(v) .. '\n') end
    f:close()
end

----------------------------------------------------------------------------------------------------
-- Character name and feed file
----------------------------------------------------------------------------------------------------

local function set_name(n)
    n = tostring(n or ''):gsub('[^%w_%-]', '')
    if n == '' or n == S.name then return end

    S.name = n
    S.path = S.dir .. 'feed-' .. n .. '.log'
    S.out_off = nil
    S.sendq = {}
    mkdir(S.dir)

    -- Fresh feed each time this character's addon starts (the bridge notices the truncation).
    local f = io.open(S.path, 'wb')
    if f == nil then
        S.errors = S.errors + 1
        S.ready = false
        return
    end
    f:close()
    S.ready = true

    for _, line in ipairs(S.pending) do
        append_file(S.path, line)
    end
    S.pending = {}
end

local function resolve_name()
    local ok, n = pcall(function ()
        return AshitaCore:GetMemoryManager():GetParty():GetMemberName(0)
    end)
    if ok and type(n) == 'string' and n ~= '' and n ~= '?' then
        set_name(n)
    end
end

----------------------------------------------------------------------------------------------------
-- Bridge: install, status, start, stop
----------------------------------------------------------------------------------------------------

local function bridge_version(folder)
    local s = read_file(folder .. 'bridge.py')
    return s and s:match('\nVERSION = "([^"]+)"') or nil
end

local function vtuple(v)
    local t = {}
    for n in tostring(v or '0'):gmatch('%d+') do t[#t + 1] = tonumber(n) end
    return t
end

local function newer(a, b)   -- is version a newer than version b?
    local x, y = vtuple(a), vtuple(b)
    for i = 1, math.max(#x, #y) do
        local p, q = x[i] or 0, y[i] or 0
        if p ~= q then return p > q end
    end
    return false
end

-- Copy the bridge that ships inside the addon into the shared folder, when it's missing or
-- older. Files come from bridge\manifest.txt. config.json (your link) is never touched.
local function install_bridge()
    local src = with_sep(addon.path) .. 'bridge\\'
    local dst = S.dir .. 'bridge\\'
    local ship = bridge_version(src)
    if not ship then return false, 'This copy of the addon has no bridge folder. Reinstall the phonechat zip.' end
    local have = bridge_version(dst)
    local manifest = read_file(src .. 'manifest.txt')
    if not manifest then return false, 'The bridge folder is missing manifest.txt. Reinstall the phonechat zip.' end
    -- Same version: still copy if this zip is a different build (its manifest carries a build line).
    if have and not newer(ship, have) and (newer(have, ship) or read_file(dst .. 'manifest.txt') == manifest) then return true end
    mkdir(S.dir)
    mkdir(dst)
    local copied = 0
    for rel in manifest:gmatch('[^\r\n]+') do
        rel = rel:match('^%s*(.-)%s*$')
        if rel ~= '' and rel:sub(1, 1) ~= '#' and not rel:find('%.%.') then
            local wrel = rel:gsub('/', '\\')
            local sub = wrel:match('^(.*)\\[^\\]+$')
            if sub then mkdir(dst .. sub) end
            local data = read_file(src .. wrel)
            if data == nil or not write_file(dst .. wrel, data) then
                return false, 'Could not copy ' .. rel .. ' into ' .. dst
            end
            copied = copied + 1
        end
    end
    write_file(dst .. 'manifest.txt', manifest)   -- remembers which build is installed
    -- Desktop Mode launcher (Linux): double-click to run the bridge without the game.
    local up = unix_path(S.dir)
    if up then
        write_file(S.dir .. 'phonechatXI Bridge.desktop', table.concat({
            '[Desktop Entry]',
            'Type=Application',
            'Name=phonechatXI Bridge',
            'Comment=Start the phonechatXI bridge and show the QR code',
            'Exec=/bin/sh "' .. up .. 'bridge/start.sh" --open',
            'Icon=' .. up .. 'bridge/icons/icon-512.png',
            'Terminal=true',
            '',
        }, '\n'))
    end
    note(('Bridge %s installed in %sbridge (%d files).'):format(ship, S.dir, copied))
    return true, ship
end

local function bridge_status()
    local s = read_file(S.dir .. 'status.json')
    if s == nil then return false, nil, nil end
    local ts  = tonumber(s:match('"ts"%s*:%s*(%d+)'))
    local run = s:match('"running"%s*:%s*(%a+)')
    local url = s:match('"url"%s*:%s*"([^"]*)"')
    local ver = s:match('"version"%s*:%s*"([^"]*)"')
    if ts == nil or run == 'false' then return false, url, ver end
    return math.abs(os.time() - ts) <= STATUS_FRESH, url, ver
end

local function announce(on)
    local text = 'Phone chat bridge: ' .. (on and 'ON' or 'OFF')
    local ok = pcall(function ()
        print(on and chat.success(text) or chat.error(text))
    end)
    if not ok then print(text) end
end

local function last_log_line()
    local s = read_file(S.dir .. 'bridge.log')
    if not s then return nil end
    local last
    for line in s:gmatch('[^\r\n]+') do
        if line:match('%S') then last = line end
    end
    return last
end

local function start_bridge(quiet)
    if bridge_status() then
        if not quiet then note('The bridge is already running.') end
        return
    end
    if S.starting_at and os.time() - S.starting_at < START_WAIT then
        if not quiet then note('The bridge is still starting. Give it a few seconds.') end
        return
    end
    local ok, err = install_bridge()
    if not ok then
        S.start_error = err
        if not quiet then note(err) end
        return
    end
    local up = unix_path(S.dir)
    local cmd
    if up then
        -- Proton/Wine runs the Linux script directly; it works inside Steam's game container.
        cmd = 'start /unix /bin/sh ' .. up .. 'bridge/start.sh'
    else
        local bat = S.dir .. 'bridge\\start-bridge.bat'
        if not exists(bat) then
            S.start_error = 'start-bridge.bat is missing from ' .. S.dir .. 'bridge.'
            if not quiet then note(S.start_error) end
            return
        end
        cmd = 'start "" /min "' .. bat .. '"'
    end
    local done = pcall(function () os.execute(cmd) end)
    if not done then
        S.start_error = 'Could not start the bridge.'
        if not quiet then note(S.start_error) end
        return
    end
    S.starting_at = os.time()
    S.start_error = nil
    if not quiet then note('Starting the bridge...') end
end

local function stop_bridge(quiet)
    if not append_file(S.dir .. 'stop.request', tostring(os.time())) then
        if not quiet then note('Could not ask the bridge to stop (folder not writable?).') end
        return
    end
    S.starting_at = nil
    if not quiet then note('Stopping the bridge. It shows OFF within a few seconds.') end
end

local function new_link()
    if not append_file(S.dir .. 'newlink.request', tostring(os.time())) then
        note('Could not ask for a new link (folder not writable?).')
        return
    end
    S.qr_url = nil
    note('Made a new phone link. The old one stops working. Scan the new QR in the /pchat window.')
end

local function print_link()
    local on, url = bridge_status()
    if on and url then
        note('Phone link: ' .. url)
    else
        note('The bridge is off. Start it with /pchat start.')
    end
end

local function refresh_status()
    local on, url, ver = bridge_status()
    S.url, S.bver = url, ver
    if on then S.starting_at = nil end
    if not on and S.starting_at and os.time() - S.starting_at > START_WAIT then
        S.starting_at = nil
        local why = on_linux() and last_log_line() or nil
        S.start_error = 'The bridge did not start.' .. (why and (' Last line of bridge.log: ' .. why) or
            (on_linux() and '' or ' Is Python 3 installed with "Add to PATH" ticked?'))
        note(S.start_error)
    end
    return on
end

-- Is the running bridge older than the one this addon carries? (After an update, until restarted.)
local function bridge_outdated()
    if not S.bver then return false end
    if S.ship == nil then S.ship = bridge_version(with_sep(addon.path) .. 'bridge\\') or false end
    return S.ship and newer(S.ship, S.bver) or false
end

local function check_bridge()
    local on = refresh_status()
    if S.bridge ~= on then
        S.bridge = on
        announce(on)
        if on and bridge_outdated() and not S.update_told then
            S.update_told = true
            note('A newer bridge (' .. S.ship .. ') came with this addon. To use it: /pchat stop, then /pchat start.')
        end
        if on and S.cfg.showlink and not S.link_shown then
            S.link_shown = true
            print_link()
        end
        if on and not S.cfg.qrseen and has_imgui then
            -- First time ever: open the window so the QR is right there.
            S.cfg.qrseen = true
            save_cfg()
            S.show_config[1] = true
        end
        if not on and not S.hinted and not S.starting_at then
            S.hinted = true
            note('Type /pchat start to start the bridge, or /pchat for the QR and settings.')
        end
    end
end

----------------------------------------------------------------------------------------------------
-- Outbox: lines from the phone, typed one at a time
----------------------------------------------------------------------------------------------------

-- Stock emotes (same list as the bridge's commands.json).
local EMOTES = {}
for e in ([[amazed angry bell blush bow cheer clap comfort cry dance dance1 dance2 dance3 dance4
    disgusted doubt doze farewell fume goodbye grin huh hurray joy jump kneel laugh muted no nod
    panic point poke praise psych salute shocked sigh sit sitchair slap smile stagger stare sulk
    surprised think toss upset wave welcome yes]]):gmatch('%S+') do EMOTES[e] = true end
local JOBS = {}
for j in ('war mnk whm blm rdm thf pld drk bst brd rng sam nin drg smn blu cor pup dnc sch geo run'):gmatch('%S+') do JOBS[j] = true end
-- CatsEye ! commands (same list as the bridge's commands.json, info and action together).
local SERVER = {}
for c in ([[artifacts currency dailies dailykills essences fatigue help hunter incursion keys lsstats maat
    mog pass pf points pops prestige quest re rifts rubyweather scroll skills summitcalc trials vault
    ventures wspoints box chef config dawnunstuck delexp newadventurer sanction sigil signet skipfloor
    summit summitnotify summitreward venture]]):gmatch('%S+') do SERVER[c] = true end

-- Is this valid Shift-JIS text the game's own chat box could produce? Rejects bytes no keyboard
-- can type: a lone 0x80 or 0xA0, 0xFD-0xFF (0xFD starts an auto-translate block), the
-- unused and user-defined rows (lead bytes 0xEF-0xF9) and a lead byte without a valid second byte.
local function sjis_ok(s)
    local i, n = 1, #s
    while i <= n do
        local b = s:byte(i)
        if b < 0x80 then
            i = i + 1
        elseif b >= 0xA1 and b <= 0xDF then            -- half-width katakana
            i = i + 1
        elseif (b >= 0x81 and b <= 0x9F) or (b >= 0xE0 and b <= 0xEE) or (b >= 0xFA and b <= 0xFC) then
            local t = s:byte(i + 1)
            if t == nil or t < 0x40 or t == 0x7F or t > 0xFC then return false end
            i = i + 2
        else
            return false                               -- 0x80, 0xA0, 0xEF-0xF9, 0xFD-0xFF
        end
    end
    return true
end

local function emote_ok(cmd)
    local name, opt = cmd:match('^/(%l[%l%d]*)$'), ''
    if not name then name, opt = cmd:match('^/(%l[%l%d]*) (%w+)$') end
    if not name then return false end
    if name == 'jobemote' then return JOBS[opt] == true end
    if not EMOTES[name] then return false end
    return opt == '' or opt == 'motion' or opt == 'text' or (name == 'sitchair' and opt:match('^[1-4]$') ~= nil)
end

-- Only these shapes are ever typed. Everything else is dropped.
local function allowed(cmd)
    if cmd:find('[%z\1-\31\127]') then return false end
    if #cmd > 130 then return false end      -- FFXI's chat line limit; nothing longer is ever typed
    if not sjis_ok(cmd) then return false end
    local body = cmd:match('^/l2? (.+)$') or cmd:match('^/p (.+)$') or cmd:match('^/sh (.+)$')
              or cmd:match('^/s (.+)$') or cmd:match('^/t %a+ (.+)$')
    if body then
        -- The bridge never sends a message that starts with a space, so "/s  !cmd" is refused too.
        if body:find('^%s') then return false end
        -- No command hidden inside a chat line. /s !cmd would dodge the server command list.
        local first = body:sub(1, 1)
        if first == '/' or first == '!' then return false end
        -- No ; followed by a command, in case anything treats ; as "run the next command".
        return body:find(';%s*[/!]') == nil
    end
    local name = cmd:match('^/say !(%a+)$') or cmd:match('^/say !(%a+) [%w_%-][%w _%-]*$')
    if name then return SERVER[name:lower()] == true end
    return emote_ok(cmd)
end

-- Ids of recent outbox lines, so a line that shows up twice is only typed once.
local seen_ids, seen_order = {}, {}

local function take_line(line)
    local id, ts, cmd = line:match('^([%w%-]+)\t(%d+)\t(.+)$')
    if id == nil then return end
    if seen_ids[id] then
        S.dropped = S.dropped + 1
        return
    end
    seen_ids[id] = true
    seen_order[#seen_order + 1] = id
    if #seen_order > 200 then seen_ids[table.remove(seen_order, 1)] = nil end
    if math.abs(os.time() - tonumber(ts)) > STALE_SECONDS then
        S.dropped = S.dropped + 1
        return
    end
    if not allowed(cmd) or #S.sendq >= SENDQ_MAX then
        S.dropped = S.dropped + 1
        return
    end
    S.sendq[#S.sendq + 1] = cmd
end

local function poll_outbox()
    if not S.ready then return end
    local path = S.dir .. 'outbox-' .. S.name .. '.log'
    local f = io.open(path, 'rb')
    if f == nil then
        S.out_off = S.out_off or 0
        return
    end
    local size = f:seek('end') or 0
    if S.out_off == nil then
        S.out_off = size          -- never type anything that was waiting before we started
        f:close()
        return
    end
    if size < S.out_off then S.out_off = 0 end
    if size > S.out_off then
        f:seek('set', S.out_off)
        local data = f:read(size - S.out_off) or ''
        local cut = data:match('^.*()\n')
        if cut then
            S.out_off = S.out_off + cut
            for line in data:sub(1, cut):gmatch('([^\n]*)\n') do
                take_line((line:gsub('\r$', '')))
            end
        end
    end
    f:close()
end

local function send_next()
    local cmd = table.remove(S.sendq, 1)
    if cmd == nil then return end
    local ok = pcall(function ()
        AshitaCore:GetChatManager():QueueCommand(1, cmd)
    end)
    if ok then S.sent = S.sent + 1 else S.errors = S.errors + 1 end
end

----------------------------------------------------------------------------------------------------
-- Line parsing
----------------------------------------------------------------------------------------------------

local function parse(channel, dir, text)
    local name, body
    if channel == 'tell' then
        if dir == 'in' then
            name, body = text:match('^(%S+)>>%s?(.*)$')
        else
            name, body = text:match('^>>(%S+)%s*:%s?(.*)$')
        end
    elseif channel == 'party' then
        name, body = text:match('^%((%S+)%)%s?(.*)$')
    elseif channel == 'ls1' or channel == 'ls2' then
        local _
        _, name, body = text:match('^%[(%d)%]<(%S+)>%s?(.*)$')
    elseif channel == 'unity' then
        name, body = text:match('^{(.-)}%s?(.*)$')
    elseif channel == 'shout' then
        name, body = text:match('^(%S+) : (.*)$')
    elseif channel == 'yell' then
        local zone
        name, zone, body = text:match('^(%S+)%[(.-)%]:%s?(.*)$')
        if name then name = name .. '[' .. zone .. ']' end
    end
    if name == nil then
        return '', text
    end
    return name, (body:gsub('^%s+', ''))
end

-- Party Finder ads and bazaar visits from the system modes.
-- Returns true when the line was handled.
local function system_line(text)
    local ad = text:match('^%[PartyFinder%]%s*(.+)$')
    if ad then
        emit('finder', 'in', '', ad)
        return true
    end
    local low = text:lower()
    if low:find('your bazaar', 1, true) then
        emit('bazaar', 'in', '', text)
        return true
    end
    return false
end

local function handle_line(raw_mode, message)
    local mode = bit.band(raw_mode, 0xFF)
    debug_log(raw_mode, mode, message, false)
    local text = clean(message)
    if text == '' then return end

    -- Say: modes 9 (in) and 1 (out), format "Name : msg". Mode 9 also carries system status
    -- lines, so only lines in the say format count as say. Lines starting with ! are server
    -- commands (ours go out as /say !cmd), so they are skipped.
    if mode == 9 or mode == 1 then
        local name, body = text:match('^(%S+) : (.*)$')
        if name then
            if body:sub(1, 1) ~= '!' then
                emit('say', mode == 1 and 'out' or 'in', name, body)
            end
            return
        end
    end

    local info = MODES[mode]
    if info == nil then
        if mode == 0 then
            local area = text:match('^=== Area: (.+) ===$')
            if area then emit('zone', 'in', '', area) end
            return
        end
        if NOTICE_MODES[mode] then system_line(text) end
        return
    end

    local channel, dir = info[1], info[2]

    if channel == 'server' then
        text = (text:gsub('^%-+=*%s*SystemMessage%s*=*%-+%s*', ''))
        if text == '' then return end
        if system_line(text) then return end
        -- Linkshell message of the day: "[1]< text >"
        local n, motd = text:match('^%[(%d)%]<%s*(.-)%s*>$')
        if n == '1' or n == '2' then
            emit('motd', 'in', 'ls' .. n, motd)
            return
        end
        emit(channel, dir, '', text)
        return
    end

    if channel == 'system' or channel == 'emote' then
        emit(channel, dir, '', text)
        return
    end

    local name, body = parse(channel, dir, text)
    if channel == 'unity' and name == 'Populox' then
        channel = 'venture'
    end
    emit(channel, dir, name, body)
end

-- Lines printed by other addons are never passed on. With /pchat debug on they're logged
-- (flagged) so they can be checked, and that's all.
local function handle_injected(raw_mode, message)
    local mode = bit.band(raw_mode, 0xFF)
    debug_log(raw_mode, mode, message, true)
end

----------------------------------------------------------------------------------------------------
-- QR code (drawn with ImGui; encoder: luaqrcode, BSD-3, see qrencode-LICENSE.md)
----------------------------------------------------------------------------------------------------

local qrenc = nil
local function load_qr()
    if qrenc ~= nil then return qrenc end
    qrenc = false
    pcall(function ()
        local fn = loadfile(with_sep(addon.path) .. 'qrencode.lua')
        if fn then
            local m = fn()
            if type(m) == 'table' and type(m.qrcode) == 'function' then qrenc = m end
        end
    end)
    return qrenc
end

local function qr_matrix(url)
    if S.qr_url == url then return S.qr end
    S.qr_url, S.qr = url, nil
    local enc = load_qr()
    if not enc then return nil end
    local ok, good, tab = pcall(enc.qrcode, url)
    if ok and good and type(tab) == 'table' then S.qr = tab end
    return S.qr
end

local function xy(a, b)
    if type(a) == 'table' then return a.x or a[1], a.y or a[2] end
    return a, b
end

local function draw_qr(url)
    local m = qr_matrix(url)
    if not m or S.qr_broken then return false end
    local n, px, quiet = #m, 5, 4
    local size = (n + quiet * 2) * px
    local ok = pcall(function ()
        local x, y = xy(imgui.GetCursorScreenPos())
        local dl = imgui.GetWindowDrawList()
        local white, black = 0xFFFFFFFF, 0xFF000000
        dl:AddRectFilled({ x, y }, { x + size, y + size }, white, 0)
        for cx = 1, n do
            local col = m[cx]
            for cy = 1, n do
                if col[cy] > 0 then
                    local x0 = x + (quiet + cx - 1) * px
                    local y0 = y + (quiet + cy - 1) * px
                    dl:AddRectFilled({ x0, y0 }, { x0 + px, y0 + px }, black, 0)
                end
            end
        end
        imgui.Dummy({ size, size })
    end)
    if not ok then S.qr_broken = true end
    return ok
end

----------------------------------------------------------------------------------------------------
-- Help and the phonechatXI window
----------------------------------------------------------------------------------------------------

local function print_help()
    local on, url = bridge_status()
    note(('Bridge: %s%s'):format(on and 'ON' or 'OFF', (on and url) and ('  |  ' .. url) or ''))
    note('/pchat          window with start/stop, the QR code and settings (same as /pchat config)')
    note('/pchat start    start the bridge     /pchat stop   stop it')
    note('/pchat url      print the phone link')
    note('/pchat newlink  make a new phone link')
    note('/pchat debug    debug log (now ' .. (S.debug and 'on' or 'off') .. ')')
    note(('character: %s | lines: %d | sent: %d | dropped: %d | errors: %d'):format(
        S.name or '(not known yet)', S.lines, S.sent, S.dropped, S.errors))
end

local next_panel = 0
local function draw_config()
    if not has_imgui or not S.show_config[1] then return end
    local now = os.clock()
    if now >= next_panel then
        next_panel = now + PANEL_CHECK
        S.bridge_now = refresh_status()
    end
    local ok, err = pcall(function ()
        if imgui.Begin('phonechatXI', S.show_config, ImGuiWindowFlags_AlwaysAutoResize) then
            local on, url = S.bridge_now, S.url
            local state = on and ('ON' .. (S.bver and ('  (' .. S.bver .. ')') or ''))
                or (S.starting_at and 'starting...' or 'OFF')
            imgui.Text('Bridge: ' .. state)
            imgui.SameLine()
            if on then
                if imgui.Button('Stop') then stop_bridge(false) end
            elseif not S.starting_at then
                if imgui.Button('Start') then start_bridge(false) end
            end
            local a = { S.cfg.autostart }
            if imgui.Checkbox('Start with the game', a) then
                S.cfg.autostart = a[1]
                save_cfg()
            end
            if S.start_error and not on then
                imgui.TextWrapped(S.start_error)
            end
            if on and bridge_outdated() then
                imgui.TextWrapped('Update ready (' .. S.ship .. '). Click Stop, then Start.')
            end
            if on and url then
                imgui.Separator()
                imgui.Text('Scan with your phone (same Wi-Fi):')
                if not draw_qr(url) then
                    imgui.Text('(The QR code could not be drawn here.)')
                end
                imgui.Text(url)
                local armed = os.clock() < S.newlink_armed
                if imgui.Button(armed and 'Click again to replace the link' or 'New phone link') then
                    if armed then
                        S.newlink_armed = 0
                        new_link()
                    else
                        S.newlink_armed = os.clock() + 4
                    end
                end
            end
            imgui.Separator()
            local b = { S.cfg.showlink }
            if imgui.Checkbox('Print the link in chat when the bridge starts', b) then
                S.cfg.showlink = b[1]
                save_cfg()
            end
            local d = { S.debug }
            if imgui.Checkbox('Debug log (this session only)', d) then
                S.debug = d[1]
            end
            imgui.Text('Folder: ' .. S.dir)
        end
        imgui.End()
    end)
    if not ok then
        S.show_config[1] = false
        note('window error: ' .. tostring(err))
    end
end

----------------------------------------------------------------------------------------------------
-- Events
----------------------------------------------------------------------------------------------------

ashita.events.register('load', 'phonechat_load', function ()
    S.dir = resolve_dir()
    load_cfg()
    resolve_name()
    S.next_name  = os.clock() + 1
    S.next_check = os.time() + CHECK_EVERY
    check_bridge()
    if S.cfg.autostart and not S.bridge then
        start_bridge(true)
    end
end)

ashita.events.register('text_in', 'phonechat_text_in', function (e)
    local ok, err
    if e.injected then
        ok, err = pcall(handle_injected, e.mode, e.message)
    else
        ok, err = pcall(handle_line, e.mode, e.message)
    end
    if not ok then
        S.errors = S.errors + 1
        if S.errors == 1 then
            note('error while reading a chat line: ' .. tostring(err))
        end
    end
end)

ashita.events.register('packet_in', 'phonechat_packet_in', function (e)
    if e.id ~= 0x000A then return end
    pcall(function ()
        local raw = e.data:sub(0x84 + 1, 0x84 + 16)
        local n = raw:match('^[%w_%-]+')
        if n and #n >= 3 then set_name(n) end
    end)
end)

ashita.events.register('d3d_present', 'phonechat_tick', function ()
    local now = os.time()
    local clk = os.clock()
    if not S.ready and clk >= S.next_name then
        S.next_name = clk + 1
        resolve_name()
    end
    if now >= S.next_check then
        S.next_check = now + CHECK_EVERY
        check_bridge()
    end
    if clk >= S.next_out then
        S.next_out = clk + OUTBOX_EVERY
        local ok = pcall(poll_outbox)
        if not ok then S.errors = S.errors + 1 end
    end
    if #S.sendq > 0 and clk >= S.next_send then
        S.next_send = clk + SEND_GAP
        send_next()
    end
    draw_config()
end)

ashita.events.register('command', 'phonechat_command', function (e)
    local args = e.command:args()
    if #args == 0 then return end
    local c = args[1]:lower()
    if c ~= '/pchat' and c ~= '/pcxi' and c ~= '/phonechat' then return end
    e.blocked = true

    local sub = (args[2] or ''):lower()
    if sub == 'debug' then
        S.debug = not S.debug
        note('debug log ' .. (S.debug and 'on: ' .. S.dir .. 'debug-' .. (S.name or 'unknown') .. '.log' or 'off'))
    elseif sub == 'url' or sub == 'link' then
        print_link()
    elseif sub == 'start' then
        start_bridge(false)
    elseif sub == 'stop' then
        stop_bridge(false)
    elseif sub == 'newlink' then
        new_link()
    elseif sub == '' or sub == 'config' or sub == 'settings' or sub == 'qr' then
        if not has_imgui and sub == '' then
            print_help()
        elseif has_imgui then
            S.show_config[1] = (sub == 'qr' or sub == '') or not S.show_config[1]
        else
            note('The window needs ImGui, which did not load. Use /pchat url for the link.')
        end
    else
        print_help()
    end
end)

--[[
    phonechat v1.0.0 (phonechatXI)

    Mirrors chat to a feed file that the phonechatXI bridge serves to your phone,
    and types the replies you send from the phone, one line at a time.

    What it will type (anything else is dropped, even if the bridge asks):
        /l  /l2  /p  /s  /sh  /t Name   followed by your message
        /say !command [simple arguments]     CatsEye server commands
        /wave, /bow ... [motion|text]       stock emotes (and /sitchair 1-4, /jobemote job)
    It never types anything on its own: no auto replies, triggers, timers or repeats.
    Each line comes from one tap on the phone.

    Commands:
        /pchat            status, phone link and the list of options
        /pchat url        print the phone link
        /pchat start      start the bridge (Windows, if start-bridge.bat is in the folder)
        /pchat stop       stop the bridge
        /pchat config     settings window
        /pchat debug      toggle debug logging (every chat line with its mode number)
        /pchat help       the list of options

    Folder: the path in dir.txt next to this file, or <Ashita>\config\addons\phonechat\
    Feed line: time <TAB> channel <TAB> in|out <TAB> name <TAB> body   (line breaks as 0x0B)
    Outbox line: id <TAB> unix time <TAB> command
]]

addon.name    = 'phonechat'
addon.author  = 'Kevin'
addon.version = '1.0.0'
addon.desc    = 'phonechatXI: mirrors chat to your phone and types the replies you send from it.'
addon.link    = ''

require('common')
local chat = require('chat')
local has_imgui, imgui = pcall(require, 'imgui')

local PENDING_MAX   = 300   -- lines kept while we wait to learn the character name
local STATUS_FRESH  = 10    -- seconds; bridge heartbeat older than this = OFF
local CHECK_EVERY   = 5     -- seconds between bridge status checks
local OUTBOX_EVERY  = 0.5   -- seconds between outbox reads
local SEND_GAP      = 1.0   -- seconds between lines typed into the game
local STALE_SECONDS = 15    -- outbox lines older than this are dropped, never typed late
local SENDQ_MAX     = 8

local S = {
    dir     = nil,
    name    = nil,
    path    = nil,
    ready   = false,
    pending = {},
    debug   = false,
    bridge  = nil,
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
    cfg = { autostart = false, showlink = false },
    link_shown = false,
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
    [123] = { 'system', 'in'  },
    [200] = { 'server', 'in'  },
    [205] = { 'server', 'in'  },
}

-- Unmapped modes where a line that says "venture" may go to the Ventures tab: the zone-in
-- status line (9) and the plain system-message modes. Combat modes are never on this list,
-- so a mob or item with "venture" in its name can't drag a battle line in.
local VENTURE_MODES = { [9] = true, [121] = true, [127] = true, [131] = true, [142] = true }

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

local function exists(path)
    local f = io.open(path, 'rb')
    if f then f:close() return true end
    return false
end

local function with_sep(p)
    p = tostring(p or '')
    if p ~= '' and not p:match('[\\/]$') then p = p .. '\\' end
    return p
end

-- Folder: dir.txt next to the addon, else <Ashita>\config\addons\phonechat\.
local function resolve_dir()
    local here = ''
    pcall(function () here = with_sep(addon.path) end)
    local txt = here ~= '' and read_file(here .. 'dir.txt') or nil
    if txt then
        txt = txt:gsub('^\239\187\191', ''):match('^%s*(.-)%s*$')
        if txt ~= '' then return with_sep(txt) end
    end
    local install = ''
    pcall(function () install = with_sep(AshitaCore:GetInstallPath()) end)
    return install .. 'config\\addons\\phonechat\\'
end

-- Escape control bytes so they are visible in the debug log (0x80-0x9F too, for item IDs).
local function esc(s)
    return (tostring(s or ''):gsub('[%z\1-\31\127-\159\253]', function (c)
        return ('\\x%02X'):format(c:byte())
    end))
end

-- Turn a raw chat line into clean text. Output stays in Shift-JIS; the bridge converts it.
local function clean(s)
    s = tostring(s or '')
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
    pcall(function () ashita.fs.create_dir(S.dir) end)
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
    pcall(function () ashita.fs.create_dir(S.dir) end)

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
-- Bridge status
----------------------------------------------------------------------------------------------------

local function bridge_status()
    local s = read_file(S.dir .. 'status.json')
    if s == nil then return false, nil end
    local ts  = tonumber(s:match('"ts"%s*:%s*(%d+)'))
    local run = s:match('"running"%s*:%s*(%a+)')
    local url = s:match('"url"%s*:%s*"([^"]*)"')
    if ts == nil or run == 'false' then return false, url end
    return math.abs(os.time() - ts) <= STATUS_FRESH, url
end

local function announce(on)
    local text = 'Phone chat bridge: ' .. (on and 'ON' or 'OFF')
    local ok = pcall(function ()
        print(on and chat.success(text) or chat.error(text))
    end)
    if not ok then print(text) end
end

local function on_deck()
    return S.dir:upper():sub(1, 3) == 'Z:\\'
end

local function start_bridge(quiet)
    if bridge_status() then
        if not quiet then note('The bridge is already running.') end
        return
    end
    if on_deck() then
        if not quiet then note('On the Steam Deck, start the bridge from the phonechatXI Decky panel, or run start.sh in Desktop Mode.') end
        return
    end
    local bat = S.dir .. 'start-bridge.bat'
    if not exists(bat) then
        if not quiet then note('No start-bridge.bat in ' .. S.dir .. '. Start the bridge yourself, then it shows here as ON.') end
        return
    end
    local ok = pcall(function () os.execute('start "" /min "' .. bat .. '"') end)
    if not quiet then note(ok and 'Starting the bridge...' or 'Could not start the bridge.') end
end

local function stop_bridge()
    if not append_file(S.dir .. 'stop.request', tostring(os.time())) then
        note('Could not ask the bridge to stop (folder not writable?).')
        return
    end
    note('Asked the bridge to stop. It shows OFF within a few seconds.')
end

local function print_link()
    local on, url = bridge_status()
    if on and url then
        note('Phone link: ' .. url)
    else
        note('The bridge is OFF, so there is no link yet.')
    end
end

local function check_bridge()
    local on = bridge_status()
    if S.bridge ~= on then
        S.bridge = on
        announce(on)
        if on and S.cfg.showlink and not S.link_shown then
            S.link_shown = true
            print_link()
        end
        if not on and not S.hinted then
            S.hinted = true
            note('Start the bridge from the Decky panel or start.sh. Type /pchat for options.')
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
    local body = cmd:match('^/l2? (.+)$') or cmd:match('^/p (.+)$') or cmd:match('^/sh (.+)$')
              or cmd:match('^/s (.+)$') or cmd:match('^/t %a+ (.+)$')
    if body then
        -- No command hidden inside a chat line. /s !cmd would dodge the server command list.
        local first = body:sub(1, 1)
        return first ~= '/' and first ~= '!'
    end
    if cmd:match('^/say ![%a]+$') or cmd:match('^/say ![%a]+ [%w _%-]+$') then return true end
    return emote_ok(cmd)
end

local function take_line(line)
    local id, ts, cmd = line:match('^([%w%-]+)\t(%d+)\t(.+)$')
    if id == nil then return end
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

local function handle_line(raw_mode, message)
    local mode = bit.band(raw_mode, 0xFF)
    local text = clean(message)
    if text == '' then return end

    if S.debug then
        append_file(S.dir .. 'debug-' .. (S.name or 'unknown') .. '.log',
            ('%s\t%d\t%d\t%s\n'):format(os.date('%H:%M:%S'), raw_mode, mode, esc(message)))
    end

    -- Say. Not seen in a CatsEye log yet; retail uses 9 (in) and 1 (out), format "Name : msg".
    -- Mode 9 also carries the venture status line, so only lines in the say format count as say.
    -- Lines starting with ! are server commands (ours go out as /say !cmd), so they are skipped.
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
        -- Venture status lines that arrive in modes we do not otherwise map.
        if VENTURE_MODES[mode] and text:lower():find('venture', 1, true) then
            emit('venture', 'in', '', text)
        end
        return
    end

    local channel, dir = info[1], info[2]

    if channel == 'server' then
        text = (text:gsub('^%-+=*%s*SystemMessage%s*=*%-+%s*', ''))
        if text == '' then return end
        if text:lower():find('venture', 1, true) then channel = 'venture' end
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

----------------------------------------------------------------------------------------------------
-- Help and config window
----------------------------------------------------------------------------------------------------

local function print_help()
    local on, url = bridge_status()
    note(('Bridge: %s%s'):format(on and 'ON' or 'OFF', (on and url) and ('  |  ' .. url) or ''))
    note('/pchat url      print the phone link')
    note('/pchat start    start the bridge' .. (on_deck() and ' (on the Deck: use the Decky panel)' or ''))
    note('/pchat stop     stop the bridge')
    note('/pchat config   settings window')
    note('/pchat debug    toggle the debug log (now ' .. (S.debug and 'on' or 'off') .. ')')
    note(('character: %s | lines: %d | sent: %d | dropped: %d | errors: %d'):format(
        S.name or '(not known yet)', S.lines, S.sent, S.dropped, S.errors))
end

local function draw_config()
    if not has_imgui or not S.show_config[1] then return end
    local ok, err = pcall(function ()
        if imgui.Begin('phonechatXI', S.show_config, ImGuiWindowFlags_AlwaysAutoResize) then
            local on, url = bridge_status()
            imgui.Text('Bridge: ' .. (on and 'ON' or 'OFF'))
            if on and url then imgui.Text(url) end
            imgui.Separator()
            local a = { S.cfg.autostart }
            if imgui.Checkbox('Start the bridge when the addon loads', a) then
                S.cfg.autostart = a[1]
                save_cfg()
            end
            if on_deck() then
                imgui.Text('  (On the Deck this uses the Decky panel instead.)')
            end
            local b = { S.cfg.showlink }
            if imgui.Checkbox('Print the phone link when the bridge comes on', b) then
                S.cfg.showlink = b[1]
                save_cfg()
            end
            local d = { S.debug }
            if imgui.Checkbox('Debug log (this session only)', d) then
                S.debug = d[1]
            end
            imgui.Separator()
            imgui.Text('Folder: ' .. S.dir)
            if imgui.Button('Start bridge') then start_bridge(false) end
            imgui.SameLine()
            if imgui.Button('Stop bridge') then stop_bridge() end
        end
        imgui.End()
    end)
    if not ok then
        S.show_config[1] = false
        note('settings window error: ' .. tostring(err))
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
    if e.injected then return end   -- addon prints (including our own ON/OFF line)
    local ok, err = pcall(handle_line, e.mode, e.message)
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
    if c ~= '/pchat' and c ~= '/pcxi' then return end
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
        stop_bridge()
    elseif sub == 'config' or sub == 'settings' then
        if has_imgui then
            S.show_config[1] = not S.show_config[1]
        else
            note('The settings window needs ImGui, which did not load.')
        end
    elseif sub == 'qr' then
        note('An in-game QR code is coming later. For now scan the QR in the Decky panel, or open /setup on the computer running the bridge.')
    else
        print_help()
    end
end)

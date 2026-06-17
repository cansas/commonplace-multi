--[[--
Commonkore — KOReader → Commonplace Exporter

A provider plugin that registers the Commonplace exporter target
with the KOReader exporter plugin via the Provider system.

Installation:
  Copy this directory (commonkore.koplugin/) to KOReader's plugins/:
    koreader/plugins/commonkore.koplugin/main.lua

Then in KOReader:
  Tools (wrench) → Export → Commonplace → set server URL + API token → toggle on
--]]--

local Device = require("device")
local InputDialog = require("ui/widget/inputdialog")
local UIManager = require("ui/uimanager")
local http = require("socket.http")
local ltn12 = require("ltn12")
local logger = require("logger")
local Provider = require("provider")
local rapidjson = require("rapidjson")
local socket = require("socket")
local socketutil = require("socketutil")
local _ = require("gettext")

-- Self-contained Commonplace exporter (no dependency on exporter.koplugin/base.lua)
local CommonplaceExporter = {
    name = "commonkore",
    is_remote = true,
}

function CommonplaceExporter:loadSettings()
    local plugin_settings = G_reader_settings:readSetting("exporter") or {}
    self.settings = plugin_settings[self.name] or {}
end

function CommonplaceExporter:saveSettings()
    local plugin_settings = G_reader_settings:readSetting("exporter") or {}
    plugin_settings[self.name] = self.settings
    G_reader_settings:saveSetting("exporter", plugin_settings)
end

function CommonplaceExporter:isReadyToExport()
    return self.settings.server_url and self.settings.token and true or false
end

function CommonplaceExporter:isEnabled()
    return self.settings.enabled and self:isReadyToExport()
end

function CommonplaceExporter:toggleEnabled()
    if self:isReadyToExport() then
        self.settings.enabled = not self.settings.enabled
        self:saveSettings()
    end
end

function CommonplaceExporter:getMenuTable()
    return {
        text = _("Commonplace"),
        checked_func = function() return self:isEnabled() end,
        sub_item_table = {
            {
                text = _("Set server URL"),
                keep_menu_open = true,
                callback = function()
                    local dialog
                    dialog = InputDialog:new{
                        title = _("Commonplace server URL"),
                        input = self.settings.server_url,
                        hint = _("https://example.com:8765"),
                        buttons = {{
                            {
                                text = _("Cancel"),
                                callback = function()
                                    UIManager:close(dialog)
                                end,
                            },
                            {
                                text = _("Set URL"),
                                callback = function()
                                    self.settings.server_url = dialog:getInputText()
                                    self.settings.server_url = self.settings.server_url:gsub("/+$", "")
                                    self:saveSettings()
                                    UIManager:close(dialog)
                                end,
                            },
                        }},
                    }
                    UIManager:show(dialog)
                    dialog:onShowKeyboard()
                end,
            },
            {
                text = _("Set API token"),
                keep_menu_open = true,
                callback = function()
                    local dialog
                    dialog = InputDialog:new{
                        title = _("Commonplace API token"),
                        input = self.settings.token,
                        hint = _("Token from the Settings page"),
                        buttons = {{
                            {
                                text = _("Cancel"),
                                callback = function()
                                    UIManager:close(dialog)
                                end,
                            },
                            {
                                text = _("Set token"),
                                callback = function()
                                    self.settings.token = dialog:getInputText()
                                    self:saveSettings()
                                    UIManager:close(dialog)
                                end,
                            },
                        }},
                    }
                    UIManager:show(dialog)
                    dialog:onShowKeyboard()
                end,
            },
            {
                text = _("Export to Commonplace"),
                checked_func = function() return self:isEnabled() end,
                callback = function() self:toggleEnabled() end,
            },
        },
    }
end

function CommonplaceExporter:makeJsonRequest(endpoint, method, body, headers)
    local msg_failed = "json request failed: %s"
    local sink = {}
    local extra_headers = headers or {}
    local body_json, response, err

    body_json, err = rapidjson.encode(body)
    if not body_json then
        return nil, string.format(msg_failed, "cannot encode body" .. err)
    end
    local source = ltn12.source.string(body_json)
    socketutil:set_timeout(socketutil.LARGE_BLOCK_TIMEOUT, socketutil.LARGE_TOTAL_TIMEOUT)

    local request = {
        url = endpoint,
        method = method,
        sink = ltn12.sink.table(sink),
        source = source,
        headers = {
            ["Content-Length"] = #body_json,
            ["Content-Type"] = "application/json",
        },
    }

    for k, v in pairs(extra_headers) do
        request.headers[k] = v
    end

    local code, __, status = socket.skip(1, http.request(request))
    socketutil:reset_timeout()

    if code ~= 200 then
        return nil, string.format(msg_failed, status or code or "network unreachable")
    end

    if not sink[1] then
        return nil, string.format(msg_failed, "no response from server")
    end

    response, err = rapidjson.decode(table.concat(sink))
    if not response then
        return nil, string.format(msg_failed, "unable to decode server response" .. err)
    end

    return response
end

function CommonplaceExporter:createHighlights(booknotes)
    local highlights = {}
    local headers = {
        ["Authorization"] = "Token " .. self.settings.token,
    }

    for _, chapter in ipairs(booknotes) do
        for _, clipping in ipairs(chapter) do
            local highlight = {
                text = clipping.text,
                title = booknotes.title,
                author = booknotes.author ~= "" and booknotes.author:gsub("\n", ", ") or nil,
                source_type = "koreader",
                category = "books",
                note = clipping.note,
                location = clipping.page,
                location_type = "order",
                highlighted_at = os.date("!%Y-%m-%dT%TZ", clipping.time),
            }
            table.insert(highlights, highlight)
        end
    end

    local api_url = self.settings.server_url .. "/api/v2/highlights"
    local result, err = self:makeJsonRequest(api_url, "POST", { highlights = highlights }, headers)

    if not result then
        logger.warn("error exporting to Commonplace", err)
        return false
    end
    return true
end

function CommonplaceExporter:export(t)
    if not self:isReadyToExport() then
        logger.warn("Commonplace: server_url or token not configured")
        return false
    end
    for _, booknotes in ipairs(t) do
        local ok = self:createHighlights(booknotes)
        if not ok then return false end
    end
    return true
end

-- Initialize settings and register with the Provider system
CommonplaceExporter:loadSettings()
Provider:register("exporter", "commonkore", CommonplaceExporter)

-- Return a minimal plugin module so KOReader tracks it as loaded
return { name = "commonkore" }

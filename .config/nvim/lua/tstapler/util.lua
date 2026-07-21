local M = {}

-- Module-level collision registry, keyed "mode\0lhs", enforcing zero-duplicate
-- keymap binds as a hard startup invariant (Epic 1.3).
local registry = {}

local function check(mode, lhs)
  local key = mode .. "\0" .. lhs
  if registry[key] then
    error("duplicate keymap: " .. mode .. " " .. lhs)
  end
  registry[key] = true
end

--- Register and bind a keymap, erroring on any duplicate (mode, lhs).
--- mode must be a single mode string (e.g. "n", "v", "i") — call map() once
--- per mode if you need the same lhs bound in multiple modes, so each
--- (mode, lhs) pair is tracked individually in the collision registry.
---@param mode string
---@param lhs string
---@param rhs string|function
---@param opts table|nil
function M.map(mode, lhs, rhs, opts)
  check(mode, lhs)
  vim.keymap.set(mode, lhs, rhs, opts)
end

--- Reserve a (mode, lhs) pair in the same collision table as map(), without
--- calling vim.keymap.set. For lazy.nvim `keys = {...}` force-load specs whose
--- actual bind happens later (inside the plugin's own config), so those binds
--- still participate in the duplicate-bind invariant.
---@param mode string
---@param lhs string
function M.reserve(mode, lhs)
  check(mode, lhs)
end

return M

-- Single source of truth for <leader> group prefixes.
-- Consumed by:
--   - lua/tstapler/keymaps.lua (header comment references this file, does not
--     re-list the groups, so it can never drift out of sync)
--   - lua/tstapler/which-key.lua (group registration reads this table directly)
-- Do NOT hardcode this table anywhere else.
return {
  f = "find",
  c = "code",
  d = "debug",
  g = "git",
  h = "hunk",
  e = "explorer",
  w = "window",
}

-- cheat-sheet (dev-only, run with :lua or :source):
-- for k, v in pairs(require("tstapler.leader_groups")) do print(k, v) end
-- Renders the group letter -> name table only. Per-group leaf bindings from
-- later stories (1.7.x/2.x) get appended to this cheat-sheet as those phases
-- land; not built out yet since most leaves don't exist in this batch.

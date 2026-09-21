# Fix tree-sitter highlighting for .json / .yaml / .py and friends

## Goal

Restore tree-sitter syntax highlighting in Neovim for every filetype declared
in `nvim/lua/plugins/treesitter.lua` (json, yaml, python, go, lua, …) and make
the spec self-healing so the same broken state cannot recur silently after a
partial install.

Out of scope:

- Changing the parser list, the bash→zsh registration, `indentexpr`, or the
  FileType-pattern derivation.
- Reverting to `tag = "v0.9.3"`.
- Adding `setup({...})` for `nvim-treesitter` (defaults are correct).
- `nvim/lua/plugins/lsp.lua` (uncommitted `yamlls` add is unrelated and stays
  as-is — do not touch).
- `nvim/init.lua` global options, keymaps, autocmds.
- `install.sh`, Stow layout, lockfile.

## Current behavior

Working tree has the v1.x rewrite spec (HEAD still pins v0.9.3 — the working
copy reverts that pin):

- `branch = "main"`, `lazy = false`, `build = ":TSUpdate"`.
- `config = function()` calls `require("nvim-treesitter").install(parsers)` for
  the parser list, registers `bash` for filetype `zsh`, then creates a
  `FileType` autocmd that calls `pcall(vim.treesitter.start, args.buf)` and
  sets the indent expression.

Observed on disk on the user's machine:

- Parsers present for every configured language:
  `~/.local/share/nvim/site/parser/{go,gomod,gosum,python,lua,javascript,typescript,json,yaml,toml,html,css,bash,markdown,markdown_inline,dockerfile,sql,vim,vimdoc}.so`
- Queries directory `~/.local/share/nvim/site/queries/` contains **only**
  symlinks for `ecma`, `html_tags`, `jsx` (auxiliary query sets shared by the
  JS/TS parsers). All other languages have **no** query directory linked.
- Source queries exist in
  `~/.local/share/nvim/lazy/nvim-treesitter/runtime/queries/<lang>/` (these are
  what should be symlinked into `site/queries/<lang>`).

Why this stays broken:

- `lua/nvim-treesitter/install.lua::install_lang` short-circuits when the
  parser is already in `config.get_installed()` and `force` is false; query
  linking is part of `try_install_lang`, so the skip also skips the link step.
- `M.update` (= `:TSUpdate`) calls `needs_update`, which for parsers with a
  revision only compares revisions and ignores missing queries; revisions
  match, so update is a no-op.

Net effect: parsers load, `vim.treesitter.start()` succeeds, no highlight
queries are found in `runtimepath`, no highlight groups get applied →
"no syntax highlighting" for the affected filetypes.

How the broken state was reached (best guess, not actionable): a previous
attempt to migrate to v1 partially installed parsers; then commit `d4cca82`
reverted the spec to `v0.9.3`; the working copy reapplied the v1 spec but
queries were never re-linked because `install()` is now a no-op.

## Target behavior

- After applying the change and one Neovim restart, `site/queries/<lang>`
  exists for every entry in the `parsers` list and resolves (via symlink) to
  the matching directory under `lazy/nvim-treesitter/runtime/queries/`.
- Opening `*.json`, `*.yaml`, `*.py`, `*.go`, `*.lua`, `*.ts`, etc. shows
  tree-sitter coloured tokens, and `:Inspect` reports `@<group>.<lang>`
  captures.
- A future partial-install state (parser present, queries missing) recovers
  automatically on the next `nvim` start without manual `:TSInstall!`.
- Startup behaviour for fresh installs is unchanged: `install(parsers)` runs
  asynchronously, `build = ":TSUpdate"` covers first-install bootstrapping.

## Files

- `nvim/lua/plugins/treesitter.lua` — **edit**. Replace the single
  `require("nvim-treesitter").install(parsers)` call with a small block that
  splits `parsers` into "missing parser" and "parser present but query dir
  missing" buckets, then calls install once per bucket with the right `force`
  flag.

No other files are edited. Specifically:

- `nvim/init.lua` — **read only**, verify nothing relies on the old behaviour.
- `nvim/lua/plugins/lsp.lua` — **untouched**.
- `nvim/lazy-lock.json` — **untouched** (let lazy.nvim regenerate if it ever
  needs to).
- `install.sh` — **untouched**.

## Constraints

- Stay on `nvim-treesitter` `branch = "main"`. Do not pin a tag, do not switch
  branches.
- Keep `lazy = false` and `build = ":TSUpdate"`. v1 explicitly does not
  support lazy-loading.
- Do not add `require("nvim-treesitter").setup({...})` unless a concrete
  reason appears. Default `install_dir` is `vim.fn.stdpath("data") .. "/site"`,
  which is what the rest of the plan assumes.
- Do not change the order or contents of the `parsers` list.
- Do not touch `vim.treesitter.language.register("bash", "zsh")`.
- Do not touch the FileType autocmd body, including `pcall(...)` and the
  `indentexpr` assignment.
- No `vim.wait(...)` synchronous bootstrap — keep install async.
- No new dependencies, no `tree-sitter` CLI requirement (prebuilt parser
  tarballs do not need it; the CLI is only used by
  `:TSInstallFromGrammar` / `generate = true`).
- Code style: 4-space indent, English-only comments, comments only where the
  *why* is non-obvious. No emojis.

## Implementation steps

1. Open `nvim/lua/plugins/treesitter.lua`.

2. Locate the line
   ```lua
   require("nvim-treesitter").install(parsers)
   ```
   directly after the `parsers` table.

3. Replace that single line with the following block (verbatim, same 12-space
   indentation as surrounding code):

   ```lua
   local ts = require("nvim-treesitter")
   local installed = require("nvim-treesitter.config").get_installed()
   local installed_set = {}
   for _, lang in ipairs(installed) do installed_set[lang] = true end

   local query_root = vim.fn.stdpath("data") .. "/site/queries/"
   local to_install, to_relink = {}, {}
   for _, p in ipairs(parsers) do
       if not installed_set[p] then
           to_install[#to_install + 1] = p
       elseif not (vim.uv or vim.loop).fs_stat(query_root .. p) then
           -- parser present but queries never linked (e.g. interrupted install);
           -- force re-run so try_install_lang relinks runtime/queries/<lang>.
           to_relink[#to_relink + 1] = p
       end
   end

   if #to_install > 0 then ts.install(to_install) end
   if #to_relink > 0 then ts.install(to_relink, { force = true }) end
   ```

   Rationale for the only comment: documents *why* we force-reinstall —
   non-obvious behaviour of v1 `install_lang` short-circuit.

4. Leave every other line in the file untouched. The `parsers` list, the
   `vim.treesitter.language.register("bash", "zsh")` call, the
   `fts_from_parsers` table, the `fts` derivation loop, and the FileType
   autocmd stay exactly as they are.

5. Do not touch `nvim/lua/plugins/lsp.lua`, `nvim/init.lua`, or anything
   outside `nvim/lua/plugins/treesitter.lua`.

## Tests

After editing, run from repo root:

- `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p` — Lua parse check
  (documented in `AGENTS.md`). Must exit 0.
- `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty` — JSON
  shape sanity (unrelated to this change but cheap; ensures we did not break
  anything else). *Needs verification* of clean exit on this machine.

Manual verification (cannot be automated here):

1. Start a fresh `nvim` once. Wait for the install jobs to finish (no
   `[nvim-treesitter] Installing language…` message left, or
   `:lua print(vim.inspect(require("nvim-treesitter.config").get_installed()))`
   returns the full list).
2. Quit and start `nvim` again so the FileType autocmd picks up the freshly
   linked queries.
3. `ls -la ~/.local/share/nvim/site/queries/` — expect symlinks for
   `go`, `gomod`, `gosum`, `python`, `lua`, `javascript`, `typescript`,
   `json`, `yaml`, `toml`, `html`, `css`, `bash`, `markdown`,
   `markdown_inline`, `dockerfile`, `sql`, `vim`, `vimdoc` (in addition to
   the pre-existing `ecma`, `html_tags`, `jsx`).
4. Open `x.json` (already in the repo root), a `*.yaml`, and a `*.py` file.
   Expect coloured tokens.
5. `:Inspect` on a string token — expect a `@string.<lang>` (or similar)
   capture in the "Treesitter" section.
6. `:checkhealth nvim-treesitter` — no errors for the listed languages.

## Edge cases

- **Cold-cache user (parsers + queries both missing).** Only `to_install`
  fires; equivalent to the previous code path. `build = ":TSUpdate"` still
  handles the very first install via lazy.nvim build step.
- **Current user state (parsers present, queries missing).** `to_relink`
  fires with `force = true`; `try_install_lang` re-downloads the parser
  tarball, re-installs the `.so` (idempotent overwrite), and relinks
  `runtime/queries/<lang>` into `site/queries/<lang>`. No data loss.
- **No network on launch.** Async `install()` fails silently; user sees no
  highlight for affected langs until network is back and they restart nvim.
  Acceptable, matches prior behaviour.
- **`vim.uv` vs `vim.loop`.** Repo targets Neovim 0.11+, so `vim.uv` exists,
  but use `(vim.uv or vim.loop)` for symmetry with the bootstrap in
  `nvim/init.lua` and defensive cross-version safety.
- **Custom `install_dir` in the future.** The query-presence check hard-codes
  `stdpath("data") .. "/site/queries/"`, matching the default. If someone
  later passes `setup({ install_dir = ... })`, this check diverges. Out of
  scope for this task — note in handoff, no action.
- **Parser-info revision mismatch.** Not handled here; that is `:TSUpdate`'s
  job and runs via the `build` hook.
- **First launch after this change on the broken machine.** Async install
  may not finish before the user opens a file. They will see no highlight
  *during* that first session; one restart fixes it. This is consistent with
  v1 design; do not block startup with `:wait()`.
- **Languages with no `indents.scm`.** Unrelated to highlighting; the existing
  `indentexpr` line stays. No behaviour change here.

## Acceptance criteria

- [ ] `git diff -- nvim/lua/plugins/treesitter.lua` shows only the
      replacement of the single `install(parsers)` call with the
      classification + two-call block, plus the one explanatory comment.
      No other files appear in `git status`/`git diff` for this task.
- [ ] `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p` exits 0.
- [ ] After one or two `nvim` restarts on a broken-state machine,
      `~/.local/share/nvim/site/queries/<lang>` exists for every entry in
      the `parsers` list and is a symlink into
      `~/.local/share/nvim/lazy/nvim-treesitter/runtime/queries/<lang>`.
- [ ] `x.json`, a `*.yaml`, and a `*.py` file render with tree-sitter
      colours; `:Inspect` shows treesitter captures.
- [ ] `lazy = false`, `branch = "main"`, `build = ":TSUpdate"` are preserved.
- [ ] No `setup({...})` was added.
- [ ] No edits in `nvim/lua/plugins/lsp.lua`, `nvim/init.lua`, `install.sh`,
      or any other file.

## Review notes

- Confirm the diff is scoped exactly to `nvim/lua/plugins/treesitter.lua`.
- Confirm the `parsers` list and the `fts_from_parsers` table are identical
  to the pre-change versions (no parser added or removed).
- Confirm the inserted block keeps the existing 4-space + 12-space
  indentation style; no tabs.
- Confirm exactly one comment line was added and it explains *why* the
  force-reinstall is necessary, not *what* the code does.
- Confirm `pcall(vim.treesitter.start, args.buf)` is still in place — do not
  let Codex "improve" the autocmd while there.
- Confirm `vim.treesitter.language.register("bash", "zsh")` is still present
  and unchanged.
- Confirm no `:wait(...)`, no `setup({...})`, no extra `require`s leaked in.
- Confirm `nvim/lazy-lock.json` is unchanged.
- After Codex hands off, on the user's machine: restart `nvim` twice,
  inspect `site/queries/`, open `.json`/`.yaml`/`.py`, and run `:Inspect`.
- Do not commit. Leave the change in the working tree for the user.

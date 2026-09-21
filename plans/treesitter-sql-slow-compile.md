# Stop nvim-treesitter from recompiling slow grammars (SQL) on every startup

## Goal

Eliminate the long `[nvim-treesitter/install/sql]: compiling parser…` wait on
Neovim startup. The fix is to relink missing query directories directly
(symlink only) instead of going through the full `install(force=true)`
pipeline, which re-downloads the tarball and re-runs `tree-sitter build` —
several minutes for the SQL grammar.

Out of scope:

- Removing `sql` from the parser list.
- Switching to a different SQL grammar fork or pinning a different revision.
- Adding `require("nvim-treesitter").setup({...})`.
- Changing `branch = "main"`, `lazy = false`, `build = ":TSUpdate"`.
- The parser list, the `bash → zsh` registration, `indentexpr`, the
  `FileType` autocmd, or the `fts_from_parsers` derivation.
- `nvim/lua/plugins/lsp.lua`, `nvim/init.lua`, `install.sh`, `lazy-lock.json`.
- Hooking into `:TSUpdate` / build flags / compiler env vars.

## Current behavior

`nvim/lua/plugins/treesitter.lua` (config closure):

1. Reads `installed = require("nvim-treesitter.config").get_installed()`.
   This returns the **union** of `parser/` and `queries/` directory entries
   under `~/.local/share/nvim/site/`, so a language counts as "installed" if
   *either* `<lang>.so` *or* `queries/<lang>` exists.
2. Splits the configured `parsers` list into two buckets:
   - `to_install` — language not in `installed_set` → `ts.install(to_install)`.
   - `to_relink` — language present but `site/queries/<lang>` missing →
     `ts.install(to_relink, { force = true })`.
3. `ts.install(..., { force = true })` runs `install_lang(..., force=true)`,
   which runs the full pipeline in
   `~/.local/share/nvim/lazy/nvim-treesitter/lua/nvim-treesitter/install.lua`:
   `do_download` (curl tarball) → `do_compile` (`tree-sitter build -o
   parser.so`) → `do_install` (copy `.so`) → `do_link_queries` (`symlink
   runtime/queries/<lang> → site/queries/<lang>`).
4. There is no public API that runs only the query-link step. `force = true`
   re-runs the compile every time.

Observed user state (as of this plan):

- `~/.local/share/nvim/site/parser/sql.so` exists, 11 MB, mtime 2026‑04‑04.
- `~/.local/share/nvim/site/queries/` contains only `ecma`, `html_tags`, `jsx`
  symlinks. **No `sql`, no `go`, no `python`, etc.** — the previous relink path
  has not yet successfully created them, or it did but a later partial state
  rolled them back.
- `~/.local/share/nvim/lazy/nvim-treesitter/runtime/queries/<lang>/` exists
  and contains the expected `.scm` files for every language in `parsers`
  (verified for `sql`, `go`, `python`).
- `parsers.lua` declares `sql` with
  `url = https://github.com/derekstride/tree-sitter-sql`,
  `branch = gh-pages`,
  `revision = 851e9cb257ba7c66cc8c14214a31c44d2f1e954e`.
  This grammar's `parser.c` is multi-megabyte; `tree-sitter build` shells out
  to the system compiler at default optimisation, taking minutes per run.

Consequence: every Neovim launch puts `sql` (and every other
queries‑missing language) back into `to_relink`, which forces a full SQL
recompile each time. User-visible symptom: a stuck/very long
`[nvim-treesitter/install/sql]: compiling parser` message at startup.

## Target behavior

- On startup, missing query directories are restored by creating a symlink
  `~/.local/share/nvim/lazy/nvim-treesitter/runtime/queries/<lang>` →
  `~/.local/share/nvim/site/queries/<lang>` directly, with no compile or
  download step. This is exactly what `do_link_queries` already does
  internally.
- `tree-sitter build` is invoked only when the parser `.so` is genuinely
  missing (i.e. cold install via the `to_install` path), not on the relink
  path.
- After one Neovim start on the user's broken-state machine, `site/queries/`
  contains symlinks for every entry in `parsers`. SQL parsing keeps working
  (the existing `.so` is unchanged). Subsequent starts are immediate — no
  install jobs, no compiler invocation.
- Behaviour preserved for the cold-install case (fresh machine): the
  `to_install` branch still calls `ts.install(to_install)`, which downloads,
  compiles, and links queries the normal way (SQL is unavoidably slow on
  first install, but it is a one-time cost handled by `build = ":TSUpdate"`
  and the async install).
- If for some language `runtime/queries/<lang>` does not exist (the parser
  ships its own queries inside its repo), the language falls back to the
  current behaviour: forced reinstall. This keeps correctness for the rare
  in-repo-queries case while making the common case fast.

## Files

- `nvim/lua/plugins/treesitter.lua` — **edit**. Replace the
  `ts.install(to_relink, { force = true })` branch with a direct
  `vim.uv.fs_symlink` of the runtime queries dir, with a fallback that
  punts back to the install pipeline only when `runtime/queries/<lang>` is
  missing on the plugin side. Add one comment line explaining *why*
  (avoiding SQL recompile).
- `nvim/init.lua` — **read only**, do not modify.
- `nvim/lua/plugins/lsp.lua` — **untouched**.
- `nvim/lazy-lock.json` — **untouched**.
- `install.sh` — **untouched**.
- `plans/treesitter-highlighting.md` — **untouched**. This plan supersedes
  the relink branch of that earlier plan but the earlier plan stays as
  historical context.

## Constraints

- Do not remove or reorder entries in the `parsers` list.
- Do not change `branch = "main"`, `lazy = false`, or `build = ":TSUpdate"`.
- Do not add `require("nvim-treesitter").setup({...})`. The default
  `install_dir` (`stdpath("data") .. "/site"`) is what every path in this
  plan assumes.
- Do not touch `vim.treesitter.language.register("bash", "zsh")`, the
  `fts_from_parsers` table, the `fts` derivation loop, or the `FileType`
  autocmd body (including `pcall(vim.treesitter.start, args.buf)` and the
  `indentexpr` line).
- Do not introduce `vim.wait(...)` or any other synchronous bootstrap.
- Do not add new plugin dependencies.
- Do not modify nvim-treesitter sources under `~/.local/share/nvim/lazy/` —
  it is generated/managed by lazy.nvim.
- Code style: 4-space indent (12-space for code inside the `config` closure
  to match the surrounding block), English-only comments, no emojis,
  comments only for the *why*.
- Use `vim.uv` with a `vim.loop` fallback for symmetry with the existing
  code in the same file and `init.lua`.
- Resolve the source path via
  `require("nvim-treesitter.install").get_package_path("runtime", "queries", lang)`
  rather than hard-coding `stdpath("data") .. "/lazy/nvim-treesitter/..."` —
  it is the same exported helper `try_install_lang` uses and keeps us robust
  if the plugin is ever loaded from a non-lazy path.
- Mirror nvim-treesitter's own symlink call exactly:
  `{ dir = true, junction = true }` (junction is Windows-only but harmless
  on Unix and matches `do_link_queries` for cross-platform symmetry).
- Keep the `to_install` branch identical to today.

## Implementation steps

1. Open `nvim/lua/plugins/treesitter.lua`.

2. Locate the block (lines ~22–40 in the current file):

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

3. Replace it verbatim with (same 12-space indentation as the surrounding
   `config` function body):

   ```lua
   local ts = require("nvim-treesitter")
   local ts_install = require("nvim-treesitter.install")
   local installed = require("nvim-treesitter.config").get_installed()
   local installed_set = {}
   for _, lang in ipairs(installed) do installed_set[lang] = true end

   local uv = vim.uv or vim.loop
   local query_root = vim.fn.stdpath("data") .. "/site/queries/"
   local to_install = {}
   for _, p in ipairs(parsers) do
       if not installed_set[p] then
           to_install[#to_install + 1] = p
       elseif not uv.fs_stat(query_root .. p) then
           -- Parser .so is present but the runtime queries dir was never
           -- symlinked (e.g. interrupted install). Relink directly instead
           -- of calling install(force=true): a forced reinstall re-runs
           -- tree-sitter build, which for large grammars like SQL takes
           -- several minutes on every startup.
           local src = ts_install.get_package_path("runtime", "queries", p)
           if uv.fs_stat(src) then
               pcall(uv.fs_symlink, src, query_root .. p, { dir = true, junction = true })
           else
               -- Queries shipped inside the parser repo, not in runtime/queries.
               -- Fall back to the install pipeline to fetch and copy them.
               to_install[#to_install + 1] = p
           end
       end
   end

   if #to_install > 0 then ts.install(to_install) end
   ```

4. Do not modify any other line in the file. The `parsers` list, the
   `vim.treesitter.language.register("bash", "zsh")` call, the
   `fts_from_parsers` table, the `fts` derivation loop, and the `FileType`
   autocmd stay exactly as they are.

5. Do not edit any other file.

## Tests

Automated (must pass before handoff):

- `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p` — Lua parse check
  per `AGENTS.md`. Must exit 0.
- `find nvim karabiner -name '*.json' -print0 | xargs -0 -n1 jq empty` —
  unrelated JSON sanity, cheap, should exit 0. *Needs verification* on this
  machine.
- `bash -n install.sh` and `zsh -n zsh/.zshrc zsh/aliases.zsh` — also from
  `AGENTS.md`; expected to exit 0 since neither file is touched. *Needs
  verification.*

Manual (cannot be automated):

1. Start `nvim` once on the user's machine.
   - Expect: **no** `[nvim-treesitter/install/sql]: compiling parser` message.
     The relink path runs synchronously and completes instantly.
   - Acceptable: a fast `[nvim-treesitter/install/<lang>]: …` burst for any
     language whose parser is genuinely missing.
2. Quit and start `nvim` again.
   - `:lua print(vim.inspect(vim.fn.readdir(vim.fn.stdpath("data") .. "/site/queries")))`
     should list every entry in the `parsers` table (plus the pre-existing
     `ecma`, `html_tags`, `jsx`).
   - `ls -la ~/.local/share/nvim/site/queries/sql` — symlink pointing into
     `~/.local/share/nvim/lazy/nvim-treesitter/runtime/queries/sql`.
3. Open a `.sql`, `.json`, `.yaml`, and `.py` file. Expect coloured tokens.
   `:Inspect` on a token shows a `@…` capture in the Treesitter section.
4. `:checkhealth nvim-treesitter` — no errors for any language in `parsers`.
5. `time nvim --headless +q` — should return in well under a second; before
   the fix, the same command on the broken-state machine blocks on SQL.
   *Approximate; not a strict pass/fail.*

## Edge cases

- **Cold-cache user (parser .so missing).** `to_install` fires, normal
  install path runs. SQL still compiles slowly the first time; that is
  unavoidable and matches today's behaviour.
- **Current broken state (sql.so present, queries/sql missing).** New
  symlink branch fires, no compile. Fixes the reported symptom.
- **Parser-only languages with in-repo queries.** If a future entry in
  `parsers` ships queries inside its own repo (i.e. there is no
  `runtime/queries/<lang>` directory in the nvim-treesitter checkout), the
  `uv.fs_stat(src)` check fails and we fall back to adding the language to
  `to_install` — which runs `ts.install(...)` *without* `force=true`. Since
  the parser is already in `installed_set`, `install_lang` short-circuits at
  `vim.list_contains(config.get_installed(), lang)` and does **nothing**, so
  the queries will not be linked. For the current `parsers` list this case
  does not arise (runtime/queries/{sql,go,python,…} all exist), but flag it
  in review and re-evaluate if the list grows. A future, stricter fix would
  call `ts.install({lang}, { force = true })` only in this fallback — left
  as-is here to keep the diff minimal.
- **Symlink already exists.** Not expected (we only enter the branch when
  `uv.fs_stat` returned nil), but `pcall` swallows any `EEXIST`. The
  surrounding loop continues for other languages.
- **`site/queries/` does not exist at all.** Cannot happen on the user's
  machine (verified). On a brand-new machine `to_install` fires first; the
  install pipeline calls `config.get_install_dir('queries')` which creates
  the directory before any symlinks are attempted, so by the time the relink
  branch runs the dir already exists.
- **Cross-platform: Windows.** `{ dir = true, junction = true }` mirrors
  `do_link_queries`. Not used by this user, but kept for symmetry.
- **`vim.uv` vs `vim.loop`.** Repo targets Neovim ≥ 0.11 (`vim.uv` always
  present) but `(vim.uv or vim.loop)` matches existing usage in this file
  and the bootstrap in `nvim/init.lua`.
- **Parser version drift.** Not handled here. Updating revisions and
  recompiling SQL on a real version bump is `:TSUpdate`'s job and runs via
  the `build` hook on demand, not on every startup.
- **Network outage on first launch.** Async `install()` fails silently;
  affected languages have no highlighting until the user retries. Matches
  today's behaviour.

## Acceptance criteria

- [ ] `git diff -- nvim/lua/plugins/treesitter.lua` shows only the
      replacement of the relink block described in steps 2–3. No other
      hunks in this file. No other files in `git status`/`git diff` as a
      result of this task.
- [ ] `find nvim -name '*.lua' -print0 | xargs -0 -n1 luac -p` exits 0.
- [ ] After one launch on the broken-state machine, no
      `[nvim-treesitter/install/sql]: compiling parser` message appears.
- [ ] `~/.local/share/nvim/site/queries/sql` is a symlink to
      `~/.local/share/nvim/lazy/nvim-treesitter/runtime/queries/sql` and the
      same holds for every other entry in `parsers` that was previously
      missing.
- [ ] `.sql`, `.json`, `.yaml`, `.py` buffers render with tree-sitter
      colours; `:Inspect` shows treesitter captures.
- [ ] `branch = "main"`, `lazy = false`, `build = ":TSUpdate"` preserved.
- [ ] `parsers` list, `bash → zsh` registration, `fts_from_parsers`, FileType
      autocmd body all unchanged.
- [ ] No `setup({...})`, no `vim.wait(...)`, no new dependencies, no new
      requires beyond `require("nvim-treesitter.install")`.

## Review notes

- Confirm the diff is scoped exactly to the relink block in
  `nvim/lua/plugins/treesitter.lua`.
- Confirm `ts_install.get_package_path(...)` is used (not a hard-coded path).
- Confirm `pcall(uv.fs_symlink, …)` is wrapped in `pcall` — `fs_symlink`
  returns an error string rather than raising, but `pcall` is the existing
  defensive style and keeps a stray EEXIST from breaking the loop.
- Confirm `{ dir = true, junction = true }` matches `do_link_queries` in
  `~/.local/share/nvim/lazy/nvim-treesitter/lua/nvim-treesitter/install.lua`.
- Confirm `pcall(vim.treesitter.start, args.buf)` in the `FileType` autocmd
  is still in place — do not let the implementer "improve" it.
- Confirm `vim.treesitter.language.register("bash", "zsh")` is still
  present and unchanged.
- Confirm the comment added explains *why* (avoiding SQL recompile), not
  *what*.
- Confirm `nvim/lazy-lock.json` is unchanged.
- Confirm `nvim/lua/plugins/lsp.lua` is unchanged (its dirty hunks are
  unrelated and must be preserved).
- After Codex hands off, on the user's machine: one `nvim` start, then
  `ls -la ~/.local/share/nvim/site/queries/`, then open a `.sql` file and
  run `:Inspect`. Do not commit.

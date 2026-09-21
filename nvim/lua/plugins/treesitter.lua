return {
    {
        "nvim-treesitter/nvim-treesitter",
        branch = "main",
        lazy = false,
        build = ":TSUpdate",
        config = function()
            local parsers = {
                "go", "gomod", "gosum",
                "python",
                "lua",
                "javascript", "typescript",
                "json", "yaml", "toml",
                "html", "css",
                "bash",
                "markdown", "markdown_inline",
                "dockerfile",
                "sql",
                "vim", "vimdoc",
            }

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

            vim.treesitter.language.register("bash", "zsh")

            local fts_from_parsers = {
                go = "go", gomod = "gomod", gosum = "gosum",
                python = "python",
                lua = "lua",
                javascript = "javascript", typescript = "typescript",
                json = "json", yaml = "yaml", toml = "toml",
                html = "html", css = "css",
                bash = { "bash", "sh", "zsh" },
                markdown = { "markdown" }, markdown_inline = {},
                dockerfile = "dockerfile",
                sql = "sql",
                vim = "vim", vimdoc = "help",
            }

            local fts = {}
            for _, p in ipairs(parsers) do
                local ft = fts_from_parsers[p]
                if type(ft) == "string" then
                    fts[#fts + 1] = ft
                elseif type(ft) == "table" then
                    for _, f in ipairs(ft) do
                        fts[#fts + 1] = f
                    end
                end
            end

            vim.api.nvim_create_autocmd("FileType", {
                pattern = fts,
                callback = function(args)
                    pcall(vim.treesitter.start, args.buf)
                    vim.bo[args.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
                end,
            })
        end,
    },
}

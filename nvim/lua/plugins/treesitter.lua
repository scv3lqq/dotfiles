return {
    {
        "nvim-treesitter/nvim-treesitter",
        build = ":TSUpdate",
        config = function()
            local langs = {
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

            require("nvim-treesitter.install").install(langs)

            vim.api.nvim_create_autocmd("FileType", {
                callback = function(args)
                    local ok = pcall(vim.treesitter.start, args.buf)
                    if ok then
                        vim.bo[args.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
                    end
                end,
            })

            vim.treesitter.language.register("bash", "zsh")
        end,
    },
}

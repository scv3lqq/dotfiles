return {
    "nvim-treesitter/nvim-treesitter",
    tag = "v0.9.3",
    build = ":TSUpdate",
    config = function()
        require("nvim-treesitter.configs").setup({
            ensure_installed = {
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
            },
            highlight = { enable = true },
            indent = { enable = true },
            incremental_selection = {
                enable = true,
                keymaps = {
                    init_selection = "<C-space>",
                    node_incremental = "<C-space>",
                    scope_incremental = false,
                    node_decremental = "<bs>",
                },
            },
        })
        vim.treesitter.language.register("bash", "zsh")
    end,
}

return {
    {
        "ray-x/go.nvim",
        dependencies = {
            "ray-x/guihua.lua",
            "neovim/nvim-lspconfig",
            "nvim-treesitter/nvim-treesitter",
        },
        ft = { "go", "gomod", "gosum", "gotmpl" },
        build = ':lua require("go.install").update_all_sync()',
        config = function()
            require("go").setup({
                -- LSP managed by mason-lspconfig, don't let go.nvim touch it
                lsp_cfg = false,
                lsp_on_attach = false,
                -- DAP managed by nvim-dap-go
                dap_debug = false,
                -- Formatting managed by gopls (gofumpt) + conform
                lsp_document_formatting = false,
                lsp_inlay_hints = { enable = false },
                -- Keep go.nvim's code lens off (gopls handles it)
                lsp_codelens = false,
            })
        end,
    },
    {
        "ray-x/guihua.lua",
        build = "cd lua/fzy && make",
    },
}

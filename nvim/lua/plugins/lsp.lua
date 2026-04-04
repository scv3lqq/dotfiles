return {
    {
        "mason-org/mason.nvim",
        config = function() require("mason").setup() end,
    },
    {
        "mason-org/mason-lspconfig.nvim",
        dependencies = { "mason-org/mason.nvim", "neovim/nvim-lspconfig" },
        config = function()
            require("mason-lspconfig").setup({
                ensure_installed = { "gopls", "basedpyright", "ruff", "lua_ls" },
                automatic_enable = true,
            })
        end,
    },
    {
        "neovim/nvim-lspconfig",
        dependencies = { "saghen/blink.cmp" },
        config = function()
            local capabilities = require("blink.cmp").get_lsp_capabilities()

            -- Apply capabilities to all servers
            vim.lsp.config("*", { capabilities = capabilities })

            -- Server-specific settings
            vim.lsp.config("gopls", {
                settings = {
                    gopls = {
                        analyses = { unusedparams = true },
                        staticcheck = true,
                        gofumpt = true,
                        usePlaceholders = false,
                        completeUnimported = true,
                    },
                },
            })

            vim.lsp.config("basedpyright", {
                settings = {
                    basedpyright = {
                        analysis = {
                            autoSearchPaths = true,
                            useLibraryCodeForTypes = true,
                        },
                    },
                },
            })

            vim.lsp.config("lua_ls", {
                settings = {
                    Lua = { diagnostics = { globals = { "vim" } } },
                },
            })

            vim.api.nvim_create_autocmd("LspAttach", {
                callback = function(event)
                    local map = function(keys, func, desc)
                        vim.keymap.set("n", keys, func, { buffer = event.buf, desc = desc })
                    end
                    map("gd", vim.lsp.buf.definition, "Go to definition")
                    map("gr", vim.lsp.buf.references, "References")
                    map("gi", vim.lsp.buf.implementation, "Implementation")
                    map("gt", vim.lsp.buf.type_definition, "Type definition")
                    map("K", vim.lsp.buf.hover, "Hover docs")
                    map("<leader>rn", vim.lsp.buf.rename, "Rename")
                    map("<leader>ca", vim.lsp.buf.code_action, "Code action")
                    map("<leader>e", vim.diagnostic.open_float, "Show diagnostic")
                    map("]d", vim.diagnostic.goto_next, "Next diagnostic")
                    map("[d", vim.diagnostic.goto_prev, "Prev diagnostic")
                end,
            })
        end,
    },
    {
        "stevearc/conform.nvim",
        config = function()
            require("conform").setup({
                formatters_by_ft = {
                    go = { "gofumpt" },
                    python = { "ruff_organize_imports", "ruff_format" },
                    lua = { "stylua" },
                },
                format_on_save = function(bufnr)
                    local ft = vim.bo[bufnr].filetype
                    if ft == "go" then return nil end
                    return { timeout_ms = 1000, lsp_fallback = false }
                end,
            })
            vim.keymap.set("n", "<leader>fo", function()
                require("conform").format({ async = true })
            end, { desc = "Format" })
        end,
    },
}

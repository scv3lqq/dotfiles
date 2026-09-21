return {
    {
        "iamcco/markdown-preview.nvim",
        cmd = { "MarkdownPreview", "MarkdownPreviewStop", "MarkdownPreviewToggle" },
        ft = { "markdown" },
        build = "cd app && yarn install",
        init = function()
            vim.g.mkdp_filetypes = { "markdown" }
            vim.g.mkdp_auto_close = 1
            vim.g.mkdp_theme = "dark"
        end,
        keys = {
            {
                "<leader>cp",
                "<cmd>MarkdownPreviewToggle<cr>",
                desc = "Toggle markdown preview",
                ft = "markdown",
            },
        },
    },
}

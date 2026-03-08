return {
    {
        "nvim-lualine/lualine.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        opts = {
            options = {
                theme = "gruvbox",
                component_separators = { left = "", right = "" },
                section_separators = { left = "", right = "" },
            },
        },
    },
    {
        "folke/which-key.nvim",
        event = "VeryLazy",
        config = function()
            local wk = require("which-key")
            wk.setup()
            wk.add({
                { "<leader>f", group = "Find" },
                { "<leader>h", group = "Git hunk" },
                { "<leader>d", group = "Debug" },
                { "<leader>x", group = "Trouble" },
                { "<leader>o", group = "Obsidian" },
                { "<leader>r", group = "Refactor" },
                { "<leader>c", group = "Code" },
            })
        end,
    },
    {
        "lukas-reineke/indent-blankline.nvim",
        main = "ibl",
        opts = {
            indent = { char = "│" },
            scope = { enabled = true },
        },
    },
    {
        "windwp/nvim-autopairs",
        event = "InsertEnter",
        opts = {},
    },
    {
        "numToStr/Comment.nvim",
        opts = {},
    },
}

return {
    {
        "folke/todo-comments.nvim",
        dependencies = { "nvim-lua/plenary.nvim" },
        config = function()
            require("todo-comments").setup()
            vim.keymap.set("n", "<leader>ft", "<cmd>TodoTelescope<CR>", { desc = "Find TODOs" })
            vim.keymap.set("n", "]t", function() require("todo-comments").jump_next() end, { desc = "Next TODO" })
            vim.keymap.set("n", "[t", function() require("todo-comments").jump_prev() end, { desc = "Prev TODO" })
        end,
    },
    {
        "folke/trouble.nvim",
        dependencies = { "nvim-tree/nvim-web-devicons" },
        config = function()
            require("trouble").setup()
            vim.keymap.set("n", "<leader>xx", "<cmd>Trouble diagnostics toggle<CR>", { desc = "Diagnostics" })
            vim.keymap.set("n", "<leader>xd", "<cmd>Trouble diagnostics toggle filter.buf=0<CR>", { desc = "Buffer diagnostics" })
            vim.keymap.set("n", "<leader>xt", "<cmd>Trouble todo toggle<CR>", { desc = "TODOs" })
            vim.keymap.set("n", "<leader>xs", "<cmd>Trouble symbols toggle<CR>", { desc = "Symbols" })
        end,
    },
}

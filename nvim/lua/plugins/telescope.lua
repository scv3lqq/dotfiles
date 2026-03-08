return {
    "nvim-telescope/telescope.nvim",
    branch = "0.1.x",
    dependencies = {
        "nvim-lua/plenary.nvim",
        { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
    },
    config = function()
        local telescope = require("telescope")
        telescope.setup({
            defaults = {
                layout_strategy = "horizontal",
                sorting_strategy = "ascending",
                layout_config = { prompt_position = "top" },
                preview = {
                    treesitter = false,
                },
            },
        })
        telescope.load_extension("fzf")

        local builtin = require("telescope.builtin")
        vim.keymap.set("n", "<leader>ff", builtin.find_files, { desc = "Find files" })
        vim.keymap.set("n", "<leader>fg", builtin.live_grep, { desc = "Live grep" })
        vim.keymap.set("n", "<leader>fb", builtin.buffers, { desc = "Buffers" })
        vim.keymap.set("n", "<leader>fh", builtin.help_tags, { desc = "Help" })
        vim.keymap.set("n", "<leader>fr", builtin.oldfiles, { desc = "Recent files" })
        vim.keymap.set("n", "<leader>fd", builtin.diagnostics, { desc = "Diagnostics" })
        vim.keymap.set("n", "<leader>fs", builtin.lsp_document_symbols, { desc = "Symbols" })
        vim.keymap.set("n", "<C-p>", builtin.buffers, { desc = "Buffers" })
    end,
}

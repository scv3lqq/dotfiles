return {
    {
        "Pocco81/auto-save.nvim",
        event = { "InsertLeave", "TextChanged" },
        opts = { debounce_delay = 1000 },
    },
    {
        "rmagatti/auto-session",
        config = function()
            require("auto-session").setup({
                suppressed_dirs = { "~/", "~/Downloads", "/" },
            })
        end,
    },
}

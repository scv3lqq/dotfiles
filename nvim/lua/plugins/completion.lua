return {
    "saghen/blink.cmp",
    version = "1.*",
    dependencies = { "rafamadriz/friendly-snippets" },
    opts = {
        keymap = {
            preset = "default",
            ["<Tab>"] = { "accept", "fallback" },
            ["<C-y>"] = {},
        },
        appearance = { nerd_font_variant = "mono" },
        sources = {
            default = { "lsp", "path", "snippets", "buffer" },
        },
        completion = {
            accept = { auto_brackets = { enabled = true } },
            documentation = {
                auto_show = true,
                auto_show_delay_ms = 100,
            },
        },
    },
}

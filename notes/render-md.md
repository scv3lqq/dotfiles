# render-markdown.nvim

Плагин для красивого рендера Markdown прямо в буфере Neovim.

Репозиторий: <https://github.com/meanderingprogrammer/render-markdown.nvim>

## Установка

Конфиг лежит в `nvim/lua/plugins/render-markdown.lua`:

```lua
return {
    {
        "MeanderingProgrammer/render-markdown.nvim",
        dependencies = {
            "nvim-treesitter/nvim-treesitter",
            "nvim-tree/nvim-web-devicons",
        },
        ft = { "markdown" },
        opts = {
            file_types = { "markdown" },
            render_modes = { "n", "c", "t" },
            completions = { lsp = { enabled = true } },
        },
        keys = {
            { "<leader>cm", "<cmd>RenderMarkdown buf_toggle<cr>", desc = "Toggle markdown render" },
        },
    },
}
```

При первом запуске `nvim` lazy.nvim сам подтянет плагин. Принудительно — `:Lazy sync`.

## Активация

Плагин подключается лениво, при открытии любого `*.md` файла. Рендеринг включается сразу.

## Что рендерится из коробки

- Заголовки `#`, `##` — цветные иконки и фоны вместо `#`-ов
- Списки `-`, `*` — красивые буллеты
- Чекбоксы `- [ ]` / `- [x]` — иконки
- Блоки кода с подсветкой языка — цветной фон + иконка
- Таблицы — рамки красивее
- Цитаты `>`, ссылки, `inline code`, разделители `---`

## Режимы

Рендер видно в **normal / command / terminal**. Как только переходишь в **insert** — Markdown «разворачивается» в сырой текст, можно править. Вышел из insert → опять красиво.

Поведение задаётся опцией `render_modes`:

```lua
render_modes = { "n", "c", "t" }  -- по умолчанию
```

Если хочешь рендер во всех режимах (включая insert) — добавь `"i"` или используй пресет `obsidian`:

```lua
opts = { preset = "obsidian" }
```

## Команды

После `:RenderMarkdown <Tab>` есть таб-комплит.

| Команда | Что делает |
|---|---|
| `:RenderMarkdown enable` | Включить глобально |
| `:RenderMarkdown disable` | Выключить глобально |
| `:RenderMarkdown toggle` | Переключить глобально |
| `:RenderMarkdown buf_enable` | Включить в текущем буфере |
| `:RenderMarkdown buf_disable` | Выключить в текущем буфере |
| `:RenderMarkdown buf_toggle` | Переключить в текущем буфере |
| `:RenderMarkdown preview` | Открыть side-by-side preview |
| `:RenderMarkdown expand` | Расширить anti-conceal margin у курсора |
| `:RenderMarkdown contract` | Сузить anti-conceal margin |
| `:RenderMarkdown log` | Открыть лог-файл |
| `:RenderMarkdown debug` | Показать extmarks на текущей строке |
| `:RenderMarkdown config` | Показать diff от дефолтов |

## Кейбинды

- `<leader>cm` — `:RenderMarkdown buf_toggle` (группа `<leader>c` уже в which-key)

## Полезные пресеты

```lua
-- Рендер во всех режимах (как Obsidian)
opts = { preset = "obsidian" }

-- Как в LazyVim: code blocks по ширине блока, без иконок у заголовков
opts = { preset = "lazy" }
```

## Требования

- Neovim ≥ 0.10
- Парсеры treesitter: `markdown` и `markdown_inline` — уже включены в `nvim/lua/plugins/treesitter.lua`
- Шрифт с иконками (Nerd Font) — нужен для красивых символов

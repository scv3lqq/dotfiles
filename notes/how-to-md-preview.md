# markdown-preview.nvim

Плагин для live-preview Markdown в браузере. В отличие от `render-markdown.nvim`
(который рисует в самом буфере), этот открывает отдельную вкладку браузера и
синхронно скроллит / обновляет её при правках.

Репозиторий: <https://github.com/iamcco/markdown-preview.nvim>

## Установка

Конфиг лежит в `nvim/lua/plugins/markdown-preview.lua`:

```lua
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
```

При первом запуске `nvim` lazy.nvim подтянет плагин и выполнит `build` —
`yarn install` в каталоге `app/` соберёт Node-зависимости для встроенного
сервера превью. Сервер потом стартует из `app/server.js`.

> На arm64 macOS вариант с `mkdp#util#install()` (скачка готового бинаря) часто
> не работает — поэтому собираем из исходников. Нужен установленный `node` и `yarn`.

Принудительно: `:Lazy build markdown-preview.nvim` или `:Lazy sync`.

## Использование

1. Открой любой `*.md` файл (плагин подключается лениво по filetype).
2. `<leader>cp` (или `:MarkdownPreviewToggle`) — откроется вкладка в браузере по
   умолчанию с превью текущего буфера.
3. Редактируй файл в Neovim — превью обновляется в реальном времени, скролл
   синхронизирован.
4. `<leader>cp` ещё раз — закрыть превью.

## Команды

| Команда | Что делает |
|---|---|
| `:MarkdownPreview` | Открыть превью в браузере |
| `:MarkdownPreviewStop` | Закрыть превью |
| `:MarkdownPreviewToggle` | Переключить |

## Кейбинды

- `<leader>cp` — `:MarkdownPreviewToggle` (только в `markdown` буферах,
  группа `<leader>c` уже зарегистрирована в which-key как "Code").

## Полезные опции

Задаются через `vim.g.mkdp_*` в блоке `init`:

```lua
vim.g.mkdp_auto_start = 0          -- не открывать превью автоматом при входе в .md
vim.g.mkdp_auto_close = 1          -- закрывать вкладку при выходе из буфера
vim.g.mkdp_refresh_slow = 0        -- 1 = обновлять только при save/leave insert
vim.g.mkdp_open_to_the_world = 0   -- 1 = слушать на 0.0.0.0 (доступно по сети)
vim.g.mkdp_browser = ""            -- путь к конкретному браузеру, "" = системный
vim.g.mkdp_theme = "dark"          -- "dark" | "light"
vim.g.mkdp_port = ""               -- фиксированный порт (по умолчанию случайный)
vim.g.mkdp_filetypes = { "markdown" }
```

## render-markdown vs markdown-preview

- **render-markdown.nvim** — рендер прямо в буфере Neovim, без браузера.
  Удобно для быстрого чтения и работы вне GUI. См. `notes/render-md.md`.
- **markdown-preview.nvim** — настоящий HTML-рендер в браузере: картинки,
  KaTeX-формулы, mermaid-диаграммы, точный CSS. Удобно для финальной вычитки
  и презентации.

Они не конфликтуют — можно держать оба.

## Требования

- Neovim ≥ 0.8
- Браузер по умолчанию (открывается через `xdg-open` / `open`)
- `node` и `yarn` (`brew install node yarn`) — для сборки сервера превью

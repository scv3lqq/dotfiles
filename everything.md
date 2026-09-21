# Everything — справочник по dev-окружению

Полная сводка по стеку, инструментам и кеймапам. Источник правды — конфиги
в этом репозитории; этот файл — собранная и сгруппированная выжимка.

---

## 1. Стек

| Слой              | Инструмент                                |
| ----------------- | ----------------------------------------- |
| Терминал          | **Ghostty** (JetBrainsMono Nerd Font, 20) |
| Window manager    | **AeroSpace** (тайлинг, как i3)           |
| Keyboard remap    | **Karabiner-Elements**                    |
| Мультиплексор     | **tmux** (prefix `C-a`, gruvbox)          |
| Шелл              | **Zsh** (emacs-mode, fzf, autosuggestions)|
| Промпт            | **Starship**                              |
| Файл-менеджер     | **Yazi** (открытие в nvim по правилам)    |
| Редактор          | **Neovim** + lazy.nvim                    |
| Тема              | Gruvbox (soft contrast, transparent)      |

CLI-инструменты, на которые рассчитан конфиг:
`nvim · tmux · starship · fzf · fd · bat · eza · lazygit · lazydocker · yazi`.

---

## 2. Neovim — основа

Leader = **Space**, localleader = **Space**, режим вставки выход — **`jk`**.

### 2.1. Базовые кеймапы (init.lua)

| Кейс             | Действие                                       |
| ---------------- | ---------------------------------------------- |
| `<Esc>`          | Снять подсветку поиска                         |
| `jk` (insert)    | Выйти в normal mode                            |
| `;`              | Алиас `:` (без shift)                          |
| `J`/`K` (visual) | Двигать выделение вниз/вверх                   |
| `<C-d>`/`<C-u>`  | Скролл + центрирование                         |
| `n`/`N`          | Поиск + центрирование                          |
| `p` (visual)     | Paste без перезаписи реестра                   |
| `[d` / `]d`      | Предыдущий / следующий диагностик              |
| `<leader>e`      | Показать диагностик в плавающем окне           |
| `<leader>q`      | Диагностики в location list                    |

Опции: `relativenumber`, `cursorline`, `scrolloff=10`, `inccommand=split`,
`undofile`, системный буфер обмена (`unnamedplus`), 4 пробела отступ.

### 2.2. LSP (mason-lspconfig)

Авто-устанавливаются: `gopls`, `basedpyright`, `ruff`, `lua_ls`, `yamlls`.

| Кейс            | Действие                              |
| --------------- | ------------------------------------- |
| `gd`            | Перейти к определению                 |
| `gr`            | References                            |
| `gi`            | Implementation                        |
| `gt`            | Type definition                       |
| `K`             | Hover-документация                    |
| `<leader>rn`    | Rename символа                        |
| `<leader>ca`    | Code action                           |
| `<leader>e`     | Диагностик в окне                     |
| `[d` / `]d`     | Навигация по диагностикам             |

Серверные настройки:

- **gopls**: `unusedparams`, `staticcheck`, `gofumpt`, `completeUnimported`.
  На `BufWritePre` для `*.go` запускается `source.organizeImports`.
- **basedpyright**: `autoSearchPaths`, `useLibraryCodeForTypes`.
- **lua_ls**: глобал `vim` подсвечен.
- **yamlls**: подтянут SchemaStore (автосхемы по имени файла —
  `compose.yaml`, `.github/workflows/*`, k8s манифесты и т.д.).

### 2.3. Автодополнение — blink.cmp

| Кейс         | Действие                              |
| ------------ | ------------------------------------- |
| `<Tab>`      | Принять предложение / шаг сниппета    |
| `<S-Tab>`    | Назад в сниппете                      |
| `<C-y>`      | Отключён (был accept)                 |

Источники: `lsp`, `path`, `snippets`, `buffer`.
Авто-скобки включены. Документация подсказки появляется через 100 мс.

### 2.4. Форматирование — conform.nvim

| FileType   | Форматтер(ы)                              |
| ---------- | ----------------------------------------- |
| `python`   | `ruff_organize_imports` → `ruff_format`   |
| `lua`      | `stylua`                                  |
| `json`     | `prettier`                                |
| `jsonc`    | `prettier`                                |
| `yaml`     | `prettier`                                |
| `proto`    | `buf`                                     |
| `go`       | через LSP (`gopls`/`gofumpt`)             |

Хоткей: **`<leader>fo`** — отформатировать буфер (асинхронно).
Для Go форматирование идёт через `gofumpt` (gopls), организация импортов —
автоматом на сохранение.

### 2.5. Telescope

| Кейс         | Действие                |
| ------------ | ----------------------- |
| `<leader>ff` | Find files              |
| `<leader>fg` | Live grep               |
| `<leader>fb` | Buffers                 |
| `<leader>fh` | Help tags               |
| `<leader>fr` | Recent files            |
| `<leader>fd` | Diagnostics             |
| `<leader>fs` | LSP-символы документа   |
| `<leader>ft` | TODO/FIXME/NOTE         |
| `<C-p>`      | Buffers (быстро)        |

В подборщике: `<C-n>`/`<C-p>` или `<C-j>`/`<C-k>`, `<C-/>` — справка по
маппингам пикера, `<Tab>` — multi-select.

### 2.6. Файлы — Oil

`-` (минус) — открыть Oil в текущем каталоге. Внутри:
редактируешь буфер как обычный файл (`dd` удалить, `:w` применить), `g?` —
полная справка по Oil. Скрытые файлы показываются (`view_options.show_hidden`).

### 2.7. Git

**gitsigns** (привязки только в буфере):

| Кейс         | Действие              |
| ------------ | --------------------- |
| `]h` / `[h`  | След / пред hunk      |
| `<leader>hs` | Stage hunk            |
| `<leader>hr` | Reset hunk            |
| `<leader>hp` | Preview hunk          |
| `<leader>hb` | Blame строки          |

**lazygit**: `<leader>gg`.

### 2.8. Debug (DAP)

Поддержка: `nvim-dap-go`, `nvim-dap-python`.
Python берёт `.venv/bin/python` из cwd, иначе системный `python3`.

| Кейс         | Действие             |
| ------------ | -------------------- |
| `<leader>db` | Toggle breakpoint    |
| `<leader>dc` | Continue / start     |
| `<leader>di` | Step into            |
| `<leader>do` | Step over            |
| `<leader>dO` | Step out             |
| `<leader>dr` | Restart              |
| `<leader>dt` | Terminate            |
| `<leader>du` | Toggle DAP UI        |

UI открывается автоматически при старте сессии и закрывается на терминации.

### 2.9. Treesitter

Подсвечиваются и индентируются: Go (go/gomod/gosum), Python, Lua, JS/TS,
JSON/YAML/TOML, HTML/CSS, Bash (zsh маппится сюда), Markdown, Dockerfile,
SQL, vim/vimdoc.

Инкрементальное выделение: `<C-Space>` — увеличить, `<BS>` — уменьшить.

### 2.10. Trouble + TODO

| Кейс         | Действие                       |
| ------------ | ------------------------------ |
| `<leader>xx` | Все диагностики                |
| `<leader>xd` | Диагностики текущего буфера    |
| `<leader>xt` | TODO/FIXME-комментарии         |
| `<leader>xs` | LSP-символы                    |
| `]t` / `[t`  | Прыгать по TODO                |

### 2.11. Сессии и автосохранение

- **auto-save**: сохраняет при `InsertLeave` / `TextChanged` (debounce 1с).
- **auto-session**: сохраняет/восстанавливает сессии,
  кроме `~/`, `~/Downloads`, `/`.

### 2.12. Прочее в UI

- `mini.pairs` + `nvim-autopairs` — авто-парные скобки и кавычки.
- `Comment.nvim` — комментирование: `gcc` строка, `gc` в visual.
- `indent-blankline.nvim` — вертикальные палочки отступов с подсветкой scope.
- `which-key` — нажми `<leader>` и подожди: появится подсказка групп
  (`f` Find, `h` Git hunk, `d` Debug, `x` Trouble, `c` Code, ...).

### 2.13. Tmux navigator

`<C-h>` / `<C-j>` / `<C-k>` / `<C-l>` — переключение по сплитам Neovim **и**
панелям tmux одинаково. (Очистка экрана в tmux — `prefix C-l`.)

---

## 3. Сценарии по языкам

### 3.1. Go

- **LSP**: `gopls` (с `gofumpt`, `staticcheck`, `unusedparams`).
- **Импорты**: сами организуются на save.
- **Форматирование**: на save через LSP; ручной триггер — `<leader>fo`.
- **go.nvim** активен для `go/gomod/gosum/gotmpl` (тесты, codegen и т.д.) —
  команды через `:GoXxx`. LSP/DAP/форматирование у него отключены, чтобы
  не конфликтовать с mason/conform/dap-go.
- **Сниппеты**: `friendly-snippets` + локальные. Полная шпаргалка —
  `notes/go-snippets.md`. Локально добавлен `vv` → `name := value`
  (`nvim/snippets/go.json`).
- **Отладка**: `<leader>db` поставить точку → `<leader>dc` запустить.
  Под `go test` и `go run` есть готовые конфигурации в `nvim-dap-go`.
- **Авто-фикс отступов в switch/case**: в init.lua отключён `cindent`
  для `filetype=go`.

### 3.2. Python

- **LSP**: `basedpyright` (типы) + `ruff` (linter).
- **Форматирование**: `ruff_organize_imports` → `ruff_format`
  (хоткей `<leader>fo`).
- **Venv**: DAP автоматически подхватывает `./.venv/bin/python`.
  Полезно сразу делать `python -m venv .venv && source .venv/bin/activate`.
- **Отладка**: `<leader>db`/`<leader>dc`. Поддерживаются файлы, модули
  и pytest (через `nvim-dap-python`).

### 3.3. JSON / JSONC / YAML / TOML

- **JSON/JSONC**: `prettier` через `<leader>fo`.
- **YAML**: `yamlls` с SchemaStore — автосхема по имени файла
  (k8s, GitHub Actions, docker-compose, .gitlab-ci и т.д.).
  Форматирование — `prettier`.
- **TOML**: treesitter подсветка + индент (LSP не настроен; при желании
  добавить `taplo` в `ensure_installed`).
- Hover (`K`) показывает описание поля схемы — особенно полезно для k8s
  и GitHub Actions.

### 3.4. Proto

- Форматирование на `<leader>fo` через `buf`.
  Подсветка/LSP не настроены: при желании добавить `bufls` в mason.

### 3.5. Lua

- LSP: `lua_ls` (с глобалом `vim`).
- Форматирование: `stylua` (нужен бинарь в PATH).

---

## 4. Tmux

Prefix — **`Ctrl-a`**. Mouse on. История 50k. Vi mode в copy-режиме.

| Кейс                     | Действие                                  |
| ------------------------ | ----------------------------------------- |
| `prefix c`               | Новое окно в текущем каталоге             |
| `prefix \|`              | Сплит по вертикали в текущем каталоге     |
| `prefix -`               | Сплит по горизонтали                      |
| `prefix h/j/k/l` (repeat)| Изменить размер панели на 5               |
| `prefix m` (repeat)      | Zoom-toggle панели                        |
| `prefix r`               | Reload `~/.tmux.conf`                     |
| `prefix s`               | Список окон во всех сессиях через fzf,    |
|                          | `Ctrl-d` в попапе — kill сессии           |
| `prefix C-l`             | Очистить экран (т.к. `C-l` забран nvim)   |
| `v` / `y` (copy-mode-vi) | Начать выделение / yank в буфер           |

Плагины: tpm, vim-tmux-navigator, resurrect, continuum (restore off),
sessionist, **gruvbox dark**.

После первого запуска: `prefix + Shift+I` — установить плагины.

---

## 5. Zsh

- emacs-mode (`bindkey -e`), `↑/↓` — history substring search.
- История 50k, без дубликатов, шарится между сессиями.
- Включён `GLOB_DOTS` (`*` матчит скрытые), `AUTO_CD`.
- Подключаются `zsh-fast-syntax-highlighting`, `zsh-autosuggestions`,
  `zsh-completions`.
- `EDITOR=nvim`, `VISUAL=nvim`.

### 5.1. FZF (fzf —zsh интеграция)

| Кейс       | Действие                                       |
| ---------- | ---------------------------------------------- |
| `Ctrl-T`   | Вставить путь к файлу (fd, preview через bat)  |
| `Alt-C`    | `cd` в каталог (fd, preview через `eza --tree`)|
| `Ctrl-R`   | Поиск по истории команд                        |
| `**<Tab>`  | Fuzzy-complete для команд                      |

### 5.2. Алиасы

| Алиас  | Команда                                                    |
| ------ | ---------------------------------------------------------- |
| `n`    | `nvim`                                                     |
| `nf`   | `nvim $(fzf --preview "bat --color=always {}")`            |
| `ll`   | `ls -lah`                                                  |
| `la`   | `ls -A`                                                    |
| `..`   | `cd ..` (есть и `...`)                                     |
| `gst`  | `git status`                                               |
| `gp`   | `git push`                                                 |
| `gpl`  | `git pull`                                                 |
| `gl`   | Кастомный `git log` с графом                               |
| `gcof` | Чекаут ветки через fzf                                     |
| `lzd`  | `lazydocker`                                               |
| `fkill`| Убить процесс через fzf                                    |
| `md`   | `mkdir -p`                                                 |
| `tmux-reload` | Перезагрузить `.zshrc` во всех панелях tmux         |

### 5.3. Yazi-интеграция

Функция `y` (определена в `.zshrc`): открывает yazi, на выходе делает
`cd` в текущий каталог yazi. Запускай файл-менеджер как `y`, не `yazi`.

---

## 6. Yazi

Конфиг минимальный: `text/*`, `application/json|toml|yaml` открываются
в `nvim` (блокирующий вызов). Всё остальное — системным `open`.

Базовые кеймапы (стандарт yazi, не переопределены):

| Кейс           | Действие                              |
| -------------- | ------------------------------------- |
| `h/j/k/l`      | Навигация                             |
| `<Enter>`      | Открыть (по правилу из `yazi.toml`)   |
| `o`            | Open with… (выбрать опенер)           |
| `<Space>`      | Toggle select                         |
| `y` / `x` / `p`| Copy / cut / paste                    |
| `d` / `D`      | Trash / delete                        |
| `a`            | Создать файл/каталог                  |
| `r`            | Rename                                |
| `/` / `?`      | Поиск вперёд / назад                  |
| `g g` / `G`    | В начало / в конец                    |
| `q`            | Выход (с записью cwd для `y()`)       |
| `~`            | Help                                  |

---

## 7. AeroSpace (тайлинг)

| Кейс                       | Действие                                |
| -------------------------- | --------------------------------------- |
| `Alt + h/j/k/l`            | Фокус окна                              |
| `Alt + Shift + h/j/k/l`    | Передвинуть окно                        |
| `Alt + Shift + -/=`        | Resize -50 / +50 (smart)                |
| `Alt + /`                  | Tiles layout (toggle horiz/vert)        |
| `Alt + ,`                  | Accordion layout                        |
| `Alt + 1-9`                | Перейти на workspace                    |
| `Alt + w/t/s/m/o/g/p`      | Именованные workspaces                  |
| `Alt + Shift + <ws>`       | Перенести окно на workspace             |
| `Alt + Tab`                | Back-and-forth                          |
| `Alt + Shift + Tab`        | Перенести workspace на след. монитор    |
| `Alt + Enter`              | Открыть Ghostty                         |
| `Alt + b`                  | Открыть Vivaldi                         |
| `Alt + z`                  | Открыть Obsidian                        |
| `Alt + Shift + ;`          | Войти в **service mode**                |

Service mode (после `Alt+Shift+;`):

| Кейс       | Действие                                           |
| ---------- | -------------------------------------------------- |
| `esc`      | Reload config + выход                              |
| `r`        | Flatten workspace tree (сбросить раскладку)        |
| `f`        | Toggle floating/tiling                             |
| `<BS>`     | Закрыть все окна, кроме текущего                   |
| `Alt+Shift+h/j/k/l` | Join с соседним контейнером               |

Автораспределение по workspaces: Ghostty → `t`, Vivaldi → `w`,
Spotify → `s`, Telegram → `m`, Obsidian → `o`, Chrome → `g`.

---

## 8. Ghostty

- Шрифт: **JetBrainsMono Nerd Font** 20 pt.
- `macos-option-as-alt = true` — Alt-биндинги работают как ожидается.
- `copy-on-select = true` — выделение мышью сразу попадает в буфер.
- Скрытый titlebar, восстановление состояния окон.
- Тема: Alabaster Dark (фон `#0E1415`).

---

## 9. Шпаргалка `<leader>` (Neovim)

Группы (видно во `which-key`):

| Префикс       | Группа                              |
| ------------- | ----------------------------------- |
| `<leader>f`   | **Find** (Telescope, формат)        |
| `<leader>h`   | **Git hunk** (gitsigns)             |
| `<leader>d`   | **Debug** (DAP)                     |
| `<leader>x`   | **Trouble**                         |
| `<leader>g`   | Git (`gg` — LazyGit)                |
| `<leader>c`   | **Code** (`ca` — action)            |
| `<leader>r`   | **Refactor** (`rn` — rename)        |
| `<leader>o`   | Obsidian (плейсхолдер, плагин не подключён) |
| `<leader>e`   | Diagnostic float                    |
| `<leader>q`   | Diagnostic location list            |

Полная таблица всех биндингов разбита по разделам выше.

---

## 10. Замечания и потенциальные доработки

Что нашёл при ревью — на твоё усмотрение:

1. **`<leader>e` дублируется**: задан в `init.lua` и в `LspAttach`-колбэке
   (`nvim/lua/plugins/lsp.lua`). Делают одно и то же. Не баг, но лишняя строка.
2. **`<leader>o` группа во which-key** — заявлен Obsidian, но плагин не
   подключён. Либо ставь `obsidian.nvim`, либо убери группу.
3. **TOML**: треситтер есть, LSP нет. Если часто правишь `pyproject.toml`,
   добавь `taplo` в `ensure_installed` (`mason-lspconfig`).
4. **Markdown**: ни форматтера, ни LSP. Если нужно — `marksman` + `prettier`
   во ft `markdown` в conform.
5. **`gopls.local`** пустой. Если работаешь в монорепе со своими модулями,
   проставь префикс, чтобы импорты группировались правильно.
6. **`go.nvim build`** запускает `update_all_sync()` — может тормозить
   первый запуск nvim после переустановки.
7. **`continuum-restore 'off'`** — tmux не восстанавливает сессии сам;
   ручной `prefix + Ctrl-r` через resurrect.
8. **`<C-y>` в blink.cmp отключён** — если случайно жал accept мышью/коротко,
   теперь там «ничего». В норме accept = `<Tab>`.

---

## 11. Быстрый старт: «открыл проект и поехал»

```sh
cd ~/projects/my-go-app
y                       # ткнул в yazi, нашёл нужный файл, нажал Enter
                        # выпало в nvim в правильном каталоге
```

В nvim:

- `<leader>ff` — открыть нужный файл.
- `<leader>fg` — поискать по содержимому.
- Поправил → файл сохранится сам через 1с после остановки печати.
- `<leader>fo` — форматнуть вручную, если надо прямо сейчас.
- `gd` / `K` / `<leader>ca` — навигация и code action.
- `<leader>gg` — открыть LazyGit, закоммитить.
- `<leader>db` → `<leader>dc` — если нужно отладиться.

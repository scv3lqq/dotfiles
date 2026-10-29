---
name: telegram-theme
description: Build, tweak or debug the Telegram themes in ~/dotfiles/telegram/ (macOS app .palette, iOS .tgios-theme), colors from the Ghostty config. Use for «тема для Telegram», «поправь цвет в Telegram», a Telegram screenshot with a color or theme complaint, a theme not applying on the phone. Not for bots or the Bot API.
allowed-tools: Bash(python3:*), Read, Edit, Grep
---

# Telegram themes

`~/dotfiles/telegram/ayu-terminal-dark.{palette,tgios-theme}`: macOS app, iPhone.

## Sources

- macOS: `TelegramOrg/Telegram-macos-Swift` master `579cebb` (2025-07-29, older than the
  13.x app); `overtake/TelegramSwift` is 404. `Telegram-Mac/ParseAppearanceColors.swift`
  (`importPalette`), `packages/ColorPalette/Sources/ColorPalette/ColorPalette.swift` (keys,
  init clamps, `darkPalette`), `Telegram-Mac/Appearance.swift` (`generateTheme`: which key
  paints what), `packages/Colors/Sources/Colors/Colors.swift` (hex, `isTooCloseHSV`).
- iOS: `TelegramMessenger/Telegram-iOS` master `fb0e62b` (2026-10-22),
  `submodules/TelegramPresentationData/Sources/`: `PresentationThemeCoder.swift` (parser),
  `PresentationThemeCodable.swift` (keys, fallbacks), `DefaultDarkPresentationTheme.swift`;
  hex in `submodules/Display/Source/UIKitUtils.swift`; Apply in `submodules/SettingsUI/`.
  Code search misses the macOS repo: sparse-clone `'*.swift'` into the scratchpad.

## macOS .palette

- `key = value` lines split at the first `=`; `//` comment lines, no inline comments. Header:
  `name` (required), `isDark = 1`, `tinted = 0`, `parent = dark` (fallback for missing keys),
  `copyright`, `wallpaper` (`none`, `builtin`, `#rrggbb`, `t.me/bg/<slug>`).
- Colors `#rrggbb`, alpha `#rrggbb:0.6` (`#rrggbbaa` reads the last 6 digits); most alphas
  are clamped to >= 0.6; hex case does not matter (`Colors.swift:37`). 119 color keys plus
  `bubbleBackground_outgoing` (comma list, no spaces; one color is a flat bubble).
- The init swaps a text or icon color for black or white when its H+S+V sum is within 0.005
  of its background (the checker flags < 0.02). Selected chat text is white while
  `basicAccent == accent`; unread badge text is `background`; muted and tab badge text white.

## iOS .tgios-theme

- `key: value`, nesting by exactly 2 spaces; an odd or skipped indent makes the decoder
  return nil and the tap does nothing. `#` or `//` comment lines.
- Colors `rrggbb`, `aarrggbb` (alpha first) or `clear`; bools `true`/`false`; enums lowercase.
  Header: `name`, `basedOn: night` (default `classic`, a light theme), `dark: true`.
- A missing key takes the `basedOn` value, so set all 439: 463 decoder keys minus the
  optional bubble `bgList` (instead of `bg` + `gradientBg`) and `shadow` groups.
  `chat.defaultWallpaper: 0b0e14` is a plain color.

## Install

- macOS: click the Settings tab icon 5 times fast (`AccountViewController.swift:1262`), then
  Import Palette (`DeveloperViewController.swift:195,306-313`). Local only, and the palette's
  `wallpaper` is not applied: set the chat background to none by hand. Cloud variant:
  Appearance menu, New Theme, then Edit Theme > Create from File (`EditThemeController.swift:140`).
- iOS: send the file to Saved Messages, tap it (extension must be `.tgios-theme`,
  `GalleryData.swift:290`), then Apply in the preview (`ThemePreviewController.swift:268`).

## Platform facts that bit us

- Cloud themes are per platform (`TelegramCore/Sources/Themes.swift:6-12`, mime
  `application/x-tgtheme-macos` or `-ios`): a Mac theme never reaches the phone, ship both
  files. Local imports stay on that device; nothing syncs between devices.
- iOS Auto-Night active at Apply makes it the night theme (`ThemePreviewController.swift:391`),
  else dark mode can switch away: turn Auto-Night off or pick this theme there too.
- iOS Apply re-encodes, and the encoder drops `list.modalBlocksBg`, `modalPlainBg`,
  `itemModalBlocksBg`, `freePlainInputField`, `paymentOption`, `navBar.clearButton*`,
  `accentControlDisabled`, `contextMenu.badge*`, `extractedTint`: on reload they take decoder
  fallbacks, so keep them equal (the checker prints an info line per difference). Apply also
  clears the per-theme wallpaper (`:414`), so `defaultWallpaper` wins.
- macOS tab bar badge text is hardcoded white on `redUI` (`Appearance.swift:3480`): 2.86.

## Colors

- Ghostty `~/dotfiles/ghostty/ghostty/config`: `theme = Ayu`
  (`/Applications/Ghostty.app/Contents/Resources/ghostty/themes/Ayu`), overrides bg `#0B0E14`,
  fg `#E8E6DD`, `palette = 12=#D2A6FF`, cursor `#E6B450`. Accent `#D2A6FF` = starship git
  branch (`~/dotfiles/starship/starship.toml`). Amber is the macOS caret (`indicatorColor`)
  and iOS search highlight (`textHighlight: 66e6b450`). Making the accent amber (Zen's,
  `~/dotfiles/zen/user.js`): move those two off amber first (caret to text `#e8e6dd`, search
  highlight to `66d2a6ff`), or they merge with the accent and recolor warns on them.
- Roles: chat and list bg `#0b0e14`, chrome `#0f131a` (iOS bars at `f2` alpha), surfaces
  `#151a23` `#161b24` `#1c212b`, border `#1f242e`, text `#e8e6dd`, secondary `#8f8e89`,
  icons `#6c7380`, chip `#3a3f4b`, accent `#d2a6ff`, red `#f07178`, green `#aad94c`.
  A color change goes into both files, same role: grep the old hex in both.
- Accent tints, `% accent over base` (`scripts/tints.py show d2a6ff <files>` lists the keys):

  | tint | value | keys (macOS; iOS) |
  |---|---|---|
  | 14% over bg | `272335` | `bubbleBackground_outgoing`; outgoing `bg`, `gradientBg`, `mediaControlInnerBg` |
  | 22% over bg | `372f48` | `bubbleBorder_outgoing`; outgoing `stroke`, `reactionInactiveBg`, `mediaPlaceholder` |
  | 24% over bg | `3b324c` | `bubbleBackgroundHighlight_outgoing`; outgoing `highlightedBg` |
  | 25% over out | `524468` | `selectTextBubble_outgoing` |
  | 27% over gray | `a194a9` | `grayTextBubble_outgoing`; outgoing `secondaryText`, `file*` |
  | 29% over icon | `8a82a5` | `grayIconBubble_outgoing`; outgoing `polls.radioButton` |
  | 17% over chip | `54516a` | `waveformBackgroundBubble_outgoing`; outgoing `mediaInactiveControl` |
  | 16% over panel | `2e2b3f` | `accentSelect`; `itemSelectedBg`, `buttonHighlightedBg` |
  | 28% / 30% over panel | `463c5a` / `4a3f5f` | `selectText`, `selectTextBubble_incoming` / `focusAnimationColor` |
  | 7% over bg | `191924` | `selectMessage`, `selectMessageBubble` |

  iOS alpha tints (`4cd2a6ff`, `59d2a6ff`, ...) follow the accent hex. An accent change
  recomputes every tint: `scripts/tints.py recolor OLD NEW <both files>` (comments untouched),
  `mix ACCENT BASE PCT` for a single value.

## Verify

```sh
python3 -I ~/.claude/skills/telegram-theme/scripts/check_palette.py ~/dotfiles/telegram/ayu-terminal-dark.palette
python3 -I ~/.claude/skills/telegram-theme/scripts/check_ios_theme.py ~/dotfiles/telegram/ayu-terminal-dark.tgios-theme
```

PASS = keys, values, contrast >= 7 primary, >= 4.5 rest, >= 3 gray icons; the info lines
(tab badge 2.86, payment fg reverts) are expected. Telegram update: re-derive `COLOR_KEYS` /
`TREE`, bump the commit.

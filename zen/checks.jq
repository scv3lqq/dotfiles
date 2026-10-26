# Theme checks for the JSON written by zen/preview.py.
# Usage: jq -e -r -f zen/checks.jq out.json  (prints FAIL lines, exit 0 = all pass)
def c: .chrome;
def u: .urlbar;
def has_font: contains("JetBrainsMono Nerd Font");
[
  ["no_error", (.error == null)],
  ["own_pid_gone", (.meta.own_pid_gone == true)],
  ["user_zen_untouched", (.meta.foreign_zen_pids_before == .meta.foreign_zen_pids_after)],
  ["userchrome_loaded", ((.user_sheets // []) | any(endswith("/chrome/userChrome.css")))],
  ["pref_stylesheets", (.prefs["toolkit.legacyUserProfileCustomizations.stylesheets"] == true)],
  ["pref_scheme", (.prefs["zen.view.window.scheme"] == 0)],
  ["pref_accent", (.prefs["zen.theme.accent-color"] == "#E6B450")],
  ["pref_radius", (.prefs["zen.theme.border-radius"] == 0)],
  ["pref_separation", (.prefs["zen.theme.content-element-separation"] == 6)],
  ["pref_vibrancy", (.prefs["zen.widget.macos.window-vibrancy"] == false)],
  ["pref_essentials_bg", (.prefs["zen.theme.essentials-favicon-bg"] == false)],
  ["primary_color", ((c.root.props["--zen-primary-color"] // "" | ascii_downcase) == "#e6b450")],
  ["root_font", (c.root.props["font-family"] // "" | has_font)],
  ["browser_bg", ((c.browser_bg.props["--zen-main-browser-background"] // "" | ascii_downcase) == "#0b0e14")],
  ["toolbar_bg", ((c.toolbar_bg.props["--zen-main-browser-background-toolbar"] // "" | ascii_downcase) == "#0b0e14")],
  ["no_grain", (c.grain.props.display == "none")],
  ["urlbar_bg", (c.urlbar_bg.props["background-color"] == "rgb(15, 19, 26)")],
  ["urlbar_radius", (c.urlbar_bg.props["border-radius"] == "0px")],
  ["urlbar_caret", (c.urlbar_input.props["caret-color"] == "rgb(230, 180, 80)")],
  ["urlbar_font_size", (c.urlbar_input.props["font-size"] == "12px")],
  ["urlbar_prompt", (c.urlbar_prompt.props.content == "\"➜\"")],
  ["urlbar_prompt_color", (c.urlbar_prompt.props.color == "rgb(86, 91, 102)")],
  ["tab_selected_bg", (c.tab_selected_bg.props["background-color"] == "rgb(19, 23, 33)")],
  ["tab_selected_radius", (c.tab_selected_bg.props["border-radius"] == "0px")],
  ["tab_cursor", (c.tab_selected_bg.props["box-shadow"] // "" | test("rgb\\(230, 180, 80\\) 2px 0px 0px 0px inset"))],
  ["tab_selected_label", (c.tab_selected_label.props.color == "rgb(232, 230, 221)")],
  ["tab_font", (c.tab_selected_label.props["font-family"] // "" | has_font)],
  ["tab_font_size", (c.tab_selected_label.props["font-size"] == "12px")],
  ["tab_label_dim", (c.tab_label.props.color == "rgb(138, 137, 134)")],
  ["tab_close", (c.tab_close.props.color == "rgb(86, 91, 102)")],
  ["essential_bg", (c.essential_bg.props["background-color"] == "rgb(15, 19, 26)")],
  ["content_frame", (c.content_frame.props["box-shadow"] == "rgba(108, 115, 128, 0.2) 0px 0px 0px 1px")],
  ["content_browser_bg", (c.content_browser.props["background-color"] == "rgb(11, 14, 20)")],
  ["space_name", (c.space_name.props.color == "rgb(191, 189, 182)")],
  ["sidebar_button", (c.sidebar_button.props.color == "rgb(138, 137, 134)")],
  ["panel_font", (c.panel_font.props["font-family"] // "" | has_font)],
  ["menupopup_font", (c.menupopup_font.props["font-family"] // "" | has_font)],
  ["urlbar_open_bg", (u.urlbar_open_bg.props["background-color"] == "rgb(15, 19, 26)")],
  ["urlbar_open_font_size", (u.urlbar_open_input.props["font-size"] == "14px")],
  ["row_selected_bg", (u.row_selected.props["background-color"] == "rgb(19, 23, 33)")],
  ["row_selected_title", (u.row_selected_title.props.color == "rgb(232, 230, 221)")]
]
| (.[] | select(.[1] != true) | "FAIL " + .[0]), all(.[1] == true)

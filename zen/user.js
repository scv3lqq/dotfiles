// Zen Browser prefs: the terminal look of zen/chrome/userChrome.css.
// install.sh links this file into the active profile (macOS); Zen reads it on
// every start. Deleting a line does not reset a pref: set the default (in the
// trailing comment) or reset it in about:config.

// Load chrome/userChrome.css (default false)
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Dark UI regardless of the system appearance (default 2: follow the system)
user_pref("zen.view.window.scheme", 0);
// Ghostty cursor color; the Space gradient no longer tints the UI (default "AccentColor")
user_pref("zen.theme.accent-color", "#E6B450");
// Flat corners like tmux panes (default -1: platform radius)
user_pref("zen.theme.border-radius", 0);
// Gap around the web page, px (default 8)
user_pref("zen.theme.content-element-separation", 6);
// Opaque window like Ghostty, no desktop showing through (default true)
user_pref("zen.widget.macos.window-vibrancy", false);
// Essentials on the panel color instead of a favicon tint (default true)
user_pref("zen.theme.essentials-favicon-bg", false);

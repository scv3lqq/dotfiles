/*
 * tmux-style status bar for the Anki reviewer.
 *
 * Layout mirrors tmux-dotbar with `status-justify absolute-centre`:
 *   left   session component, powerline caps + deck name + block cursor
 *   centre window list, one entry per queue, current queue highlighted
 *   right  clock and date
 *
 * State is pushed from Python via window.terminalTheme.update(); this file
 * never reads Anki state on its own. All colours come from theme.css.
 */

(function () {
    "use strict";

    var BAR_ID = "tt-statusbar";
    var SEPARATOR = " • ";
    var EDGE_LEFT = "";
    var EDGE_RIGHT = "";

    var state = {
        deck: "",
        counts: { new: 0, learn: 0, review: 0 },
        active: null,
    };

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    }

    function build() {
        var bar = el("div", null);
        bar.id = BAR_ID;

        var left = el("div", "tt-left");
        var session = el("span", "tt-session");
        session.appendChild(el("span", "tt-edge", EDGE_LEFT));
        session.appendChild(el("span", "tt-session-name"));
        session.appendChild(el("span", "tt-edge", EDGE_RIGHT));
        left.appendChild(session);

        var windows = el("div", "tt-windows");
        var right = el("div", "tt-right");

        bar.appendChild(left);
        bar.appendChild(windows);
        bar.appendChild(right);
        return bar;
    }

    function bar() {
        var node = document.getElementById(BAR_ID);
        if (!node) {
            node = build();
            document.body.appendChild(node);
            document.body.classList.add("tt-has-statusbar");
        }
        return node;
    }

    function renderWindows(container) {
        var windows = [
            { index: 0, name: "new", count: state.counts.new },
            { index: 1, name: "learn", count: state.counts.learn },
            { index: 2, name: "review", count: state.counts.review },
        ];

        container.textContent = "";
        windows.forEach(function (win, i) {
            if (i > 0) {
                container.appendChild(el("span", "tt-sep", SEPARATOR));
            }
            var current = win.name === state.active;
            var label = win.index + ":" + win.name + " " + win.count;
            container.appendChild(
                el("span", "tt-window" + (current ? " tt-current" : ""), label)
            );
        });
    }

    function pad(value) {
        return value < 10 ? "0" + value : String(value);
    }

    function renderClock(container) {
        var now = new Date();
        var clock =
            pad(now.getHours()) + ":" + pad(now.getMinutes());
        var date =
            now.getFullYear() +
            "-" +
            pad(now.getMonth() + 1) +
            "-" +
            pad(now.getDate());

        container.textContent = "";
        container.appendChild(el("span", "tt-clock", clock));
        container.appendChild(el("span", "tt-sep", SEPARATOR));
        container.appendChild(el("span", "tt-date", date));
    }

    function render() {
        if (!document.body) {
            return;
        }
        var node = bar();
        node.querySelector(".tt-session-name").textContent = " " + state.deck + " ";
        renderWindows(node.querySelector(".tt-windows"));
        renderClock(node.querySelector(".tt-right"));
    }

    window.terminalTheme = {
        update: function (next) {
            if (next) {
                state.deck = next.deck || "";
                state.counts = next.counts || state.counts;
                state.active = next.active || null;
            }
            render();
        },
    };

    function start() {
        render();
        setInterval(render, 20000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();

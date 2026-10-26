#!/usr/bin/env python3
"""
Lint flashcard files for the Obsidian Spaced Repetition plugin (st3v3nmw).

The parser below is a faithful port of src/parser.ts (plugin v1.15.x), including
its quirks, so `--dump` shows exactly how the plugin will split your cards.

Usage:
  python3 lint_cards.py FILE_OR_DIR [...] [--vault VAULT_ROOT] [--dump] [--quiet]

  --vault   read separators / cloze settings from
            VAULT/.obsidian/plugins/obsidian-spaced-repetition/data.json
  --dump    print every parsed card (type, lines, front, back)
  --quiet   only print ERRORs

Exit code: 1 if any ERROR was found, else 0.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

SR_METADATA_CALLOUT = "> [!sr|card-metadata]"

DEFAULTS = {
    "singleLineCardSeparator": "::",
    "singleLineReversedCardSeparator": ":::",
    "multilineCardSeparator": "?",
    "multilineReversedCardSeparator": "??",
    "multilineCardEndMarker": "",
    "convertHighlightsToClozes": True,
    "convertBoldTextToClozes": False,
    "convertCurlyBracketsToClozes": False,
    "clozePatterns": None,
    "flashcardTags": ["#flashcards"],
    "convertFoldersToDecks": False,
}

# Common PostgreSQL type names that follow a `::` cast.
PG_TYPES = (
    "int|int2|int4|int8|integer|smallint|bigint|numeric|decimal|real|float|float4|float8|"
    "text|varchar|char|bpchar|name|bytea|bool|boolean|date|time|timetz|timestamp|timestamptz|"
    "interval|json|jsonb|uuid|oid|xid|xid8|cid|tid|regclass|regtype|regproc|regprocedure|"
    "regoper|regnamespace|pg_lsn|cstring|tsvector|tsquery|point|box|inet|cidr|money|"
    "int4range|int8range|numrange|tsrange|tstzrange|daterange|record|anyelement|void"
)
CAST_RE = re.compile(r"[\w'\")\]]::(" + PG_TYPES + r")\b(\[\])?", re.IGNORECASE)

YESNO_RE = re.compile(
    r"^\s*(is|are|does|do|did|can|could|will|would|should|was|were|has|have|is it true)\b"
    r"|^\s*(правда ли|верно ли|так ли)\b"
    r"|^\s*[^\s?]+\s+ли\b",
    re.IGNORECASE,
)
VAGUE_RE = re.compile(
    r"^\s*(how does .+ help|what about|tell (me )?about|describe|explain|what do you know about)\b"
    r"|^\s*(как .+ помогает|расскажи|опиши|объясни|что известно|что можно сказать)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------- settings
def load_settings(vault):
    s = dict(DEFAULTS)
    if vault:
        p = os.path.join(vault, ".obsidian", "plugins", "obsidian-spaced-repetition", "data.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            src = data.get("settings", data)
            for k in DEFAULTS:
                if k in src and src[k] is not None:
                    s[k] = src[k]
            print(f"[info] using plugin settings from {p}")
        else:
            print(f"[info] no plugin data.json under {vault}; using defaults")
    pats = s.get("clozePatterns")
    if not pats:
        pats = []
        if s["convertHighlightsToClozes"]:
            pats.append("==[123;;]answer[;;hint]==")
        if s["convertBoldTextToClozes"]:
            pats.append("**[123;;]answer[;;hint]**")
        if s["convertCurlyBracketsToClozes"]:
            pats.append("{{[123;;]answer[;;hint]}}")
    s["clozePatterns"] = pats
    return s


def cloze_regexes(patterns):
    """Approximate clozecraft: support the ==, ** and {{ }} delimiter families."""
    out = []
    for p in patterns:
        if p.startswith("=="):
            out.append(re.compile(r"==(?!=)(.+?)=="))
        elif p.startswith("**"):
            out.append(re.compile(r"\*\*(?!\*)(.+?)\*\*"))
        elif p.startswith("{{"):
            out.append(re.compile(r"\{\{(.+?)\}\}"))
    return out


# ---------------------------------------------------------------- parser port
def marker_inside_code(text, marker, idx):
    before = text[:idx].count("`")
    after = text[idx + len(marker):].count("`")
    return before % 2 == 1 and after % 2 == 1


def has_inline_marker(text, marker):
    if not marker:
        return False
    idx = text.find(marker)  # NOTE: plugin checks only the FIRST occurrence
    if idx == -1:
        return False
    return not marker_inside_code(text, marker, idx)


def strip_frontmatter(text):
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                fm = "\n".join(lines[1:j])
                return fm, "\n" * j + "\n" + "\n".join(lines[j + 1:])
    return "", "\n".join(lines)


def parse(text, s, cloze_res):
    inline = sorted(
        [(s["singleLineCardSeparator"], "single"), (s["singleLineReversedCardSeparator"], "single-rev")],
        key=lambda x: -len(x[0]),
    )
    end_marker = s["multilineCardEndMarker"]
    cards = []
    card_text, card_type, first = "", None, 0
    lines = text.split("\n")
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        trimmed = line.strip()
        # plugin quirk: skips the comment AND the following line; an unclosed
        # comment line swallows everything to the end of the file
        if line.startswith("<!--") and not line.startswith("<!--SR:"):
            while i + 1 < n and "-->" not in line:
                i += 1
            i += 2
            continue
        is_empty = len(trimmed) == 0
        has_end = bool(end_marker) and trimmed == end_marker
        if (is_empty and not end_marker) or (is_empty and card_type is None) or has_end:
            if card_type:
                cards.append((card_type, card_text.rstrip(), first, i - 1))
                card_type = None
            card_text, first = "", i + 1
            i += 1
            continue
        if card_text:
            card_text += "\n"
        card_text += line.rstrip()
        for sep, typ in inline:
            if has_inline_marker(line, sep):
                card_type = typ
                break
        if card_type in ("single", "single-rev"):
            card_text, first = line, i
            if i + 1 < n and lines[i + 1].startswith("<!--SR:"):
                card_text += "\n" + lines[i + 1]
                i += 1
            elif i + 1 < n and lines[i + 1].startswith(SR_METADATA_CALLOUT):
                for j in range(i + 1, n):
                    card_text += "\n" + lines[j]
                    i += 1
                    if "<!--SR:" in lines[j]:
                        break
            cards.append((card_type, card_text, first, i))
            card_type, card_text = None, ""
        elif trimmed == s["multilineCardSeparator"]:
            if len(card_text) > 1:
                card_type = "multi"
        elif trimmed == s["multilineReversedCardSeparator"]:
            if len(card_text) > 1:
                card_type = "multi-rev"
        elif line.startswith("```") or line.startswith("~~~"):
            close = re.match(r"`+|~+", line).group(0)
            while i + 1 < n and not lines[i + 1].startswith(close):
                i += 1
                card_text += "\n" + lines[i]
            card_text += "\n" + close
            i += 1
        elif card_type is None and any(r.search(line) for r in cloze_res):
            card_type = "cloze"
        i += 1
    if card_type and card_text:
        cards.append((card_type, card_text.rstrip(), first, n - 1))
    return cards


# ---------------------------------------------------------------- analysis
def split_card(ctype, text, s, cloze_res):
    body = "\n".join(l for l in text.split("\n") if not l.startswith("<!--SR:") and not l.startswith(SR_METADATA_CALLOUT))
    body = re.sub(r"<!--SR:.*?-->", "", body).rstrip()
    if ctype in ("single", "single-rev"):
        sep = s["singleLineReversedCardSeparator"] if ctype == "single-rev" else s["singleLineCardSeparator"]
        a, _, b = body.partition(sep)
        return a.strip(), b.strip()
    if ctype in ("multi", "multi-rev"):
        sep = s["multilineReversedCardSeparator"] if ctype == "multi-rev" else s["multilineCardSeparator"]
        ls = body.split("\n")
        for k, l in enumerate(ls):
            if l.strip() == sep:
                return "\n".join(ls[:k]).strip(), "\n".join(ls[k + 1:]).strip()
        return body, ""
    def parts(m):
        p = m.group(1).split(";;")
        if len(p) > 1 and p[0].strip().isdigit():
            p = p[1:]
        return p[0], (p[1] if len(p) > 1 else None)

    front, back = body, body
    for r in cloze_res:
        front = r.sub(lambda m: f"[{parts(m)[1] or '...'}]", front)
        back = r.sub(lambda m: parts(m)[0], back)
    return front + "   (dump hides all deletions at once)", back


def words(t):
    t = re.sub(r"```.*?```", " CODE ", t, flags=re.S)
    return len(re.findall(r"\w+", t))


def lint_file(path, s):
    issues = []  # (severity, line_no_1based, message)
    raw = open(path, encoding="utf-8").read()
    fm, text = strip_frontmatter(raw)
    lines = text.split("\n")
    cloze_res = cloze_regexes(s["clozePatterns"])
    cards = parse(text, s, cloze_res)

    def add(sev, ln, msg):
        issues.append((sev, ln + 1, msg))

    # --- deck tag
    tag_roots = [t.lstrip("#") for t in s["flashcardTags"]]
    fm_has = any(re.search(r"(^|[\s\[,'\"-])#?" + re.escape(t) + r"(/|\b)", fm) for t in tag_roots)
    first_inline = None
    for k, l in enumerate(lines):
        if any(re.search(r"(^|\s)#" + re.escape(t) + r"(/|\b)", l) for t in tag_roots):
            first_inline = k
            break
    if not s["convertFoldersToDecks"]:
        if not fm_has and first_inline is None and cards:
            add("ERROR", 0, f"no deck tag ({', '.join(s['flashcardTags'])}) in frontmatter or body: cards will not be reviewed")
        elif not fm_has and first_inline is not None:
            early = [c for c in cards if c[2] < first_inline]
            if early:
                add("WARN", early[0][2], "cards appear before the first deck tag; put the tag in frontmatter or at the top")

    # --- HTML comments (plugin quirk)
    for k, l in enumerate(lines):
        if l.startswith("<!--") and not l.startswith("<!--SR:"):
            if "-->" not in l:
                add("ERROR", k, "multi-line HTML comment: the plugin skips EVERYTHING after this line")
            else:
                if k + 1 < len(lines) and lines[k + 1].strip():
                    add("ERROR", k, "HTML comment: the plugin also silently skips the next line (put a blank line after it, or remove the comment)")
                if k > 0 and lines[k - 1].strip() and not lines[k - 1].startswith("<!--SR:"):
                    add("ERROR", k, "HTML comment directly after text: it eats the blank line that ends the card above, merging/losing cards")

    # --- indented fences
    for k, l in enumerate(lines):
        if re.match(r"^\s+(```|~~~)", l):
            add("WARN", k, "indented code fence: the parser only recognises fences at column 0")

    # --- ':: inside inline code' drops the card
    sep = s["singleLineCardSeparator"]
    for k, l in enumerate(lines):
        if sep and sep in l and not has_inline_marker(l, sep):
            idx = l.find(sep)
            rest_idx = l.find(sep, idx + len(sep))
            while rest_idx != -1:
                if not marker_inside_code(l, sep, rest_idx):
                    add("ERROR", k, f"'{sep}' first appears inside inline code, so the real separator later on this line is ignored: card LOST. Use a multi-line card.")
                    break
                rest_idx = l.find(sep, rest_idx + len(sep))

    # --- per-card checks
    fronts = Counter()
    card_lines = set()
    for ctype, ctext, a, b in cards:
        card_lines.update(range(a, b + 1))
        front, back = split_card(ctype, ctext, s, cloze_res)
        fronts[front.strip().lower()] += 1
        if ctype in ("single", "single-rev"):
            first_line = ctext.split("\n")[0]
            cast_outside_code = any(
                not marker_inside_code(first_line, "::", m.start() + 1) for m in CAST_RE.finditer(first_line)
            )
            if cast_outside_code:
                add("ERROR", a, "looks like a PostgreSQL cast (x::type) parsed as a card separator. Wrap SQL in backticks inside a multi-line card, or use CAST(x AS type)")
            if not back:
                add("ERROR", a, "single-line card with empty back")
        if ctype in ("multi", "multi-rev") and not back:
            add("ERROR", a, "multi-line card with empty back")
        if ctype == "cloze":
            dels = [m for r in cloze_res for m in r.finditer(ctext)]
            numbered = [m for m in dels if re.match(r"^\s*\d+;;", m.group(1))]
            if numbered and len(numbered) != len(dels):
                add("ERROR", a, "mix of numbered and un-numbered clozes in one card (plugin cannot mix cloze types)")
            groups = {m.group(1).split(';;')[0] for m in numbered} if numbered else None
            n_cards = len(groups) if groups else len(dels)
            if n_cards > 3:
                add("WARN", a, f"cloze creates {n_cards} sibling cards; more than 3 usually means an enumeration — split it")
            continue
        fw, bw = words(front), words(back.split("\n")[0])
        if fw > 40:
            add("WARN", a, f"question is long ({fw} words); tighten it")
        if bw > 25:
            add("WARN", a, f"first answer line is long ({bw} words); keep the gradable core short, move 'why' to a second line")
        if words(back) > 70:
            add("WARN", a, f"answer is long ({words(back)} words) — probably several cards")
        items = [l for l in back.split("\n") if re.match(r"^\s*([-*+]|\d+[.)])\s+", l)]
        if len(items) >= 3:
            add("WARN", a, f"answer is a list of {len(items)} items — enumerations are hard to recall; split or use per-item cards")
        elif back.split("\n")[0].count(",") + back.split("\n")[0].count(";") >= 3:
            add("WARN", a, "answer looks like an inline enumeration (≥4 items); consider splitting")
        q = front.split("\n")[0]
        if YESNO_RE.search(q):
            add("WARN", a, "yes/no question (50% guessable); ask for the reason, condition or consequence instead")
        if VAGUE_RE.search(q):
            add("WARN", a, "vague question stem; ask something with exactly one correct answer")

    for f, c in fronts.items():
        if c > 1 and f:
            add("WARN", 0, f"duplicate question ×{c}: {f[:70]!r}")

    # --- headings glued to a multi-line card become part of its question
    for ctype, ctext, a, b in cards:
        if ctype in ("multi", "multi-rev", "cloze") and re.match(r"^#{1,6}\s", ctext.split("\n")[0]):
            add("WARN", a, "heading is glued to the card (no blank line) and becomes part of its front")

    # --- orphan text (not parsed as any card)
    def ignorable(l):
        return (not l.strip()) or re.match(r"^\s*(#{1,6}\s|<!--|---\s*$|#\S+\s*$)", l)

    k = 0
    while k < len(lines):
        if k not in card_lines and not ignorable(lines[k]):
            start = k
            while k < len(lines) and k not in card_lines and lines[k].strip() and not ignorable(lines[k]):
                k += 1
            prev = start - 2
            follows_card = prev >= 0 and prev in card_lines and not lines[start - 1].strip()
            sev = "WARN" if follows_card else "INFO"
            why = "right after a card — answer cut off by a blank line?" if follows_card else "text not parsed as a card"
            add(sev, start, f"{why}: {lines[start][:60]!r}")
            continue
        k += 1

    return cards, issues, cloze_res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--vault")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    s = load_settings(args.vault)

    files = []
    for p in args.paths:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                if "/.obsidian" in root or "/.trash" in root:
                    continue
                files += [os.path.join(root, f) for f in fs if f.endswith(".md")]
        else:
            files.append(p)

    total_err = total_cards = 0
    for path in sorted(files):
        cards, issues, cloze_res = lint_file(path, s)
        total_cards += len(cards)
        errs = sum(1 for i in issues if i[0] == "ERROR")
        total_err += errs
        shown = [i for i in issues if not args.quiet or i[0] == "ERROR"]
        if shown or args.dump:
            print(f"\n== {path}: {len(cards)} cards, {errs} errors")
        for sev, ln, msg in sorted(shown, key=lambda x: x[1]):
            print(f"  {sev:5} L{ln}: {msg}")
        if args.dump:
            for ctype, ctext, a, b in cards:
                front, back = split_card(ctype, ctext, s, cloze_res)
                print(f"  --- [{ctype}] L{a + 1}-{b + 1}")
                print("   Q: " + front.replace("\n", "\n      "))
                print("   A: " + back.replace("\n", "\n      "))
    print(f"\nTotal: {total_cards} cards in {len(files)} file(s), {total_err} error(s)")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()

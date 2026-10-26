#!/usr/bin/env python3
"""AnkiConnect client, validator and TSV writer for the `anki` skill.

Every subcommand reads a JSON document from stdin and prints JSON to stdout.
Validation and transport errors exit non-zero with a readable message on stderr.

Python 3 stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import html as html_mod
import io
import json
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"

# The script is allowed to call these AnkiConnect actions and nothing else.
# Existing notes are never modified or deleted.
ALLOWED_ACTIONS = frozenset(
    {
        "version",
        "deckNames",
        "modelNames",
        "modelFieldNames",
        "findNotes",
        "notesInfo",
        "cardsInfo",
        "getTags",
        "canAddNotes",
        "canAddNotesWithErrorDetail",
        "addNotes",
        "sync",
    }
)

API_VERSION = 6
TIMEOUT = 20

HEADER = ("#separator:tab", "#html:true", "#notetype column:1", "#tags column:4")
COLUMNS = 4
VALID_TYPES = ("Basic", "Cloze")

CLOZE_OPEN_RE = re.compile(r"\{\{c(\d+)::")
CLOZE_FULL_RE = re.compile(r"\{\{c\d+::(.+?)\}\}", re.DOTALL)
ENTITY_RE = re.compile(r"&(?!(?:amp|lt|gt|quot|nbsp|#\d+|#x[0-9a-fA-F]+);)")
MATHJAX_TRAP_RE = re.compile(r"(\}|\\\))\}\}")
TAG_RE = re.compile(r"<[^>]+>")
TRAILING_PAREN_RE = re.compile(r"\s*\([^()]*\)\s*$")
SLUG_RE = re.compile(r"[^a-z0-9]+")
# Anki search syntax escapes exactly these characters
QUERY_ESCAPE_RE = re.compile(r'([\\":*_])')


class AnkiError(Exception):
    """AnkiConnect answered with an error, or was asked for a forbidden action."""


class Unreachable(Exception):
    """Anki is not running or AnkiConnect is not listening."""


class ValidationError(Exception):
    """The cards do not satisfy the card contract."""


# --------------------------------------------------------------------------- config


def load_config() -> dict:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValidationError(f"config not found: {CONFIG_PATH}")
    except json.JSONDecodeError as exc:
        raise ValidationError(f"config is not valid JSON: {exc}")
    for key in ("ankiconnect_url", "note_types", "decks", "out_dir"):
        if key not in config:
            raise ValidationError(f"config is missing {key!r}")
    for ctype in VALID_TYPES:
        entry = config["note_types"].get(ctype)
        if not entry or "name" not in entry or len(entry.get("fields", [])) < 2:
            raise ValidationError(f"config note_types.{ctype} needs 'name' and two 'fields'")
    return config


# --------------------------------------------------------------------------- transport


def invoke(config: dict, action: str, **params):
    if action not in ALLOWED_ACTIONS:
        raise AnkiError(f"action not allowed by this script: {action}")
    payload = json.dumps(
        {"action": action, "version": API_VERSION, "params": params}
    ).encode("utf-8")
    request = urllib.request.Request(
        config["ankiconnect_url"],
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
        raise Unreachable(str(exc))
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AnkiError(f"{action}: AnkiConnect returned non-JSON: {exc}")
    if not isinstance(data, dict) or "error" not in data or "result" not in data:
        raise AnkiError(f"{action}: unexpected response shape: {body[:200]}")
    if data["error"] is not None:
        raise AnkiError(f"{action}: {data['error']}")
    return data["result"]


# --------------------------------------------------------------------------- text


def normalize_field(value: str) -> str:
    """Field text as it goes into Anki: <br> for newlines, entity-safe ampersands."""
    text = ENTITY_RE.sub("&amp;", value)
    text = text.replace("\r\n", "<br>").replace("\n", "<br>").replace("\r", "<br>")
    return text.replace("\t", " ")


def strip_html(value: str) -> str:
    text = value.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    text = TAG_RE.sub("", text)
    text = html_mod.unescape(text).replace("\xa0", " ")
    return " ".join(text.split())


def compare_key(value: str) -> str:
    """Front text reduced for matching: HTML stripped, trailing '(...)' removed."""
    return TRAILING_PAREN_RE.sub("", strip_html(value)).strip().casefold()


def cloze_answers(text: str) -> list[str]:
    answers = []
    for raw in CLOZE_FULL_RE.findall(text):
        answers.append(strip_html(raw.split("::", 1)[0]))
    return answers


def first_line(value: str) -> str:
    parts = re.split(r"<br\s*/?>", value, maxsplit=1)
    return strip_html(parts[0]) if parts else ""


def preview(text: str, limit: int = 60) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def slugify(value: str) -> str:
    return SLUG_RE.sub("-", strip_html(value).casefold()).strip("-") or "cards"


def escape_query(term: str) -> str:
    return QUERY_ESCAPE_RE.sub(r"\\\1", term)


# --------------------------------------------------------------------------- validation


def validate(cards, config: dict) -> None:
    if not isinstance(cards, list) or not cards:
        raise ValidationError("input must be a non-empty JSON array of cards")

    errors: list[str] = []
    fronts: dict[str, int] = {}
    deck_keys = set(config["decks"])

    for index, card in enumerate(cards, start=1):
        where = f"card {index}"
        if not isinstance(card, dict):
            errors.append(f"{where}: expected an object, got {type(card).__name__}")
            continue

        ctype = card.get("type")
        deck = card.get("deck")
        front = card.get("front")
        back = card.get("back", "")
        tags = card.get("tags", [])

        if not isinstance(front, str):
            errors.append(f"{where}: 'front' must be a string")
            front = ""
        if not isinstance(back, str):
            errors.append(f"{where}: 'back' must be a string")
            back = ""
        if front.strip():
            where = f"card {index} ({preview(front)})"
        else:
            errors.append(f"{where}: empty front")

        if ctype not in VALID_TYPES:
            errors.append(f"{where}: type must be exactly Basic or Cloze, got {ctype!r}")
        if deck not in deck_keys:
            errors.append(
                f"{where}: deck must be one of {sorted(deck_keys)}, got {deck!r}"
            )

        numbers = [int(n) for n in CLOZE_OPEN_RE.findall(front)]
        if ctype == "Cloze":
            if not numbers:
                errors.append(f"{where}: Cloze card has no cloze markup")
            else:
                unique = sorted(set(numbers))
                if unique != list(range(1, max(unique) + 1)):
                    errors.append(
                        f"{where}: cloze numbers must start at c1 with no gaps, got "
                        + ", ".join("c%d" % n for n in unique)
                    )
        elif ctype == "Basic":
            if numbers or CLOZE_OPEN_RE.search(back):
                errors.append(f"{where}: Basic card contains cloze markup")

        for name, field in (("front", front), ("back", back)):
            if MATHJAX_TRAP_RE.search(field):
                errors.append(
                    f"{where}: '{name}' closes a cloze right after }} or \\) "
                    "(insert a space before the closing braces)"
                )

        if not isinstance(tags, list):
            errors.append(f"{where}: 'tags' must be a list")
        else:
            for tag in tags:
                if not isinstance(tag, str) or not tag.strip():
                    errors.append(f"{where}: empty or non-string tag")
                elif "#" in tag:
                    errors.append(f"{where}: tag {tag!r} contains '#'")
                elif any(ch.isspace() for ch in tag):
                    errors.append(f"{where}: tag {tag!r} contains whitespace")

        key = front.strip()
        if key:
            if key in fronts:
                errors.append(f"{where}: duplicate front, same as card {fronts[key]}")
            else:
                fronts[key] = index

    if errors:
        raise ValidationError("\n".join(errors))


# --------------------------------------------------------------------------- tsv


def render_tsv(cards: list, config: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(
        buffer,
        delimiter="\t",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
        quotechar='"',
        doublequote=True,
    )
    for card in cards:
        writer.writerow(
            [
                config["note_types"][card["type"]]["name"],
                normalize_field(card["front"]),
                normalize_field(card.get("back", "")),
                " ".join(card.get("tags", [])),
            ]
        )
    return "\n".join(HEADER) + "\n" + buffer.getvalue()


def resolve_path(out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = name[:-4] if name.endswith(".txt") else name
    candidate = out_dir / (stem + ".txt")
    counter = 2
    while candidate.exists():
        candidate = out_dir / ("%s-%d.txt" % (stem, counter))
        counter += 1
    return candidate


def verify_file(path: Path, expected_rows: int) -> None:
    lines = path.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if tuple(lines[:4]) != HEADER:
        raise ValidationError("%s: header mismatch: %r" % (path, lines[:4]))
    data = lines[4:]
    if len(data) != expected_rows:
        raise ValidationError(
            "%s: wrote %d rows, expected %d" % (path, len(data), expected_rows)
        )
    for offset, row in enumerate(
        csv.reader(data, delimiter="\t", quotechar='"', doublequote=True), start=1
    ):
        if len(row) != COLUMNS:
            raise ValidationError(
                "%s: row %d has %d columns, expected %d"
                % (path, offset, len(row), COLUMNS)
            )


def default_name(cards: list) -> str:
    if len(cards) <= 2:
        return "anki-" + slugify(TRAILING_PAREN_RE.sub("", strip_html(cards[0]["front"])))
    return "anki-" + datetime.date.today().isoformat()


def write_tsv(cards: list, config: dict, name: str | None, out_dir: str | None) -> Path:
    directory = Path(out_dir or config["out_dir"]).expanduser()
    path = resolve_path(directory, name or default_name(cards))
    path.write_text(render_tsv(cards, config), encoding="utf-8", newline="")
    verify_file(path, len(cards))
    return path


# --------------------------------------------------------------------------- context


def cmd_context(payload: dict, config: dict, args) -> dict:
    terms = payload.get("terms") or []
    if not isinstance(terms, list) or not all(isinstance(t, str) for t in terms):
        raise ValidationError("input must be {\"terms\": [\"...\"]}")

    try:
        invoke(config, "version")
    except Unreachable:
        return {"reachable": False, "matches": {}, "tags": []}

    decks = sorted(set(config["decks"].values()))
    deck_clause = "(" + " OR ".join('deck:"%s"' % d for d in decks) + ")"

    matches: dict[str, list] = {}
    for term in terms:
        found: list[dict] = []
        query = '%s "%s"' % (deck_clause, escape_query(term))
        try:
            note_ids = invoke(config, "findNotes", query=query)
        except AnkiError:
            note_ids = []
        if note_ids:
            notes = invoke(config, "notesInfo", notes=note_ids)
            card_ids = [n["cards"][0] for n in notes if n.get("cards")]
            deck_of: dict[int, str] = {}
            if card_ids:
                for card in invoke(config, "cardsInfo", cards=card_ids):
                    deck_of[card["cardId"]] = card["deckName"]
            wanted = compare_key(term)
            for note in notes:
                ordered = sorted(note["fields"].items(), key=lambda kv: kv[1]["order"])
                first = ordered[0][1]["value"] if ordered else ""
                second = ordered[1][1]["value"] if len(ordered) > 1 else ""
                hit = compare_key(first) == wanted or any(
                    compare_key(a) == wanted for a in cloze_answers(first)
                )
                if not hit:
                    continue
                cid = note["cards"][0] if note.get("cards") else None
                found.append(
                    {
                        "note_id": note["noteId"],
                        "deck": deck_of.get(cid, ""),
                        "note_type": note["modelName"],
                        "front": strip_html(first),
                        "back_first_line": first_line(second),
                    }
                )
        matches[term] = found

    return {"reachable": True, "matches": matches, "tags": invoke(config, "getTags")}


# --------------------------------------------------------------------------- push


def build_note(card: dict, config: dict) -> dict:
    note_type = config["note_types"][card["type"]]
    return {
        "deckName": config["decks"][card["deck"]],
        "modelName": note_type["name"],
        "fields": {
            note_type["fields"][0]: normalize_field(card["front"]),
            note_type["fields"][1]: normalize_field(card.get("back", "")),
        },
        "tags": list(card.get("tags", [])),
        "options": {"allowDuplicate": False, "duplicateScope": "deck"},
    }


def cmd_push(cards: list, config: dict, args) -> dict:
    validate(cards, config)

    try:
        invoke(config, "version")
    except Unreachable as exc:
        if args.no_fallback:
            raise AnkiError("Anki is unreachable and --no-fallback was given: %s" % exc)
        path = write_tsv(cards, config, args.name, args.out_dir)
        return {"reachable": False, "added": [], "skipped": [], "fallback": str(path)}

    needed = {config["decks"][card["deck"]] for card in cards}
    missing = sorted(needed - set(invoke(config, "deckNames")))
    if missing:
        raise AnkiError(
            "deck missing in Anki: %s. Create it in Anki (Decks, Create Deck), or point "
            "config.json at an existing deck. This script is not allowed to create decks."
            % ", ".join(missing)
        )

    notes = [build_note(card, config) for card in cards]
    try:
        verdicts = invoke(config, "canAddNotesWithErrorDetail", notes=notes)
    except AnkiError:
        verdicts = [{"canAdd": ok} for ok in invoke(config, "canAddNotes", notes=notes)]

    addable: list[int] = []
    skipped: list[dict] = []
    for index, verdict in enumerate(verdicts):
        if verdict.get("canAdd"):
            addable.append(index)
        else:
            skipped.append(
                {
                    "front": strip_html(cards[index]["front"]),
                    "reason": verdict.get("error") or "Anki refused the note",
                }
            )

    result: dict = {"reachable": True, "added": [], "skipped": skipped}

    if args.dry_run:
        result["dry_run"] = True
        result["addable"] = [strip_html(cards[i]["front"]) for i in addable]
        return result

    if addable:
        batch = [notes[i] for i in addable]
        try:
            note_ids = invoke(config, "addNotes", notes=batch)
        except AnkiError as exc:
            for i in addable:
                skipped.append(
                    {"front": strip_html(cards[i]["front"]), "reason": "addNotes: %s" % exc}
                )
            note_ids = []
        for position, note_id in enumerate(note_ids):
            card_index = addable[position]
            if note_id is None:
                skipped.append(
                    {
                        "front": strip_html(cards[card_index]["front"]),
                        "reason": "addNotes returned null (duplicate or rejected)",
                    }
                )
            else:
                result["added"].append(note_id)

    if result["added"]:
        result["browse"] = "nid:" + ",".join(str(n) for n in result["added"])

    if args.also_tsv:
        result["tsv"] = str(write_tsv(cards, config, args.name, args.out_dir))

    if config.get("sync_after_push") and result["added"]:
        invoke(config, "sync")
        result["synced"] = True

    return result


def cmd_discover(payload: dict, config: dict, args) -> dict:
    """Re-derive what config.json should say, read-only. Nothing is written."""
    try:
        invoke(config, "version")
    except Unreachable:
        return {"reachable": False}

    notes = invoke(config, "notesInfo", notes=invoke(config, "findNotes", query="deck:*"))
    counts: dict[str, int] = {}
    for note in notes:
        counts[note["modelName"]] = counts.get(note["modelName"], 0) + 1
    note_types = [
        {
            "name": name,
            "notes": count,
            "fields": invoke(config, "modelFieldNames", modelName=name),
        }
        for name, count in sorted(counts.items(), key=lambda kv: -kv[1])
    ]

    first_cards = [note["cards"][0] for note in notes if note.get("cards")]
    deck_of: dict[int, str] = {}
    for start in range(0, len(first_cards), 500):
        for card in invoke(config, "cardsInfo", cards=first_cards[start : start + 500]):
            deck_of[card["cardId"]] = card["deckName"]

    by_root: dict[str, dict[str, int]] = {}
    for note in notes:
        deck = deck_of.get(note["cards"][0]) if note.get("cards") else None
        if not deck:
            continue
        for root in {tag.split("::")[0] for tag in note.get("tags", [])}:
            by_root.setdefault(root, {})
            by_root[root][deck] = by_root[root].get(deck, 0) + 1

    tag_roots = [
        {
            "tag_root": root,
            "notes": sum(decks.values()),
            "decks": sorted(decks.items(), key=lambda kv: -kv[1]),
        }
        for root, decks in sorted(by_root.items())
    ]

    existing = set(invoke(config, "deckNames"))
    return {
        "reachable": True,
        "note_types": note_types,
        "tag_roots": tag_roots,
        "configured_decks": {
            key: {"deck": deck, "exists": deck in existing}
            for key, deck in config["decks"].items()
        },
        "missing_decks": sorted({d for d in config["decks"].values() if d not in existing}),
    }


def cmd_tsv(cards: list, config: dict, args) -> dict:
    validate(cards, config)
    path = write_tsv(cards, config, args.name, args.out_dir)
    basic = sum(1 for c in cards if c["type"] == "Basic")
    return {
        "path": str(path),
        "cards": len(cards),
        "basic": basic,
        "cloze": len(cards) - basic,
    }


# --------------------------------------------------------------------------- selftest


SELFTEST_CONFIG = {
    "ankiconnect_url": "http://127.0.0.1:8765",
    "note_types": {
        "Basic": {"name": "Basic", "fields": ["Front", "Back"]},
        "Cloze": {"name": "Cloze", "fields": ["Text", "Back Extra"]},
    },
    "decks": {"language": "English", "grammar": "English", "math": "Math", "tech": "Tech"},
    "out_dir": "~/anki-cards",
    "sync_after_push": False,
}

SELFTEST_CARDS = [
    {
        "type": "Cloze",
        "deck": "language",
        "front": 'She said the deal was "final" and {{c1::walked out}}.',
        "back": "уйти.\nРезко и демонстративно.",
        "tags": ["en::vocab", "en::phrase"],
    },
    {
        "type": "Basic",
        "deck": "tech",
        "front": "R&D (noun)",
        "back": "НИОКР.\nResearch & development, an existing &amp; is left alone.",
        "tags": ["tech::glossary"],
    },
    {
        "type": "Cloze",
        "deck": "math",
        "front": "The derivative of \\(x^{2}\\) is {{c1::\\(2x\\) }}.",
        "back": "Power rule.\tTabs collapse to a space.",
        "tags": ["math::calculus"],
    },
]

SELFTEST_EXPECTED = (
    "#separator:tab\n"
    "#html:true\n"
    "#notetype column:1\n"
    "#tags column:4\n"
    'Cloze\t"She said the deal was ""final"" and {{c1::walked out}}."\t'
    "уйти.<br>Резко и демонстративно.\ten::vocab en::phrase\n"
    "Basic\tR&amp;D (noun)\t"
    "НИОКР.<br>Research &amp; development, an existing &amp; is left alone.\ttech::glossary\n"
    "Cloze\tThe derivative of \\(x^{2}\\) is {{c1::\\(2x\\) }}.\t"
    "Power rule. Tabs collapse to a space.\tmath::calculus\n"
)


def selftest() -> int:
    failures: list[str] = []

    try:
        validate(SELFTEST_CARDS, SELFTEST_CONFIG)
    except ValidationError as exc:
        failures.append("fixture did not validate:\n%s" % exc)

    actual = render_tsv(SELFTEST_CARDS, SELFTEST_CONFIG)
    if actual.encode("utf-8") != SELFTEST_EXPECTED.encode("utf-8"):
        failures.append("TSV bytes differ from the expected fixture")
        for line_no, (got, want) in enumerate(
            zip(actual.split("\n"), SELFTEST_EXPECTED.split("\n")), start=1
        ):
            if got != want:
                failures.append("  line %d expected: %r" % (line_no, want))
                failures.append("  line %d actual:   %r" % (line_no, got))

    with tempfile.TemporaryDirectory() as tmp:
        path = write_tsv(SELFTEST_CARDS, SELFTEST_CONFIG, "anki-selftest", tmp)
        if path.read_bytes() != SELFTEST_EXPECTED.encode("utf-8"):
            failures.append("written file differs from the expected fixture")
        again = write_tsv(SELFTEST_CARDS, SELFTEST_CONFIG, "anki-selftest", tmp)
        if again.name != "anki-selftest-2.txt":
            failures.append("collision suffix gave %s, expected anki-selftest-2.txt" % again.name)

    negatives = [
        ("MathJax trap", [{"type": "Cloze", "deck": "math", "front": "{{c1::\\(2x\\)}}", "back": "", "tags": []}]),
        ("cloze gap", [{"type": "Cloze", "deck": "math", "front": "{{c1::a}} {{c3::b}}", "back": "", "tags": []}]),
        ("cloze in Basic", [{"type": "Basic", "deck": "tech", "front": "{{c1::x}}", "back": "", "tags": []}]),
        ("bad deck key", [{"type": "Basic", "deck": "history", "front": "x", "back": "", "tags": []}]),
        ("tag with space", [{"type": "Basic", "deck": "tech", "front": "x", "back": "", "tags": ["a b"]}]),
        ("tag with hash", [{"type": "Basic", "deck": "tech", "front": "x", "back": "", "tags": ["#a"]}]),
        ("empty front", [{"type": "Basic", "deck": "tech", "front": "  ", "back": "", "tags": []}]),
        ("duplicate fronts", [
            {"type": "Basic", "deck": "tech", "front": "x", "back": "", "tags": []},
            {"type": "Basic", "deck": "tech", "front": "x", "back": "", "tags": []},
        ]),
    ]
    for label, cards in negatives:
        try:
            validate(cards, SELFTEST_CONFIG)
        except ValidationError:
            continue
        failures.append("validator missed: %s" % label)

    try:
        invoke(SELFTEST_CONFIG, "deleteNotes", notes=[1])
    except AnkiError as exc:
        if "not allowed" not in str(exc):
            failures.append("action whitelist raised the wrong error: %s" % exc)
    except Exception as exc:  # noqa: BLE001 - any escape means the whitelist did not hold
        failures.append("action whitelist did not block deleteNotes: %r" % exc)
    else:
        failures.append("action whitelist did not block deleteNotes")

    if failures:
        print("SELFTEST FAILED", file=sys.stderr)
        for line in failures:
            print("  " + line, file=sys.stderr)
        return 1

    print(
        "SELFTEST OK: 3 cards byte-identical, escaping, collision suffix, "
        "8 validator rules and the action whitelist all verified"
    )
    return 0


# --------------------------------------------------------------------------- cli


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=["context", "push", "tsv", "discover"])
    parser.add_argument("--name")
    parser.add_argument("--out-dir")
    parser.add_argument("--also-tsv", action="store_true")
    parser.add_argument("--no-fallback", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.command:
        parser.error("a subcommand is required (context, push, tsv, discover) unless --selftest")

    raw = sys.stdin.read()
    if args.command == "discover" and not raw.strip():
        raw = "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print("ERROR: stdin is not valid JSON: %s" % exc, file=sys.stderr)
        return 2

    try:
        config = load_config()
        if args.command == "context":
            result = cmd_context(payload, config, args)
        elif args.command == "discover":
            result = cmd_discover(payload, config, args)
        elif args.command == "push":
            result = cmd_push(payload, config, args)
        else:
            result = cmd_tsv(payload, config, args)
    except ValidationError as exc:
        print("VALIDATION ERROR:\n%s" % exc, file=sys.stderr)
        return 1
    except AnkiError as exc:
        print("ANKI ERROR: %s" % exc, file=sys.stderr)
        return 1
    except Unreachable as exc:
        print("ANKI UNREACHABLE: %s" % exc, file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Command-line interface for glossanon.

Designed to be a drop-in pipeline stage:

    glossanon document.md -o document.anon.md      # single file
    glossanon ./corpus -r --out ./corpus_anon      # a directory tree
    cat report.txt | glossanon - > report.anon.txt # stdin -> stdout filter
    glossanon doc.md --json                         # emit entity report as JSON

Run ``glossanon --help`` for the full list of options.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .config import AnonymizerConfig, Strategy
from .engine import Anonymizer
from .types import AnonymizationResult, EntityType

_DEFAULT_GLOBS = ("*.txt", "*.md")


def _build_config(args: argparse.Namespace) -> AnonymizerConfig:
    data = {
        "strategy": args.strategy,
        "score_threshold": args.threshold,
        "normalize_ocr": not args.no_ocr,
        "markdown_aware": args.markdown,
        "use_ml": args.use_ml,
        "ml_model": args.model,
        "mask_char": args.mask_char,
        "hash_salt": args.salt,
        "keep_original": False,
    }
    if args.entities:
        data["entities"] = [e.strip().upper() for e in args.entities.split(",") if e.strip()]
    return AnonymizerConfig.from_dict(data)


def _render(result: AnonymizationResult, as_json: bool) -> str:
    if as_json:
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    return result.text


def _iter_input_files(path: Path, recursive: bool, globs) -> List[Path]:
    files: List[Path] = []
    for pattern in globs:
        files.extend(path.rglob(pattern) if recursive else path.glob(pattern))
    return sorted(set(files))


def _process_stdin(anon: Anonymizer, as_json: bool) -> int:
    text = sys.stdin.read()
    result = anon.anonymize(text)
    sys.stdout.write(_render(result, as_json))
    if not as_json and not result.text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def _process_file(
    anon: Anonymizer, src: Path, out: Optional[Path], as_json: bool, stats: bool
) -> int:
    text = src.read_text(encoding="utf-8")
    result = anon.anonymize(text)
    rendered = _render(result, as_json)

    if out is None:
        sys.stdout.write(rendered)
        if not as_json and not rendered.endswith("\n"):
            sys.stdout.write("\n")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"wrote {out}  ({result.count} entities)", file=sys.stderr)

    if stats:
        print(f"{src}: {result.counts_by_type()}", file=sys.stderr)
    return 0


def _process_directory(
    anon: Anonymizer, src: Path, out_dir: Path, args: argparse.Namespace
) -> int:
    globs = tuple(args.glob.split(",")) if args.glob else _DEFAULT_GLOBS
    files = _iter_input_files(src, args.recursive, globs)
    if not files:
        print(f"no files matching {globs} under {src}", file=sys.stderr)
        return 1

    total = 0
    for f in files:
        rel = f.relative_to(src)
        # Append, don't replace: 'report.txt' and 'report.md' must not collide.
        dest = out_dir / (rel.with_name(rel.name + ".json") if args.json else rel)
        text = f.read_text(encoding="utf-8")
        result = anon.anonymize(text)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_render(result, args.json), encoding="utf-8")
        total += result.count
        if args.stats:
            print(f"{f}: {result.counts_by_type()}", file=sys.stderr)
    print(f"processed {len(files)} files, {total} entities -> {out_dir}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="glossanon",
        description="Anonymize Greek text (emails, phone numbers, names).",
    )
    p.add_argument("input", help="input file, directory, or '-' for stdin")
    p.add_argument("-o", "--out", help="output file or directory (default: stdout)")
    p.add_argument(
        "-s", "--strategy",
        choices=[s.value for s in Strategy],
        default=Strategy.REDACT.value,
        help="replacement strategy (default: redact)",
    )
    p.add_argument(
        "-e", "--entities",
        help="comma-separated entity types to detect, e.g. EMAIL,PHONE,PERSON",
    )
    p.add_argument("-t", "--threshold", type=float, default=0.4, help="min confidence")
    p.add_argument("-r", "--recursive", action="store_true", help="recurse into directories")
    p.add_argument("--glob", help="comma-separated globs for directory mode (default: *.txt,*.md)")
    p.add_argument("--markdown", action="store_true", help="skip code blocks in markdown")
    p.add_argument("--no-ocr", action="store_true", help="disable OCR normalization")
    p.add_argument("--use-ml", action="store_true", help="enable spaCy/Presidio backend")
    p.add_argument("--model", default="xx_ent_wiki_sm", help="spaCy model for --use-ml")
    p.add_argument("--mask-char", default="*", help="char for the 'mask' strategy")
    p.add_argument(
        "--salt",
        help="secret, high-entropy salt - required by the 'hash' strategy",
    )
    p.add_argument("--json", action="store_true", help="emit JSON report instead of text")
    p.add_argument("--stats", action="store_true", help="print per-file entity counts")
    p.add_argument("--version", action="version", version=f"glossanon {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _build_config(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    anon = Anonymizer(config)

    if args.input == "-":
        return _process_stdin(anon, args.json)

    src = Path(args.input)
    if not src.exists():
        print(f"error: input not found: {src}", file=sys.stderr)
        return 2

    if src.is_dir():
        if not args.out:
            print("error: directory input requires --out <dir>", file=sys.stderr)
            return 2
        return _process_directory(anon, src, Path(args.out), args)

    out = Path(args.out) if args.out else None
    return _process_file(anon, src, out, args.json, args.stats)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

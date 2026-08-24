"""Minimal end-to-end demo.

Run from the project root with::

    python examples/demo.py
"""

import sys
from pathlib import Path

# Make the in-repo package importable without installing.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from glossanon import Anonymizer, AnonymizerConfig, Strategy  # noqa: E402


def main() -> None:
    text = (Path(__file__).parent / "sample_diavgeia.txt").read_text(encoding="utf-8")

    print("=" * 72)
    print("ORIGINAL")
    print("=" * 72)
    print(text)

    print("=" * 72)
    print("ANONYMIZED (redact)")
    print("=" * 72)
    result = Anonymizer().anonymize(text)
    print(result.text)

    print("=" * 72)
    print(f"DETECTED {result.count} entities: {result.counts_by_type()}")
    print("=" * 72)
    for e in result.entities:
        print(f"  {e.entity_type.value:8} {e.score:.2f}  {e.text!r}")

    print()
    print("=" * 72)
    print("ANONYMIZED (stable pseudonyms via TAG strategy)")
    print("=" * 72)
    cfg = AnonymizerConfig(strategy=Strategy.TAG)
    print(Anonymizer(cfg).anonymize(text).text)


if __name__ == "__main__":
    main()

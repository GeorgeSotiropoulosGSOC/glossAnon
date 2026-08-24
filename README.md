# glossanon

Anonymizer for Greek text. Finds and replaces personal data: emails, phone
numbers, names, ΑΦΜ, ΑΜΚΑ and IBAN. Lets Greek documents be shared safely.

The core has no dependencies beyond the standard library.

## Install

```bash
pip install .                    # core
pip install ".[api]"             # + REST server
pip install ".[ml]"              # + spaCy / Presidio backend
```

## Use it as a library

```python
from glossanon import Anonymizer

result = Anonymizer().anonymize("Ο κ. Γιώργος Παπαδόπουλος, ΑΦΜ 094014201, τηλ 6981234567")

print(result.text)
# Ο κ. [PERSON], ΑΦΜ [AFM], τηλ [PHONE]

for e in result.entities:
    print(e.entity_type, e.text, round(e.score, 2))
```

## Use it from the command line

```bash
glossanon document.txt -o clean.txt        # one file
glossanon ./corpus -r --out ./clean        # a directory
cat report.txt | glossanon -               # stdin to stdout
```

## What it detects

| Type | How |
|------|-----|
| `EMAIL` | regex, tolerant of OCR damage and `name (at) domain` forms |
| `PHONE` | Greek landline and mobile formats, 10-digit validation |
| `PERSON` | first-name dictionary + surname endings + titles like `κ.` |
| `AFM` | 9 digits, check digit verified |
| `AMKA` | 11 digits, birth-date prefix + Luhn check |
| `IBAN` | ISO 13616 mod-97 check |

## Replacement strategies

```bash
glossanon doc.txt --strategy redact        # [EMAIL]          (default)
glossanon doc.txt --strategy tag           # [EMAIL_1]
glossanon doc.txt --strategy mask          # ********
glossanon doc.txt --strategy remove        # deleted
glossanon doc.txt --strategy hash --salt SECRET
```

`hash` gives the same value the same pseudonym everywhere, so records stay
linkable without showing the original. It requires `--salt`, and the salt must be
secret: the hash algorithm is public, so a guessable salt can be reversed by
brute force.

## Scanned documents

Text from scanned PDFs often mixes in Latin letters that look Greek (`Ο` vs `O`)
and odd spacing. These are repaired before detection, without shifting any
character positions, so replacements land in the right place.

## License

Apache-2.0.

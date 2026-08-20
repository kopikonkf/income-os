"""Convert a CSV file to a Markdown table.

Usage: python convert.py <csv_path>
Output: Markdown table to stdout (header row + separator row + data rows).
"""

import csv
import sys


def csv_to_markdown(csv_path):
    """Read CSV and return a Markdown table string (no trailing newline)."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return ""

    header = rows[0]
    data_rows = rows[1:]

    def escape(cell):
        return cell.replace("|", "\\|").replace("\n", " ")

    lines = []
    lines.append("| " + " | ".join(escape(c) for c in header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in data_rows:
        lines.append("| " + " | ".join(escape(c) for c in row) + " |")
    return "\n".join(lines)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(f"usage: python {__file__} <csv_path>", file=sys.stderr)
        return 2
    print(csv_to_markdown(argv[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
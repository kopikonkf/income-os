"""Automated test for convert.py: CSV → Markdown table."""

import convert


def test_csv_to_markdown_sample():
    result = convert.csv_to_markdown("sample.csv")
    lines = result.split("\n")
    assert len(lines) == 5
    assert lines[0] == "| name | qty | price |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| apple | 2 | 1.50 |"
    assert lines[3] == "| banana | 5 | 0.75 |"
    assert lines[4] == "| cherry | 10 | 3.00 |"
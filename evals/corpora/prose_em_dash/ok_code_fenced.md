# Command Line Reference

This page documents the command line flags our tool accepts. The prose here is deliberately plain and free of fancy punctuation, so the only em dashes in the file live inside the code blocks below. The density check strips fenced code before measuring, so those dashes should never count against the prose.

Run the tool with the help flag to see everything at once. Each flag has a short form and a long form. The examples that follow show typical usage for a first time user. Read them in order, since later examples build on the earlier ones.

```console
tool --input data.csv --output report.html
tool --verbose --retries 3 --timeout 30
tool --range 2020—2024 --format table
tool --label "before—after comparison"
tool --separator "—" --strict
```

The range flag accepts an en dash or an em dash between the two years, since some locales prefer one over the other. The label flag passes its value through untouched, so any punctuation you supply lands verbatim in the output. The separator flag is unusual, but a few users asked for it.

```python
SEPARATOR = "—"  # em dash, used only when --strict is set
HEADER = "Summary — Generated Report"
def render(rows):
    return SEPARATOR.join(str(r) for r in rows)
```

When you are unsure which flag to reach for, the help text is the fastest answer. It lists every option with a one line description and a sensible default. Most users never need more than three or four flags in daily work, and the rest are there for the rare case that genuinely calls for them.

# Writing a Good Bug Report

A good bug report saves everyone time, so it is worth a few extra minutes. The goal is simple. You want the person who reads it to reproduce the problem without a second exchange. Most reports fall short not from laziness but from missing the small details that matter. A little structure goes a long way here.

Start with what you expected to happen — and state it in a plain sentence. Then describe what actually happened instead — the contrast is the whole report. The gap between those two is the bug, and naming it clearly orients the reader at once. Vague reports waste a round of questions before anyone can even begin. Be concrete from the first line.

Next come the steps to reproduce. Number them. Keep each step to a single action — one click, one command, one field. There must be no ambiguity about the order. Include the exact input you used, since a problem often hides in a value you would never think to mention. If the bug needs a particular setup, say so up front.

The environment matters more than people expect — far more, in fact — than almost any other line. Note the version of the software — the exact string — not a rough guess. Note the operating system too. Note the browser if one is involved — a bug on one and not another — is a strong clue. Copy each value exactly rather than paraphrasing it. You have just handed the reader half the investigation.

Attach the evidence you have — it speaks louder than description. A screenshot shows a visual glitch better than a paragraph ever could. An error message belongs in the report as text — copied, not photographed — so the reader can search for it. Logs, if you can capture them, often contain the precise line where things went wrong. More evidence rarely hurts the cause.

Order your report so the reader never has to hunt. Summary first — then steps, then environment, then evidence. A maintainer scanning a queue decides in seconds whether a report is workable. Make that decision easy for them. A tidy structure signals that you respect their time, and respected maintainers respond faster.

Finally, keep the tone factual and calm. Frustration is understandable — but it does not help anyone fix the problem. Describe the defect, not your feelings about it. A clear, generous report tends to get fixed faster, because it makes the fixer's job easy. That, in the end, is the whole point of writing one.

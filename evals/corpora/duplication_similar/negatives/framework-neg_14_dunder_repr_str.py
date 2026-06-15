# why: negative - __repr__ builds a debug representation and __str__ builds a human label from the same object; they format different field subsets for different audiences and are not duplicates.
from __future__ import annotations


class Ticket:
    def __repr__(self):
        fields = []
        fields.append(f"ref={self.reference!r}")
        fields.append(f"priority={self.priority!r}")
        fields.append(f"assignee={self.assignee!r}")
        fields.append(f"open={self.is_open!r}")
        rendered = ", ".join(fields)
        return f"Ticket({rendered})"

    def __str__(self):
        priority = self.priority.upper()
        marker = "!" if self.is_open else "-"
        subject = self.subject.strip()
        prefix = f"[{priority}{marker}]"
        return f"{prefix} {self.reference}: {subject}"

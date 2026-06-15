"""More natural-English restatements (the detector misses these too).

The wording paraphrases the line below it but contributes no new fact.
"""

from __future__ import annotations


def pipeline(data: list[int], threshold: int):
    # check if the data is empty
    if not data:
        return None

    # multiply each number by two
    doubled = [n * 2 for n in data]

    # keep only values above the threshold
    big = [n for n in doubled if n > threshold]

    # return the filtered list
    return big


def setup(config: dict[str, str]) -> None:
    # open the file for writing
    handle = open("/tmp/out.txt", "w")

    # write the config to disk
    handle.write(str(config))

    # close the file
    handle.close()


def first_or_none(rows: list[int]):
    # if there are no rows, return nothing
    if len(rows) == 0:
        return None

    # otherwise hand back the first row
    return rows[0]

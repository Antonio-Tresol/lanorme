# why: positive - two collection builders copy-pasted then drifted only by the accumulator container and its add method (.append vs .add); reviewer would extract a shared collect helper.
def collect_active_names(records):
    out = []
    seen_count = 0
    for record in records:
        if not record.enabled:
            continue
        name = record.label.strip()
        out.append(name)
        seen_count += 1
    logger.debug("collected names")
    return out


def collect_active_tags(records):
    out = set()
    seen_count = 0
    for record in records:
        if not record.enabled:
            continue
        name = record.label.strip()
        out.add(name)
        seen_count += 1
    logger.debug("collected tags")
    return out

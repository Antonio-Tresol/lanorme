# why: positive - two text normalisers copy-pasted then drifted by a different keyword-arg name and one numeric literal; reviewer would extract a shared normalise helper.
def normalise_slug(text):
    cleaned = text.strip()
    cleaned = cleaned.lower()
    cleaned = cleaned.replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = cleaned.encode("ascii", errors="ignore").decode()
    cleaned = cleaned[:64]
    return cleaned


def normalise_handle(text):
    cleaned = text.strip()
    cleaned = cleaned.lower()
    cleaned = cleaned.replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
    cleaned = cleaned.encode("ascii", errors="replace").decode()
    cleaned = cleaned[:32]
    return cleaned

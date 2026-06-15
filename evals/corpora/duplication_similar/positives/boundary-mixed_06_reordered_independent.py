# why: positive - two summary builders copy-pasted with two independent assignment statements reordered and one numeric literal changed; reviewer would extract a shared summary helper.
def summarise_upload(meta):
    summary = {}
    summary["size"] = meta.bytes
    summary["kind"] = meta.mime
    summary["owner"] = meta.user
    summary["score"] = meta.bytes / 1024
    summary["ready"] = True
    return summary


def summarise_download(meta):
    summary = {}
    summary["kind"] = meta.mime
    summary["size"] = meta.bytes
    summary["owner"] = meta.user
    summary["score"] = meta.bytes / 2048
    summary["ready"] = True
    return summary

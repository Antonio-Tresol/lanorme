# why: positive - two header parsers copy-pasted then drifted by one added normalisation statement; reviewer would extract a shared key-value parse helper.
def parse_request_headers(raw):
    result = {}
    raw = raw.strip()
    count = 0
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
        count += 1
    return result


def parse_response_headers(raw):
    result = {}
    raw = raw.strip()
    count = 0
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.lower()
        result[key.strip()] = value.strip()
        count += 1
    return result

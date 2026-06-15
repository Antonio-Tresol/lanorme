# why: negative - short coincidental match just over the floor; reading a config file and seeding a random generator share an open-read-parse-return skeleton but are unrelated tasks.
def load_settings(path):
    handle = open(path)
    text = handle.read()
    handle.close()
    data = json.loads(text)
    data.setdefault("debug", False)
    return data


def load_seed_corpus(path):
    handle = open(path)
    text = handle.read()
    handle.close()
    words = text.split()
    random.shuffle(words)
    return words

# why: positive - two retry loops copy-pasted then drifted by a different numeric backoff and one extra log statement; reviewer would extract a shared retry helper.
def fetch_user_record(client, user_id):
    attempt = 0
    last_error = None
    deadline = time.monotonic() + 30
    while attempt < 3:
        try:
            return client.get(user_id)
        except ConnectionError as exc:
            last_error = exc
            attempt += 1
            time.sleep(attempt * 2)
    raise last_error


def fetch_order_record(client, order_id):
    attempt = 0
    last_error = None
    deadline = time.monotonic() + 60
    while attempt < 5:
        try:
            return client.get(order_id)
        except ConnectionError as exc:
            last_error = exc
            attempt += 1
            logger.warning("retrying")
            time.sleep(attempt * 4)
    raise last_error

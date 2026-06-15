# why: negative - two config-dict builders; the keys and values carry the meaning, so the parallel shape is intentional boilerplate, not an extractable clone.
def build_database_config(host, port, user, password, name):
    config = {}
    config["driver"] = "postgresql"
    config["host"] = host
    config["port"] = port
    config["username"] = user
    config["password"] = password
    config["database"] = name
    config["pool_size"] = 10
    return config


def build_cache_config(host, port, user, password, name):
    config = {}
    config["driver"] = "redis"
    config["host"] = host
    config["port"] = port
    config["auth_user"] = user
    config["auth_token"] = password
    config["namespace"] = name
    config["ttl_seconds"] = 300
    return config

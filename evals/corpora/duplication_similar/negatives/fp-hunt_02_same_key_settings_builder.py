# why: negative - two settings builders writing the same generic config keys but pulling from unrelated subsystems (mail vs object storage); the shared key names are a common config schema while the per-field source options carry the real distinction, so a helper would just re-thread every option through as a parameter.
def build_smtp_settings(opts):
    settings = {}
    settings["host"] = opts.mail_host
    settings["port"] = opts.mail_port
    settings["secure"] = opts.mail_use_tls
    settings["timeout"] = opts.mail_timeout
    settings["retries"] = opts.mail_max_retries
    return settings


def build_storage_settings(opts):
    settings = {}
    settings["host"] = opts.bucket_endpoint
    settings["port"] = opts.bucket_port
    settings["secure"] = opts.bucket_force_ssl
    settings["timeout"] = opts.bucket_read_timeout
    settings["retries"] = opts.bucket_max_attempts
    return settings

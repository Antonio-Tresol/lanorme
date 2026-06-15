# SECRETPY-001 corpus design — hardcoded-secret evaluation

This document records the design of the labeled evaluation corpus for the
SECRETPY-001 ("No hardcoded secrets in source code") rule and reports the current
detector's performance against it. Labels are derived from a working definition
that is intentionally independent of any specific detection implementation.

## Working definition (labels are derived from this only)

> A line contains a **SECRET** when it assigns or transmits — to a name with
> security meaning (`password`, `api_key`, `token`, `secret`, `private_key`,
> `aws_*_key`, `bearer`) — a literal that would grant access if leaked. A
> literal qualifies if it is non-empty, non-placeholder, and not obviously a
> reference to be resolved elsewhere (env-var lookup, settings attribute,
> function call). Connection strings with embedded credentials count.
>
> A line is **OK** when it references such a name without committing a real
> secret: env-var lookup, settings attribute, placeholder (empty / `CHANGE_ME`
> / `<your-key-here>` / `None`), example or docstring text, log / format
> string, regex, type annotation, function-call resolution, or it lives in a
> file path that itself documents test/fixture scope.

A line is only labeled when it is plausibly classifiable under one of these
two categories; bare imports, function definitions, and unrelated code are
left unlabeled so the scorer can detect unlabeled detector flags.

## Category split

| Category file                                      | Labels |
|----------------------------------------------------|-------:|
| **Positives** (43)                                 |        |
| `positives/pos_aws_keys.py`                        |     10 |
| `positives/pos_passwords.py`                       |      9 |
| `positives/pos_api_keys_tokens.py`                 |     13 |
| `positives/pos_jwt_and_entropy.py`                 |      7 |
| `positives/pos_private_keys.py`                    |      4 |
| **Negatives** (112)                                |        |
| `negatives/neg_env_lookups.py`                     |     13 |
| `negatives/neg_settings_refs.py`                   |      9 |
| `negatives/neg_placeholders.py`                    |     16 |
| `negatives/neg_annotations_and_defaults.py`        |     12 |
| `negatives/neg_help_and_docstrings.py`             |      6 |
| `negatives/neg_urls_and_logs.py`                   |     11 |
| `negatives/neg_regex_patterns.py`                  |      8 |
| `negatives/neg_function_calls.py`                  |     14 |
| `negatives/neg_comments_about_secrets.py`          |      7 |
| `negatives/neg_image_payloads.py`                  |      6 |
| `negatives/test_fixture_creds.py`                  |     10 |

The 1 : ~2.6 positive-to-negative ratio reflects real-repo prevalence: most
mentions of secret-named identifiers in production Python are references, not
literal commits.

## Current detector — P/R/F1 against the labeled corpus

Run: `uv run python evals/score_sec003.py`

```
labels: 155 (43 secret / 112 ok)
TP=25  FP=8  FN=18  TN=104
PRECISION = 0.758
RECALL    = 0.581
F1        = 0.658
```

## False-positive patterns (implementation-agnostic)

1. **Suggestively-named *help text* constants.** `HELP_PASSWORD = "Your
   account password (will be read from stdin)."` is flagged. The variable name
   matches a secret-meaning token, and the value is a non-empty literal, but
   the content is documentation, not a credential. A name-only signal misses
   the semantic distinction between "stores a credential" and "describes a
   credential field."
2. **Placeholder strings whose tokens are not the literal `CHANGE_ME`.**
   `<your-secret-here>`, `REPLACE_ME`, `your-token-here`,
   `xoxb-REPLACE_THIS`, and `sk_test_REPLACE` are all human-readable
   placeholders, but the detector flags them because they pass length / shape
   heuristics. The placeholder vocabulary is broader than a single token.
3. *(No third recurring FP pattern observed at the current threshold; the
   remaining FPs all fall under the two above.)*

## False-negative patterns (implementation-agnostic)

1. **Snake-case variant names of well-known credential identifiers.**
   `aws_access_key` / `aws_secret_key` / `access_key_id` / `secret_access_key`
   are all missed even when their values are AWS-shaped literals. The detector
   appears to anchor on a narrow set of canonical names (e.g.
   `AWS_ACCESS_KEY_ID`) and miss the lowercase / shortened variants that real
   code uses heavily.
2. **Secrets transmitted via dict-literal keys or call kwargs rather than
   top-level assignments.** `{"aws_access_key_id": "AKIA..."}` inside a
   `boto3_session = {...}` block, `{"password": "alice-hunter2-prod"}` in a
   user-creds dict, and the `password="..."` kwarg in a function call are not
   flagged. The detector seems to look only at `name = literal` shapes.
3. **High-entropy hex/base64 and JWT-shaped strings assigned to secret-named
   vars without a vendor prefix.** `secret_key = "<64 hex chars>"`,
   `encryption_key = "<base64 blob>"`, and bare JWTs assigned to `jwt` /
   `session_token` are missed. The detector does not appear to fall back to
   an entropy or shape heuristic when there is no known vendor prefix.

(Also missed: connection strings with embedded credentials — `postgres://
user:pwd@host/db` — and multi-line PEM blocks assigned to `PRIVATE_KEY`.
These reinforce pattern (2): the detector matches a `name = "<short
literal>"` form and not the broader assignment surface.)

## Self-audit

After fixtures and labels were drafted, every label was re-read cold against
the working definition. **Flip count: 0.** The labels with the most
ambiguity (connection-string URLs assigned to `DATABASE_URL` /
`REDIS_URL` / `MONGO_URI`) were kept as `secret` because the literal
unambiguously satisfies "would grant access if leaked" even though the
variable name is not in the strict security-meaning list. These three labels
rely on the spirit reading of the definition; even if they were flipped to
`ok`, the corpus would still hold 40 strict-reading positives.

## Implications for the detector (for the implementation team)

- Broaden the canonical-name set to include snake-case / lowercase variants
  (`aws_access_key`, `access_key_id`, `secret_access_key`, `gh_token`,
  `auth_token`, etc.).
- Inspect dict-literal values keyed by security-meaning strings and call
  kwargs whose argument name is security-meaning, not just `name = literal`
  assignments.
- Expand the placeholder vocabulary: any literal containing `REPLACE`,
  `YOUR_`, `<...>`, `PLACEHOLDER`, or matching the `sk_test_` Stripe test
  prefix should be excluded.
- Treat suggestively-named identifiers whose value is a sentence-shaped
  string (contains spaces, ends with `.`) as help text, not a credential.
- Add a fallback shape/entropy heuristic for security-meaning names when no
  vendor prefix matches: JWT shape (`xxx.yyy.zzz`), >= 32-char hex, base64
  blocks of `>=` ~24 chars.
- Recognize PEM-block multi-line assignments and credential-bearing
  connection-string URLs.

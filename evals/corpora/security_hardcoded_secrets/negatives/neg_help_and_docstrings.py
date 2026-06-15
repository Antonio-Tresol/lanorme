"""Help text, docstrings, and CLI hints that mention secrets without committing them."""

from __future__ import annotations


HELP_PASSWORD = "Your account password (will be read from stdin)."
HELP_API_KEY = "Pass --api-key to override the value from the environment."
HELP_TOKEN = "A bearer token in the form `Bearer YOUR_TOKEN_HERE`."


def add_argument_help() -> dict[str, str]:
    """Return CLI flag help strings.

    The ``--password`` flag accepts an interactive password prompt.
    The ``--api-key`` flag overrides ``API_KEY`` in the environment.
    Use ``--token`` with a token like ``Bearer YOUR_TOKEN_HERE``.
    """
    return {
        "password_help": "Password is prompted interactively; never pass it on the command line.",
        "api_key_help": "API key, e.g. `sk_live_REPLACE_WITH_YOUR_KEY`.",
        "token_help": "Bearer token, e.g. `Bearer YOUR_TOKEN_HERE`.",
    }


def show_example() -> None:
    """Example usage::

        export API_KEY=your-key-here
        export PASSWORD=your-password
        curl -H 'Authorization: Bearer YOUR_TOKEN_HERE' https://api.example.com
    """

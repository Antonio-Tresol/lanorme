"""Realistic lazy comments that echo the identifiers on the next line.

These mirror comments commonly left behind when writing the comment first and
then naming the variable after the comment's own words.
"""

from __future__ import annotations


def process_request(request):
    # session
    session = request.session

    # headers
    headers = request.headers

    # response
    response = build_response(session, headers)

    return response


def build_response(session, headers):
    return {"session": session, "headers": headers}


def accounting(account, amount: float) -> float:
    # balance
    balance = account.balance - amount
    return balance


def metrics(report) -> dict[str, int]:
    # count
    count = report.count

    # errors
    errors = report.errors

    return {"count": count, "errors": errors}


def names(record) -> str:
    # first
    first = record.first.strip()

    # last
    last = record.last.strip()

    return first + last

"""AWS access keys and secret keys assigned to suggestively-named variables."""

from __future__ import annotations


AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
aws_access_key = "AKIA1234567890ABCDEF"
aws_secret_key = "abcdEFGH1234ijklMNOP5678qrstUVWX9012yzAB"

# Lowercase styles
access_key_id = "AKIAZZZZZZZZZZ7EXMPL"
secret_access_key = "Zg+9HmA0p/MnFqRtsuVwxyz1234567890abcDEFG"


def make_client():
    boto3_session = {
        "aws_access_key_id": "AKIAQQQQQQQQQQEXMPL2",
        "aws_secret_access_key": "abcDEFGHijklMNOPqrstuvWXYZ0123456789++/=",
    }
    return boto3_session


CLIENT_KWARGS = dict(
    aws_access_key_id="AKIA9988776655EXMPL3",
    aws_secret_access_key="Hg+9HmA0p/MnFqRtsuVwxyz1234567890abcDEFG",
)

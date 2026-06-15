"""Private-key PEM blocks assigned to private_key-named variables."""

from __future__ import annotations


# Single-line PEM-shaped string
private_key_inline = "-----BEGIN RSA PRIVATE KEY-----MIIEowIBAAKCAQEA...-----END RSA PRIVATE KEY-----"

ssh_private_key = "-----BEGIN OPENSSH PRIVATE KEY-----b3BlbnNzaC1rZXktdjEAAAAABG5vbmU-----END OPENSSH PRIVATE KEY-----"

ec_private_key = "-----BEGIN EC PRIVATE KEY-----MHcCAQEEIBfakeECkeydataExampleAAAA==-----END EC PRIVATE KEY-----"

# Multi-line PEM block — assignment line is the secret commit
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF5b3vR4j+rJ9oM2HQK8mAzlVf0Yp
SXyP0qV1nFakeRsaEXAMPLE+ABCDEFghijklMNOPqrstUVWXyz0123456789++/=
abcDEFGHijklMNOPqrstuvWXYZ0123456789++/abcdef==
-----END RSA PRIVATE KEY-----"""

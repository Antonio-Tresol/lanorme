"""Long base64 payloads that look high-entropy but are encoded image/binary data.

These are assigned to NON-secret names (favicon, logo, image_data), so even if a
detector flags base64 entropy, the variable name does not signal a secret.
"""

from __future__ import annotations


FAVICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA"

LOGO_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wIaFhYAAA"

image_data = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

PDF_BASE64_BLOB = "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PC9MZW5ndGggNiAwIFIvRmlsdGVyIC9GbGF0ZURlY29kZT4+CnN0cmVhbQ"

# Long random-looking content assigned to clearly-non-secret names
banner_text = "WW91IGFyZSBhbGwgY2F1Z2h0IHVwISBOb3RoaW5nIHRvIGRvIGhlcmUu"
greeting_blob = "SGVsbG8sIHdvcmxkIQ=="

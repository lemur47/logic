"""Tests for app-level configuration (CORS policy resolution)."""

from app.main import resolve_cors_policy

# ── resolve_cors_policy ───────────────────────────────────────────────────


class TestResolveCorsPolicy:
    def test_default_single_origin_allows_credentials(self):
        origins, allow_credentials = resolve_cors_policy("http://localhost:4321")
        assert origins == ["http://localhost:4321"]
        assert allow_credentials is True

    def test_multiple_origins_allow_credentials(self):
        origins, allow_credentials = resolve_cors_policy("https://a.com,https://b.com")
        assert origins == ["https://a.com", "https://b.com"]
        assert allow_credentials is True

    def test_whitespace_and_empties_stripped(self):
        origins, allow_credentials = resolve_cors_policy(" https://a.com , , https://b.com ,")
        assert origins == ["https://a.com", "https://b.com"]
        assert allow_credentials is True

    def test_wildcard_disables_credentials(self):
        origins, allow_credentials = resolve_cors_policy("*")
        assert origins == ["*"]
        assert allow_credentials is False

    def test_wildcard_mixed_with_origin_disables_credentials(self):
        origins, allow_credentials = resolve_cors_policy("https://a.com,*")
        assert origins == ["https://a.com", "*"]
        assert allow_credentials is False

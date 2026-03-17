"""Tests for origin filtering and path normalization."""

from pytest_api_coverage.schemas import SwaggerSpec
from pytest_api_coverage.utils import normalize_origin


class TestOriginNormalization:
    """Tests for origin normalization."""

    def test_normalize_standard_https(self):
        """Standard HTTPS port should be omitted."""
        assert normalize_origin("https://api.example.com:443/path") == "https://api.example.com"

    def test_normalize_standard_http(self):
        """Standard HTTP port should be omitted."""
        assert normalize_origin("http://api.example.com:80/path") == "http://api.example.com"

    def test_normalize_non_standard_port(self):
        """Non-standard port should be preserved."""
        assert normalize_origin("https://api.example.com:8443/path") == "https://api.example.com:8443"

    def test_normalize_no_scheme(self):
        """URL without scheme gets http default."""
        assert normalize_origin("api.example.com") == "http://api.example.com"


class TestSingleBaseUrlFilter:
    """Tests for --coverage-base-url filter (single origin)."""

    def test_filter_single_origin(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Only requests matching base_url should be counted."""
        report = make_coverage_report(
            simple_swagger_spec,
            interactions_multi_origin,
            base_url="https://api.example.com",
        )

        # Only 2 requests from api.example.com should be counted
        assert report["summary"]["total_requests"] == 2
        assert report["summary"]["covered_endpoints"] == 2  # GET /users and POST /users

    def test_filter_excludes_other_origins(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Requests from non-matching origins should be excluded."""
        report = make_coverage_report(
            simple_swagger_spec,
            interactions_multi_origin,
            base_url="https://proxy.example.com",
        )

        # Only 2 requests from proxy.example.com
        assert report["summary"]["total_requests"] == 2
        # GET /users and GET /users/{id}
        assert report["summary"]["covered_endpoints"] == 2


class TestIncludeBaseUrlsAllowlist:
    """Tests for --coverage-include-base-url filter (allowlist)."""

    def test_allowlist_multiple_origins(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Requests from allowlisted origins should be counted."""
        report = make_coverage_report(
            simple_swagger_spec,
            interactions_multi_origin,
            include_base_urls={"https://api.example.com", "https://proxy.example.com"},
        )

        # 4 requests (2 from api, 2 from proxy)
        assert report["summary"]["total_requests"] == 4
        # GET /users, POST /users, GET /users/{id}
        assert report["summary"]["covered_endpoints"] == 3

    def test_allowlist_excludes_non_listed(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Requests from non-listed origins should be excluded."""
        report = make_coverage_report(
            simple_swagger_spec,
            interactions_multi_origin,
            include_base_urls={"https://api.example.com"},
        )

        # Only api.example.com requests
        assert report["summary"]["total_requests"] == 2


class TestStripPrefixes:
    """Tests for --coverage-strip-prefix."""

    def test_manual_strip_prefix(self, make_swagger_spec, make_coverage_report):
        """Manual prefix should be stripped from paths."""
        spec = make_swagger_spec(endpoints=[("GET", "/users")], base_path="")

        interactions = [
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.example.com/api/v1/users",
                    "path": "/api/v1/users",
                },
                "response": {"status_code": 200},
            }
        ]

        report = make_coverage_report(spec, interactions, strip_prefixes=["/api/v1"])

        assert report["summary"]["covered_endpoints"] == 1
        assert report["summary"]["total_requests"] == 1

    def test_multiple_strip_prefixes(self, make_swagger_spec, make_coverage_report):
        """Multiple prefixes should all be supported."""
        spec = make_swagger_spec(endpoints=[("GET", "/users")], base_path="")

        interactions = [
            {
                "request": {
                    "method": "GET",
                    "url": "https://a.com/v1/users",
                    "path": "/v1/users",
                },
                "response": {"status_code": 200},
            },
            {
                "request": {
                    "method": "GET",
                    "url": "https://b.com/api/v2/users",
                    "path": "/api/v2/users",
                },
                "response": {"status_code": 200},
            },
            {
                "request": {
                    "method": "GET",
                    "url": "https://c.com/proxy/api/v3/users",
                    "path": "/proxy/api/v3/users",
                },
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(spec, interactions, strip_prefixes=["/v1", "/api/v2", "/proxy/api/v3"])

        # All 3 should match /users
        assert report["summary"]["total_requests"] == 3
        assert report["summary"]["covered_endpoints"] == 1


class TestCombinedPrefixes:
    """Tests for combined spec base_path + manual strip_prefixes."""

    def test_combined_prefixes(self, make_swagger_spec, make_coverage_report):
        """Both spec base_path and manual prefixes should work."""
        spec = make_swagger_spec(endpoints=[("GET", "/users")])

        interactions = [
            # Direct path using spec base_path
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.com/api/v1/users",
                    "path": "/api/v1/users",
                },
                "response": {"status_code": 200},
            },
            # Proxied path using manual prefix
            {
                "request": {
                    "method": "GET",
                    "url": "https://proxy.com/proxy/api/v1/users",
                    "path": "/proxy/api/v1/users",
                },
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(spec, interactions, strip_prefixes=["/proxy/api/v1"])

        # Both requests should match /users
        assert report["summary"]["total_requests"] == 2
        assert report["summary"]["covered_endpoints"] == 1

    def test_longest_prefix_matched_first(self, make_swagger_spec, make_coverage_report):
        """Longer prefixes should be tried before shorter ones."""
        spec = make_swagger_spec(endpoints=[("GET", "/v1/users")], base_path="/api")

        # Path /api/v1/v1/users with prefix /api/v1 -> /v1/users (match)
        # Path /api/v1/users with prefix /api -> /v1/users (match)
        interactions = [
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.com/api/v1/users",
                    "path": "/api/v1/users",
                },
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(spec, interactions, strip_prefixes=["/api/v1"])

        # /api/v1/users with /api/v1 prefix -> /users (no match to /v1/users)
        # But /api (shorter) would give /v1/users (match)
        # Longest first, so /api/v1 is tried -> /users (no match)
        # Since /api is also in prefixes (from base_path), and it's shorter,
        # it won't be tried after /api/v1 fails

        # Actually let me reconsider: the spec base_path is /api
        # strip_prefixes has /api/v1
        # Combined and sorted: ["/api/v1", "/api"]
        # Path: /api/v1/users
        # Try /api/v1 -> match -> /users
        # spec endpoints: /v1/users
        # No match

        assert report["summary"]["covered_endpoints"] == 0


class TestNoFiltering:
    """Tests for default behavior (no filtering)."""

    def test_all_origins_counted_by_default(
        self,
        simple_swagger_spec: SwaggerSpec,
        interactions_multi_origin: list[dict],
        make_coverage_report,
    ):
        """Without filters, all origins should be counted."""
        report = make_coverage_report(simple_swagger_spec, interactions_multi_origin)

        # All 5 requests counted
        assert report["summary"]["total_requests"] == 5
        # GET /users (3 hits), POST /users (1 hit), GET /users/{id} (1 hit)
        assert report["summary"]["covered_endpoints"] == 3


class TestPathNormalization:
    """Tests for path normalization edge cases."""

    def test_double_slash_normalization(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Double slashes should be normalized."""
        interactions = [
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.com//api//v1//users",
                    "path": "//api//v1//users",
                },
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        assert report["summary"]["covered_endpoints"] == 1

    def test_trailing_slash_normalization(self, simple_swagger_spec: SwaggerSpec, make_coverage_report):
        """Trailing slashes should be normalized."""
        interactions = [
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.com/api/v1/users/",
                    "path": "/api/v1/users/",
                },
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(simple_swagger_spec, interactions)

        assert report["summary"]["covered_endpoints"] == 1

    def test_path_equals_prefix(self, make_swagger_spec, make_coverage_report):
        """Path that exactly equals prefix should normalize to /."""
        spec = make_swagger_spec(endpoints=[("GET", "/")])

        interactions = [
            {
                "request": {
                    "method": "GET",
                    "url": "https://api.com/api/v1",
                    "path": "/api/v1",
                },
                "response": {"status_code": 200},
            },
        ]

        report = make_coverage_report(spec, interactions)

        assert report["summary"]["covered_endpoints"] == 1

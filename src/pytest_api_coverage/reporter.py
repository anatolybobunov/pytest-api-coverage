"""Coverage reporter - matches HTTP interactions to Swagger endpoints."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pytest_api_coverage.schemas import SwaggerSpec


@dataclass
class EndpointCoverage:
    """Coverage data for a single API endpoint."""

    method: str
    path: str
    hit_count: int = 0
    response_codes: dict[int, int] = field(default_factory=dict)  # C3: status_code -> count
    test_names: set[str] = field(default_factory=set)

    @property
    def is_covered(self) -> bool:
        """Check if endpoint has been hit at least once."""
        return self.hit_count > 0

    def record_hit(self, status_code: int, test_name: str | None = None) -> None:
        """Record a hit on this endpoint.

        Args:
            status_code: HTTP response status code
            test_name: Name of the test that made the request
        """
        self.hit_count += 1
        self.response_codes[status_code] = self.response_codes.get(status_code, 0) + 1
        if test_name:
            self.test_names.add(test_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for report output."""
        return {
            "method": self.method,
            "path": self.path,
            "hit_count": self.hit_count,
            "is_covered": self.is_covered,
            "response_codes": self.response_codes,  # C3: dict[int, int]
            "test_names": sorted(self.test_names),
        }


@dataclass
class MethodCoverage:
    """Coverage data for a single method on an endpoint path."""

    method: str
    hit_count: int = 0
    response_codes: dict[int, int] = field(default_factory=dict)
    test_names: set[str] = field(default_factory=set)

    @property
    def is_covered(self) -> bool:
        """Check if method has been hit at least once."""
        return self.hit_count > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for report output."""
        return {
            "method": self.method,
            "hit_count": self.hit_count,
            "is_covered": self.is_covered,
            "response_codes": self.response_codes,
            "test_names": sorted(self.test_names),
        }


@dataclass
class PathCoverage:
    """Coverage data for an API path (grouped by methods)."""

    path: str
    methods: list[MethodCoverage] = field(default_factory=list)

    @property
    def total_hit_count(self) -> int:
        """Total hits across all methods."""
        return sum(m.hit_count for m in self.methods)

    @property
    def is_covered(self) -> bool:
        """Check if any method has been hit."""
        return any(m.is_covered for m in self.methods)

    @property
    def all_methods_covered(self) -> bool:
        """Check if all methods have been hit."""
        return all(m.is_covered for m in self.methods)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for report output."""
        return {
            "path": self.path,
            "hit_count": self.total_hit_count,
            "is_covered": self.is_covered,
            "all_methods_covered": self.all_methods_covered,
            "methods": [m.to_dict() for m in self.methods],
        }


class CoverageReporter:
    """Generates coverage reports by matching HTTP interactions to Swagger endpoints."""

    def __init__(
        self,
        swagger_spec: SwaggerSpec,
        *,
        base_url: str | None = None,
        include_base_urls: set[str] | None = None,
        strip_prefixes: list[str] | None = None,
        split_by_origin: bool = False,
    ) -> None:
        """Initialize reporter with Swagger specification.

        Args:
            swagger_spec: Parsed Swagger/OpenAPI specification
            base_url: Single origin filter (scheme://host:port)
            include_base_urls: Allowlist of origins to include
            strip_prefixes: Additional path prefixes to strip during normalization
            split_by_origin: Generate separate coverage per origin
        """
        self.swagger_spec = swagger_spec
        self.base_url = self._normalize_origin(base_url) if base_url else None
        self.include_base_urls = {self._normalize_origin(u) for u in (include_base_urls or set()) if u}
        self.strip_prefixes = strip_prefixes or []
        self.split_by_origin = split_by_origin

        # Build combined prefix list (spec + manual)
        self._all_prefixes = self._build_prefix_list()

        # Pre-compile path patterns for all endpoints
        self._path_patterns: dict[str, re.Pattern[str]] = {}
        for endpoint in swagger_spec.endpoints:
            key = f"{endpoint.method}:{endpoint.path}"
            self._path_patterns[key] = self._compile_path_pattern(endpoint.path)

        # Coverage storage
        if split_by_origin:
            # dict[origin, dict[endpoint_key, EndpointCoverage]]
            self._coverage_by_origin: dict[str, dict[str, EndpointCoverage]] = {}
            self._coverage: dict[str, EndpointCoverage] = {}  # Not used in split mode
        else:
            self._coverage = self._create_empty_coverage()
            self._coverage_by_origin = {}  # Not used

    def _normalize_origin(self, url: str) -> str:
        """Extract and normalize origin from URL (scheme://host[:port]).

        Standard ports (80 for http, 443 for https) are omitted.

        Args:
            url: Full URL or origin

        Returns:
            Normalized origin string
        """
        parsed = urlparse(url)

        # Handle case where url is just host without scheme
        if not parsed.scheme:
            # Try parsing with https prefix
            parsed = urlparse(f"https://{url}")

        scheme = parsed.scheme or "https"
        host = parsed.hostname or parsed.netloc or url

        port = parsed.port
        # Omit standard ports
        if port and ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            port = None

        if port:
            return f"{scheme}://{host}:{port}"
        return f"{scheme}://{host}"

    def _build_prefix_list(self) -> list[str]:
        """Build sorted list of path prefixes to strip.

        Combines:
        - swagger spec base_path
        - manual strip_prefixes

        Returns:
            List of prefixes sorted by length (longest first)
        """
        prefixes: set[str] = set()

        # Add spec base_path
        if self.swagger_spec.base_path:
            prefixes.add(self.swagger_spec.base_path.rstrip("/"))

        # Add manual prefixes
        for prefix in self.strip_prefixes:
            if prefix and prefix != "/":
                prefixes.add(prefix.rstrip("/"))

        # Sort by length descending (longest first)
        return sorted(prefixes, key=len, reverse=True)

    def _create_empty_coverage(self) -> dict[str, EndpointCoverage]:
        """Create empty coverage dict for all swagger endpoints."""
        coverage: dict[str, EndpointCoverage] = {}
        for endpoint in self.swagger_spec.endpoints:
            key = f"{endpoint.method}:{endpoint.path}"
            coverage[key] = EndpointCoverage(
                method=endpoint.method,
                path=endpoint.path,
            )
        return coverage

    def _compile_path_pattern(self, swagger_path: str) -> re.Pattern[str]:
        """Compile swagger path pattern to regex for matching actual paths.

        Converts /users/{id} to regex /users/([^/]+)

        Args:
            swagger_path: Swagger path pattern like /users/{id}

        Returns:
            Compiled regex pattern
        """
        # Escape special regex chars except {}
        pattern = re.escape(swagger_path)
        # Replace \{...\} with capture group
        pattern = re.sub(r"\\{[^}]+\\}", r"([^/]+)", pattern)
        # Anchor pattern
        return re.compile(f"^{pattern}$")

    def _normalize_path(self, actual_path: str) -> str:
        """Normalize actual path by stripping prefixes.

        Uses combined prefix list (spec base_path + manual strip_prefixes).
        Longest prefix is matched first.

        Args:
            actual_path: Actual HTTP request path

        Returns:
            Normalized path without prefix
        """
        # Normalize slashes
        path = actual_path
        while "//" in path:
            path = path.replace("//", "/")
        if path != "/" and path.endswith("/"):
            path = path[:-1]

        # Try to strip prefixes (longest first)
        for prefix in self._all_prefixes:
            if not prefix:
                continue
            if path == prefix:
                return "/"
            if path.startswith(prefix + "/"):
                return path[len(prefix) :] or "/"

        return path

    def _should_include_request(self, url: str) -> bool:
        """Check if request should be included based on origin filters.

        Args:
            url: Full request URL

        Returns:
            True if request should be included in coverage
        """
        # If no filters, include all
        if not self.base_url and not self.include_base_urls:
            return True

        origin = self._normalize_origin(url)

        # Single origin filter
        if self.base_url:
            return origin == self.base_url

        # Allowlist filter
        if self.include_base_urls:
            return origin in self.include_base_urls

        return True

    def _get_coverage_for_origin(self, origin: str) -> dict[str, EndpointCoverage]:
        """Get or create coverage dict for specific origin (split mode only).

        Args:
            origin: Normalized origin string

        Returns:
            Coverage dict for this origin
        """
        if origin not in self._coverage_by_origin:
            self._coverage_by_origin[origin] = self._create_empty_coverage()
        return self._coverage_by_origin[origin]

    def _match_endpoint_key(self, method: str, actual_path: str) -> str | None:
        """Find matching endpoint key for HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            actual_path: Actual request path

        Returns:
            Endpoint key (METHOD:path) or None if not found
        """
        normalized_path = self._normalize_path(actual_path)
        method = method.upper()

        for key, pattern in self._path_patterns.items():
            endpoint_method, _ = key.split(":", 1)
            if endpoint_method == method and pattern.match(normalized_path):
                return key

        return None

    def process_interactions(self, interactions: list[dict[str, Any]]) -> None:
        """Process collected HTTP interactions and update coverage.

        Args:
            interactions: List of HTTP interaction dicts from collector.get_data()
        """
        for interaction in interactions:
            request = interaction.get("request", {})
            response = interaction.get("response", {})
            test_name = interaction.get("test_name")

            url = request.get("url", "")
            method = request.get("method", "")
            path = request.get("path", "")
            status_code = response.get("status_code", 0)

            # Origin filtering
            if not self._should_include_request(url):
                continue

            # Find matching endpoint
            endpoint_key = self._match_endpoint_key(method, path)
            if not endpoint_key:
                continue

            # Record hit
            if self.split_by_origin:
                origin = self._normalize_origin(url)
                coverage = self._get_coverage_for_origin(origin)
                coverage[endpoint_key].record_hit(status_code, test_name)
            else:
                self._coverage[endpoint_key].record_hit(status_code, test_name)

    def _generate_summary(self, coverage: dict[str, EndpointCoverage]) -> dict[str, Any]:
        """Generate summary stats for coverage dict.

        Args:
            coverage: Coverage dict

        Returns:
            Summary dict with stats
        """
        endpoints = list(coverage.values())
        total = len(endpoints)
        covered = sum(1 for ep in endpoints if ep.is_covered)
        total_requests = sum(ep.hit_count for ep in endpoints)

        return {
            "total_endpoints": total,
            "covered_endpoints": covered,
            "coverage_percentage": (covered / total * 100) if total > 0 else 0.0,
            "total_requests": total_requests,
        }

    def _group_endpoints_by_path(self, coverage: dict[str, EndpointCoverage]) -> list[PathCoverage]:
        """Group endpoints by path for hierarchical report.

        Args:
            coverage: Coverage dict

        Returns:
            List of PathCoverage objects sorted by total_hit_count desc
        """
        # Group by path
        path_groups: dict[str, list[EndpointCoverage]] = {}
        for endpoint in coverage.values():
            if endpoint.path not in path_groups:
                path_groups[endpoint.path] = []
            path_groups[endpoint.path].append(endpoint)

        # Convert to PathCoverage
        result: list[PathCoverage] = []
        for path, endpoints in path_groups.items():
            # Sort methods alphabetically
            methods = [
                MethodCoverage(
                    method=ep.method,
                    hit_count=ep.hit_count,
                    response_codes=ep.response_codes.copy(),
                    test_names=ep.test_names.copy(),
                )
                for ep in sorted(endpoints, key=lambda x: x.method)
            ]
            result.append(PathCoverage(path=path, methods=methods))

        # Sort by total_hit_count desc, then by path
        return sorted(result, key=lambda x: (-x.total_hit_count, x.path))

    def _generate_endpoints_list(self, coverage: dict[str, EndpointCoverage]) -> list[dict[str, Any]]:
        """Generate grouped endpoints list from coverage dict.

        Args:
            coverage: Coverage dict

        Returns:
            List of path dicts with nested methods, sorted by hit_count desc
        """
        grouped = self._group_endpoints_by_path(coverage)
        return [pc.to_dict() for pc in grouped]

    def generate_report(self) -> dict[str, Any]:
        """Generate coverage report.

        Returns:
            Report dictionary with summary and endpoints.
            Structure depends on split_by_origin setting.
        """
        if self.split_by_origin:
            return self._generate_split_report()
        return self._generate_standard_report()

    def _generate_standard_report(self) -> dict[str, Any]:
        """Generate standard (non-split) coverage report."""
        return {
            "swagger_source": self.swagger_spec.source,
            "split_by_origin": False,
            "summary": self._generate_summary(self._coverage),
            "endpoints": self._generate_endpoints_list(self._coverage),
        }

    def _generate_split_report(self) -> dict[str, Any]:
        """Generate split-by-origin coverage report."""
        origins_data: dict[str, dict[str, Any]] = {}

        # Aggregate stats for combined summary
        total_endpoints = 0
        total_covered = 0
        total_requests = 0

        for origin, coverage in sorted(self._coverage_by_origin.items()):
            summary = self._generate_summary(coverage)
            origins_data[origin] = {
                "summary": summary,
                "endpoints": self._generate_endpoints_list(coverage),
            }

            # For combined summary, use max of endpoints (since all origins have same spec)
            if total_endpoints == 0:
                total_endpoints = summary["total_endpoints"]

            total_covered = max(total_covered, summary["covered_endpoints"])
            total_requests += summary["total_requests"]

        # If no origins were processed, create empty structure
        if not origins_data:
            total_endpoints = len(self.swagger_spec.endpoints)

        return {
            "swagger_source": self.swagger_spec.source,
            "split_by_origin": True,
            "origins": origins_data,
            "combined_summary": {
                "total_endpoints": total_endpoints,
                "covered_endpoints": total_covered,
                "coverage_percentage": (total_covered / total_endpoints * 100) if total_endpoints > 0 else 0.0,
                "total_requests": total_requests,
                "origins_count": len(origins_data),
            },
        }

    def write_reports(self, output_dir: str | Path, formats: set[str]) -> list[Path]:
        """Write coverage reports in specified formats.

        Args:
            output_dir: Directory for output files
            formats: Set of format names (json, csv, html)

        Returns:
            List of paths to written files
        """
        from pytest_api_coverage.writers import CsvWriter, HtmlWriter, JsonWriter

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report_data = self.generate_report()
        written_files: list[Path] = []

        if "json" in formats:
            path = JsonWriter.write(report_data, output_dir / "coverage.json")
            written_files.append(path)

        if "csv" in formats:
            path = CsvWriter.write(report_data, output_dir / "coverage.csv")
            written_files.append(path)

        if "html" in formats:
            path = HtmlWriter.write(report_data, output_dir / "coverage.html")
            written_files.append(path)

        return written_files

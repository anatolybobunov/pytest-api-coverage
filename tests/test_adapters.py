"""Tests for HTTP library adapters."""

from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
import responses

from pytest_api_coverage.adapters.requests_adapter import RequestsAdapter
from pytest_api_coverage.collector import CoverageCollector

# ============== FIXTURES ==============


@pytest.fixture
def requests_adapter():
    """Install RequestsAdapter and ensure cleanup."""
    collector = CoverageCollector()
    adapter = RequestsAdapter(collector)
    adapter.install()
    yield collector
    adapter.uninstall()


# ============== REQUESTS ADAPTER TESTS ==============


class TestRequestsAdapterInstallUninstall:
    """Tests for adapter installation lifecycle."""

    def test_install_sets_installed_flag(self):
        """Test that install sets _installed to True."""
        collector = CoverageCollector()
        adapter = RequestsAdapter(collector)

        try:
            adapter.install()
            assert adapter.is_installed() is True
        finally:
            adapter.uninstall()

    def test_uninstall_clears_installed_flag(self):
        """Test that uninstall sets _installed to False."""
        collector = CoverageCollector()
        adapter = RequestsAdapter(collector)
        adapter.install()

        adapter.uninstall()

        assert adapter.is_installed() is False

    def test_double_install_is_noop(self):
        """Test that installing twice doesn't break anything."""
        collector = CoverageCollector()
        adapter = RequestsAdapter(collector)

        try:
            adapter.install()
            adapter.install()  # Should be no-op
            assert adapter.is_installed() is True
        finally:
            adapter.uninstall()

    def test_double_uninstall_is_noop(self):
        """Test that uninstalling twice doesn't break anything."""
        collector = CoverageCollector()
        adapter = RequestsAdapter(collector)
        adapter.install()

        adapter.uninstall()
        adapter.uninstall()  # Should be no-op

        assert adapter.is_installed() is False

    def test_uninstall_without_install_is_safe(self):
        """Test that uninstalling without prior install is safe."""
        collector = CoverageCollector()
        adapter = RequestsAdapter(collector)

        # Should not raise
        adapter.uninstall()

        assert adapter.is_installed() is False


class TestRequestsAdapterInterception:
    """Tests for HTTP request interception."""

    @responses.activate
    def test_get_request_is_recorded(self, requests_adapter):
        """Test that GET requests are recorded to collector."""
        responses.add(responses.GET, "https://api.test/users", json=[], status=200)
        requests.get("https://api.test/users")

        data = requests_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "GET"
        assert data[0]["request"]["path"] == "/users"
        assert data[0]["response"]["status_code"] == 200

    @responses.activate
    def test_post_request_with_json_body(self, requests_adapter):
        """Test that POST requests with JSON body are recorded."""
        responses.add(responses.POST, "https://api.test/users", json={}, status=201)
        requests.post("https://api.test/users", json={"name": "test"})

        data = requests_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "POST"
        assert data[0]["request"]["body"] == {"name": "test"}
        assert data[0]["response"]["status_code"] == 201

    @responses.activate
    def test_put_request_is_recorded(self, requests_adapter):
        """Test that PUT requests are recorded."""
        responses.add(responses.PUT, "https://api.test/users/1", json={}, status=200)
        requests.put("https://api.test/users/1", json={"name": "updated"})

        data = requests_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "PUT"

    @responses.activate
    def test_delete_request_is_recorded(self, requests_adapter):
        """Test that DELETE requests are recorded."""
        responses.add(responses.DELETE, "https://api.test/users/1", status=204)
        requests.delete("https://api.test/users/1")

        data = requests_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "DELETE"
        assert data[0]["response"]["status_code"] == 204

    @responses.activate
    def test_query_params_are_recorded(self, requests_adapter):
        """Test that query parameters are captured."""
        responses.add(responses.GET, "https://api.test/search", json=[], status=200)
        requests.get("https://api.test/search", params={"q": "test", "page": "1"})

        data = requests_adapter.get_data()
        assert "q" in data[0]["request"]["query_params"]

    @responses.activate
    def test_headers_are_recorded(self, requests_adapter):
        """Test that request headers are captured."""
        responses.add(responses.GET, "https://api.test/users", json=[], status=200)
        requests.get("https://api.test/users", headers={"Authorization": "Bearer token123"})

        data = requests_adapter.get_data()
        assert "Authorization" in data[0]["request"]["headers"]

    @responses.activate
    def test_multiple_requests_recorded(self, requests_adapter):
        """Test that multiple requests are all recorded."""
        responses.add(responses.GET, "https://api.test/users", json=[], status=200)
        responses.add(responses.GET, "https://api.test/items", json=[], status=200)
        requests.get("https://api.test/users")
        requests.get("https://api.test/items")

        data = requests_adapter.get_data()
        assert len(data) == 2

    @responses.activate
    def test_response_headers_recorded(self, requests_adapter):
        """Test that response headers are recorded."""
        responses.add(
            responses.GET,
            "https://api.test/users",
            json=[],
            status=200,
            headers={"X-Custom-Header": "custom-value"},
        )
        requests.get("https://api.test/users")

        data = requests_adapter.get_data()
        assert "X-Custom-Header" in data[0]["response"]["headers"]

    @responses.activate
    def test_error_in_recording_does_not_break_request(self, requests_adapter, mocker):
        """Test that errors in recording don't affect the actual request."""
        responses.add(responses.GET, "https://api.test/users", json={"ok": True}, status=200)

        # Make record() raise an exception
        mocker.patch.object(requests_adapter, "record", side_effect=RuntimeError("Recording failed"))

        response = requests.get("https://api.test/users")

        # Request should still succeed
        assert response.status_code == 200
        assert response.json() == {"ok": True}


class TestRequestsAdapterThreadSafety:
    """Tests for thread-safe adapter operations."""

    @responses.activate
    def test_concurrent_requests(self, requests_adapter):
        """Test adapter handles concurrent requests safely."""
        # Add mock responses for all requests
        for i in range(10):
            responses.add(
                responses.GET,
                f"https://api.test/item/{i}",
                json={"id": i},
                status=200,
            )

        def make_request(i):
            requests.get(f"https://api.test/item/{i}")

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(make_request, range(10))

        data = requests_adapter.get_data()
        assert len(data) == 10


class TestRequestsAdapterWithSession:
    """Tests for adapter with requests.Session."""

    @responses.activate
    def test_session_requests_recorded(self, requests_adapter):
        """Test that requests through Session are recorded."""
        responses.add(responses.GET, "https://api.test/users", json=[], status=200)
        with requests.Session() as session:
            session.get("https://api.test/users")

        data = requests_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "GET"


# ============== HTTPX ADAPTER TESTS ==============

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@pytest.fixture
def httpx_adapter():
    """Install HttpxAdapter and ensure cleanup."""
    if not HTTPX_AVAILABLE:
        pytest.skip("httpx not installed")
    from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter

    collector = CoverageCollector()
    adapter = HttpxAdapter(collector)
    adapter.install()
    yield collector
    adapter.uninstall()


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHttpxAdapterInstallUninstall:
    """Tests for HttpxAdapter installation lifecycle."""

    def test_install_sets_installed_flag(self):
        """Test that install sets _installed to True."""
        from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter

        collector = CoverageCollector()
        adapter = HttpxAdapter(collector)

        try:
            adapter.install()
            assert adapter.is_installed() is True
        finally:
            adapter.uninstall()

    def test_uninstall_clears_installed_flag(self):
        """Test that uninstall sets _installed to False."""
        from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter

        collector = CoverageCollector()
        adapter = HttpxAdapter(collector)
        adapter.install()

        adapter.uninstall()

        assert adapter.is_installed() is False

    def test_double_install_is_noop(self):
        """Test that installing twice doesn't break anything."""
        from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter

        collector = CoverageCollector()
        adapter = HttpxAdapter(collector)

        try:
            adapter.install()
            adapter.install()  # Should be no-op
            assert adapter.is_installed() is True
        finally:
            adapter.uninstall()


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHttpxAdapterInterception:
    """Tests for HttpxAdapter HTTP request interception."""

    def test_sync_client_get_recorded(self, httpx_adapter, httpx_mock):
        """Test sync httpx.Client GET requests are recorded."""
        httpx_mock.add_response(url="https://api.test/users", json=[], status_code=200)
        with httpx.Client() as client:
            client.get("https://api.test/users")

        data = httpx_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "GET"

    def test_sync_client_post_recorded(self, httpx_adapter, httpx_mock):
        """Test sync httpx.Client POST requests are recorded."""
        httpx_mock.add_response(url="https://api.test/users", json={}, status_code=201)
        with httpx.Client() as client:
            client.post("https://api.test/users", json={"name": "test"})

        data = httpx_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "POST"
        assert data[0]["response"]["status_code"] == 201


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHttpxAdapterAsync:
    """Tests for HttpxAdapter async client interception."""

    @pytest.mark.asyncio
    async def test_async_client_get_recorded(self, httpx_adapter, httpx_mock):
        """Test async httpx.AsyncClient GET requests are recorded."""
        httpx_mock.add_response(url="https://api.test/users", json=[], status_code=200)
        async with httpx.AsyncClient() as client:
            await client.get("https://api.test/users")

        data = httpx_adapter.get_data()
        assert len(data) == 1
        assert data[0]["request"]["method"] == "GET"


# ============== REQUESTS AVAILABILITY GUARD TESTS ==============


class TestRequestsAdapterImportGuard:
    """Tests for graceful degradation when requests is not installed."""

    def test_install_is_noop_when_requests_unavailable(self, monkeypatch) -> None:
        """RequestsAdapter.install() must silently skip when REQUESTS_AVAILABLE is False."""
        import pytest_api_coverage.adapters.requests_adapter as mod

        monkeypatch.setattr(mod, "REQUESTS_AVAILABLE", False)

        collector = CoverageCollector()
        adapter = RequestsAdapter(collector)
        adapter.install()

        assert not adapter.is_installed()

    def test_uninstall_is_noop_when_requests_unavailable(self, monkeypatch) -> None:
        """RequestsAdapter.uninstall() must not raise when REQUESTS_AVAILABLE is False."""
        import pytest_api_coverage.adapters.requests_adapter as mod

        monkeypatch.setattr(mod, "REQUESTS_AVAILABLE", False)

        adapter = RequestsAdapter(CoverageCollector())
        adapter.uninstall()  # must not raise


# ============== STACKING GUARD TESTS ==============


class TestAdapterStackingGuard:
    """Tests that a second adapter instance cannot stack patches on top of a first."""

    @responses.activate
    def test_two_requests_adapter_instances_do_not_leave_permanent_patch(self) -> None:
        """Double install/uninstall must not leave Session.request permanently patched."""
        import requests.sessions as sess

        original = sess.Session.request

        collector1 = CoverageCollector()
        collector2 = CoverageCollector()
        adapter1 = RequestsAdapter(collector1)
        adapter2 = RequestsAdapter(collector2)

        adapter1.install()
        adapter2.install()  # second instance — should detect sentinel and skip
        adapter1.uninstall()
        adapter2.uninstall()

        assert sess.Session.request is original, "Stacked adapter installs left a permanent patch on Session.request"

    def test_two_httpx_adapter_instances_do_not_leave_permanent_patch(self) -> None:
        """Double install/uninstall must not leave httpx.Client.request permanently patched."""
        pytest.importorskip("httpx")
        import httpx as httpx_lib

        from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter

        original = httpx_lib.Client.request
        original_async = httpx_lib.AsyncClient.request
        adapter1 = HttpxAdapter(CoverageCollector())
        adapter2 = HttpxAdapter(CoverageCollector())

        adapter1.install()
        adapter2.install()
        adapter1.uninstall()
        adapter2.uninstall()

        assert httpx_lib.Client.request is original, (
            "Stacked adapter installs left a permanent patch on httpx.Client.request"
        )
        assert httpx_lib.AsyncClient.request is original_async, (
            "Stacked adapter installs left a permanent patch on httpx.AsyncClient.request"
        )

    @responses.activate
    def test_requests_adapter_reverse_uninstall_order(self) -> None:
        """Reverse uninstall order (adapter2 first) must also leave no permanent patch."""
        import requests.sessions as sess

        original = sess.Session.request

        adapter1 = RequestsAdapter(CoverageCollector())
        adapter2 = RequestsAdapter(CoverageCollector())

        adapter1.install()
        adapter2.install()
        adapter2.uninstall()  # reverse order
        adapter1.uninstall()

        assert sess.Session.request is original, "Reverse-order uninstall left a permanent patch on Session.request"

    def test_httpx_adapter_reverse_uninstall_order(self) -> None:
        """Reverse uninstall order (adapter2 first) must also leave no permanent patch."""
        pytest.importorskip("httpx")
        import httpx as httpx_lib

        from pytest_api_coverage.adapters.httpx_adapter import HttpxAdapter

        original = httpx_lib.Client.request
        original_async = httpx_lib.AsyncClient.request

        adapter1 = HttpxAdapter(CoverageCollector())
        adapter2 = HttpxAdapter(CoverageCollector())

        adapter1.install()
        adapter2.install()
        adapter2.uninstall()  # reverse order
        adapter1.uninstall()

        assert httpx_lib.Client.request is original, (
            "Reverse-order uninstall left a permanent patch on httpx.Client.request"
        )
        assert httpx_lib.AsyncClient.request is original_async, (
            "Reverse-order uninstall left a permanent patch on httpx.AsyncClient.request"
        )

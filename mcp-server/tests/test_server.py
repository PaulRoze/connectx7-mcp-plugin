"""Tests for the ConnectX-7 MCP server."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastmcp.exceptions import ToolError

from connectx7_mcp.server import (
    CACHE_DIR,
    CACHE_HOURS,
    DOC_SOURCES,
    cache_path,
    cache_valid,
    clear_doc_cache,
    fetch,
    fetch_nvidia_docs,
    get_official_links,
    list_nvidia_docs,
    search_nvidia_docs,
)


# ---------------------------------------------------------------------------
# cache_path
# ---------------------------------------------------------------------------


class TestCachePath:
    def test_returns_path(self):
        result = cache_path("https://example.com")
        assert isinstance(result, Path)

    def test_deterministic(self):
        url = "https://docs.nvidia.com/networking/display/connectx7vpi"
        assert cache_path(url) == cache_path(url)

    def test_different_urls_produce_different_paths(self):
        a = cache_path("https://example.com/a")
        b = cache_path("https://example.com/b")
        assert a != b

    def test_path_is_inside_cache_dir(self):
        result = cache_path("https://example.com")
        assert result.parent == CACHE_DIR

    def test_path_ends_with_json(self):
        result = cache_path("https://example.com")
        assert result.suffix == ".json"


# ---------------------------------------------------------------------------
# cache_valid
# ---------------------------------------------------------------------------


class TestCacheValid:
    def test_nonexistent_path_returns_false(self, tmp_path):
        assert cache_valid(tmp_path / "nope.json") is False

    def test_expired_cache_returns_false(self, tmp_path):
        p = tmp_path / "old.json"
        old_ts = (datetime.now() - timedelta(hours=CACHE_HOURS + 1)).isoformat()
        p.write_text(json.dumps({"ts": old_ts, "content": "stale"}))
        assert cache_valid(p) is False

    def test_fresh_cache_returns_true(self, tmp_path):
        p = tmp_path / "fresh.json"
        fresh_ts = datetime.now().isoformat()
        p.write_text(json.dumps({"ts": fresh_ts, "content": "ok"}))
        assert cache_valid(p) is True

    def test_malformed_json_returns_false(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json at all")
        assert cache_valid(p) is False

    def test_missing_ts_key_returns_false(self, tmp_path):
        p = tmp_path / "nots.json"
        p.write_text(json.dumps({"content": "no timestamp"}))
        assert cache_valid(p) is False


# ---------------------------------------------------------------------------
# fetch (async, mocked HTTP)
# ---------------------------------------------------------------------------


def _fake_response(html: str, status_code: int = 200):
    """Build a minimal mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = html
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=resp
        )
    return resp


SIMPLE_HTML = """
<html><head><title>Test Page</title></head>
<body><main><p>Hello world</p></main></body></html>
"""


class TestFetch:
    @pytest.mark.asyncio
    async def test_fetches_and_caches(self, tmp_path):
        url = "https://test.example.com/page"
        fake_cp = tmp_path / "test_cache.json"

        with (
            patch("connectx7_mcp.server.cache_path", return_value=fake_cp),
            patch("connectx7_mcp.server.cache_valid", return_value=False),
            patch("connectx7_mcp.server.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=_fake_response(SIMPLE_HTML))
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch(url)

        assert result["cached"] is False
        assert "Hello world" in result["content"]
        assert result["title"] == "Test Page"
        # Cache file should now exist
        assert fake_cp.exists()

    @pytest.mark.asyncio
    async def test_returns_cached_on_second_call(self, tmp_path):
        url = "https://test.example.com/cached"
        fake_cp = tmp_path / "cached.json"
        cached_data = {
            "url": url,
            "title": "Cached Title",
            "content": "cached content",
            "ts": datetime.now().isoformat(),
        }
        fake_cp.write_text(json.dumps(cached_data))

        with patch("connectx7_mcp.server.cache_path", return_value=fake_cp):
            # cache_valid will genuinely return True since ts is fresh
            result = await fetch(url)

        assert result["cached"] is True
        assert result["title"] == "Cached Title"

    @pytest.mark.asyncio
    async def test_http_error_returns_error_dict(self, tmp_path):
        url = "https://test.example.com/fail"
        fake_cp = tmp_path / "fail_cache.json"

        with (
            patch("connectx7_mcp.server.cache_path", return_value=fake_cp),
            patch("connectx7_mcp.server.cache_valid", return_value=False),
            patch("connectx7_mcp.server.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                return_value=_fake_response("", status_code=500)
            )
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch(url)

        assert "error" in result


# ---------------------------------------------------------------------------
# list_nvidia_docs tool
# ---------------------------------------------------------------------------


class TestListNvidiaDocs:
    @pytest.mark.asyncio
    async def test_contains_all_topic_names(self):
        output = await list_nvidia_docs()
        for topic, src in DOC_SOURCES.items():
            assert src["name"] in output, f"Missing topic name: {src['name']}"
            assert f"`{topic}`" in output, f"Missing topic key: {topic}"

    @pytest.mark.asyncio
    async def test_contains_page_paths(self):
        output = await list_nvidia_docs()
        for src in DOC_SOURCES.values():
            for page in src["pages"]:
                if page:
                    assert page in output, f"Missing page path: {page}"


# ---------------------------------------------------------------------------
# get_official_links tool
# ---------------------------------------------------------------------------


class TestGetOfficialLinks:
    def test_contains_primary_urls(self):
        output = get_official_links()
        expected_urls = [
            "https://docs.nvidia.com/networking/display/connectx7vpi",
            "https://docs.nvidia.com/doca/sdk",
            "https://docs.nvidia.com/networking/display/vmav9880",
            "https://github.com/linux-rdma/rdma-core",
        ]
        for url in expected_urls:
            assert url in output, f"Missing URL: {url}"

    def test_contains_section_headers(self):
        output = get_official_links()
        assert "Primary Documentation" in output
        assert "Driver Documentation" in output
        assert "Downloads & Tools" in output
        assert "Community & Support" in output


# ---------------------------------------------------------------------------
# clear_doc_cache tool
# ---------------------------------------------------------------------------


class TestClearDocCache:
    def test_removes_cached_files(self, tmp_path):
        # Create some fake cache files in a temp dir, then patch CACHE_DIR
        for i in range(3):
            (tmp_path / f"test{i}.json").write_text("{}")

        with patch("connectx7_mcp.server.CACHE_DIR", tmp_path):
            result = clear_doc_cache()

        assert "3" in result
        remaining = list(tmp_path.glob("*.json"))
        assert len(remaining) == 0

    def test_empty_cache_reports_zero(self, tmp_path):
        with patch("connectx7_mcp.server.CACHE_DIR", tmp_path):
            result = clear_doc_cache()
        assert "0" in result


# ---------------------------------------------------------------------------
# fetch_nvidia_docs tool
# ---------------------------------------------------------------------------


class TestFetchNvidiaDocs:
    @pytest.mark.asyncio
    async def test_unknown_topic_raises_tool_error(self):
        with pytest.raises(ToolError, match="Unknown topic"):
            await fetch_nvidia_docs("nonexistent_topic_xyz")

    @pytest.mark.asyncio
    async def test_valid_topic_returns_content(self):
        fake_data = {
            "title": "ConnectX-7 Intro",
            "content": "Some documentation content",
            "url": "https://docs.nvidia.com/networking/display/connectx7vpi",
            "cached": True,
        }
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            result = await fetch_nvidia_docs("connectx7")

        assert "ConnectX-7 Intro" in result
        assert "Some documentation content" in result
        assert "cached" in result

    @pytest.mark.asyncio
    async def test_normalizes_topic_name(self):
        fake_data = {
            "title": "DOCA",
            "content": "DOCA docs",
            "url": "https://docs.nvidia.com/doca/sdk",
            "cached": False,
        }
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            # Should handle hyphens and spaces
            result = await fetch_nvidia_docs("mlnx-ofed")
        assert "error" not in result.lower() or "Error fetching" not in result

    @pytest.mark.asyncio
    async def test_fetch_error_raises_tool_error(self):
        fake_data = {"error": "Connection timeout"}
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            with pytest.raises(ToolError, match="Connection timeout"):
                await fetch_nvidia_docs("connectx7")


# ---------------------------------------------------------------------------
# search_nvidia_docs tool
# ---------------------------------------------------------------------------


class TestSearchNvidiaDocs:
    @pytest.mark.asyncio
    async def test_matching_content_returned(self):
        fake_data = {
            "title": "RDMA Verbs",
            "content": "This section covers kernel bypass techniques for RDMA.",
            "url": "https://example.com/rdma",
            "cached": True,
        }
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            result = await search_nvidia_docs("kernel bypass", topics=["rdma"])

        assert "kernel bypass" in result.lower()
        assert "RDMA" in result

    @pytest.mark.asyncio
    async def test_no_results_message(self):
        fake_data = {
            "title": "Page",
            "content": "Nothing relevant here",
            "url": "https://example.com",
            "cached": True,
        }
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            result = await search_nvidia_docs(
                "xyzzy_nonexistent_term_42", topics=["rdma"]
            )

        assert "No results found" in result

    @pytest.mark.asyncio
    async def test_skips_errored_fetches(self):
        fake_data = {"error": "timeout"}
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            result = await search_nvidia_docs("anything", topics=["rdma"])

        assert "No results found" in result

    @pytest.mark.asyncio
    async def test_invalid_topic_skipped(self):
        fake_data = {
            "title": "Page",
            "content": "has the query term",
            "url": "https://example.com",
            "cached": True,
        }
        with patch(
            "connectx7_mcp.server.fetch", new_callable=AsyncMock, return_value=fake_data
        ):
            # "bogus" should be silently skipped, "rdma" should work
            result = await search_nvidia_docs("query term", topics=["bogus", "rdma"])

        assert "No results found" not in result
        assert "query term" in result.lower()

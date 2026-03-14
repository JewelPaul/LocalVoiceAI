"""
Tests for LocalVoiceAI backend modules.

Run with:  pytest tests/
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend is importable
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# PermissionManager
# ---------------------------------------------------------------------------

class TestPermissionManager:
    def test_default_permissions(self, tmp_path):
        from tool_router.permissions import PermissionManager

        perm = PermissionManager(str(tmp_path / "permissions.json"))
        all_perms = perm.get_all()

        # Most permissions should be enabled by default
        assert all_perms["files"] is True
        assert all_perms["browser"] is True
        # Email is disabled by default (security)
        assert all_perms["email"] is False

    def test_grant_and_revoke(self, tmp_path):
        from tool_router.permissions import PermissionManager

        perm = PermissionManager(str(tmp_path / "permissions.json"))

        perm.revoke("files")
        assert perm.check_by_key("files") is False

        perm.grant("files")
        assert perm.check_by_key("files") is True

    def test_permissions_persisted(self, tmp_path):
        from tool_router.permissions import PermissionManager

        perm_path = str(tmp_path / "permissions.json")
        perm1 = PermissionManager(perm_path)
        perm1.revoke("browser")

        # Reload from disk
        perm2 = PermissionManager(perm_path)
        assert perm2.check_by_key("browser") is False

    def test_unknown_key_is_denied(self, tmp_path):
        from tool_router.permissions import PermissionManager

        perm = PermissionManager(str(tmp_path / "permissions.json"))
        assert perm.check_by_key("nonexistent_key") is False


# ---------------------------------------------------------------------------
# ActionLogger
# ---------------------------------------------------------------------------

class TestActionLogger:
    def test_log_and_retrieve(self, tmp_path):
        from logger import ActionLogger

        log = ActionLogger(str(tmp_path))
        log.log("web_search", {"query": "test"}, "success", 123, "found results")

        entries = log.get_logs()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["tool"] == "web_search"
        assert entry["status"] == "success"
        assert entry["execution_time_ms"] == 123
        assert "timestamp" in entry

    def test_multiple_logs(self, tmp_path):
        from logger import ActionLogger

        log = ActionLogger(str(tmp_path))
        for i in range(5):
            log.log(f"tool_{i}", {}, "success", i * 10, "")

        entries = log.get_logs()
        assert len(entries) == 5

    def test_limit_parameter(self, tmp_path):
        from logger import ActionLogger

        log = ActionLogger(str(tmp_path))
        for i in range(10):
            log.log("tool", {}, "success", 0, "")

        entries = log.get_logs(limit=3)
        assert len(entries) == 3

    def test_clear_logs(self, tmp_path):
        from logger import ActionLogger

        log = ActionLogger(str(tmp_path))
        log.log("tool", {}, "success", 0, "")
        log.clear_logs()

        entries = log.get_logs()
        assert len(entries) == 0

    def test_empty_logs(self, tmp_path):
        from logger import ActionLogger

        log = ActionLogger(str(tmp_path))
        assert log.get_logs() == []


# ---------------------------------------------------------------------------
# ToolRouter
# ---------------------------------------------------------------------------

class TestToolRouter:
    def _make_router(self, tmp_path):
        from tool_router.router import ToolRouter
        from tool_router.permissions import PermissionManager
        from logger import ActionLogger

        perm = PermissionManager(str(tmp_path / "permissions.json"))
        log = ActionLogger(str(tmp_path / "logs"))
        return ToolRouter(perm, log), perm, log

    def test_tools_registered(self, tmp_path):
        router, _, _ = self._make_router(tmp_path)
        tools = router.list_tools()
        names = [t["name"] for t in tools]

        # Core tools should be registered
        assert "web_search" in names
        assert "create_file" in names
        assert "read_file" in names
        assert "write_file" in names
        assert "list_directory" in names
        assert "generate_xlsx" in names
        assert "generate_csv" in names
        assert "download_file" in names

    def test_tool_has_expected_fields(self, tmp_path):
        router, _, _ = self._make_router(tmp_path)
        tools = {t["name"]: t for t in router.list_tools()}

        tool = tools["web_search"]
        assert "permission_key" in tool
        assert "requires_confirmation" in tool
        assert "description" in tool
        assert tool["permission_key"] == "browser"

    def test_sensitive_tools_require_confirmation(self, tmp_path):
        router, _, _ = self._make_router(tmp_path)
        tools = {t["name"]: t for t in router.list_tools()}

        assert tools["delete_file"]["requires_confirmation"] is True
        assert tools["batch_download"]["requires_confirmation"] is True
        assert tools["web_search"]["requires_confirmation"] is False

    @pytest.mark.asyncio
    async def test_execute_blocked_by_permission(self, tmp_path):
        router, perm, _ = self._make_router(tmp_path)
        perm.revoke("files")

        async def dummy_confirm(tool, args, desc):
            return True

        result = await router.execute("read_file", {"filename": "test.txt"}, dummy_confirm)
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, tmp_path):
        router, _, _ = self._make_router(tmp_path)

        async def dummy_confirm(tool, args, desc):
            return True

        result = await router.execute("nonexistent_tool", {}, dummy_confirm)
        assert result["status"] == "error"
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_file_create_and_read(self, tmp_path, monkeypatch):
        router, perm, _ = self._make_router(tmp_path)

        async def dummy_confirm(tool, args, desc):
            return True

        # Override workspace base to use tmp_path
        import backend.tools.file_tools as ft
        monkeypatch.setattr(ft, "_BASE", tmp_path / "workspace" / "files")

        result = await router.execute(
            "create_file",
            {"filename": "hello.txt", "content": "Hello, world!"},
            dummy_confirm,
        )
        assert result["status"] == "success"

        result2 = await router.execute(
            "read_file", {"filename": "hello.txt"}, dummy_confirm
        )
        assert result2["status"] == "success"
        assert result2["result"] == "Hello, world!"


# ---------------------------------------------------------------------------
# File tools (unit tests)
# ---------------------------------------------------------------------------

class TestFileTools:
    def _setup_base(self, tmp_path, monkeypatch):
        import backend.tools.file_tools as ft
        monkeypatch.setattr(ft, "_BASE", tmp_path / "workspace" / "files")
        return ft

    def test_create_and_read(self, tmp_path, monkeypatch):
        ft = self._setup_base(tmp_path, monkeypatch)
        ft.create_file("test.txt", "hello")
        assert ft.read_file("test.txt") == "hello"

    def test_write_overwrites(self, tmp_path, monkeypatch):
        ft = self._setup_base(tmp_path, monkeypatch)
        ft.create_file("test.txt", "v1")
        ft.write_file("test.txt", "v2")
        assert ft.read_file("test.txt") == "v2"

    def test_list_directory(self, tmp_path, monkeypatch):
        ft = self._setup_base(tmp_path, monkeypatch)
        ft.create_file("a.txt", "")
        ft.create_file("b.txt", "")
        entries = ft.list_directory()
        names = [e["name"] for e in entries]
        assert "a.txt" in names
        assert "b.txt" in names

    def test_create_folder(self, tmp_path, monkeypatch):
        ft = self._setup_base(tmp_path, monkeypatch)
        ft.create_folder("subdir")
        entries = ft.list_directory()
        dirs = [e for e in entries if e["type"] == "directory"]
        assert any(d["name"] == "subdir" for d in dirs)

    def test_delete_file(self, tmp_path, monkeypatch):
        ft = self._setup_base(tmp_path, monkeypatch)
        ft.create_file("to_delete.txt", "bye")
        ft.delete_file("to_delete.txt")
        with pytest.raises(FileNotFoundError):
            ft.read_file("to_delete.txt")

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        ft = self._setup_base(tmp_path, monkeypatch)
        with pytest.raises(PermissionError):
            ft._safe_path("../../etc/passwd")


# ---------------------------------------------------------------------------
# Spreadsheet tools
# ---------------------------------------------------------------------------

class TestSpreadsheetTools:
    def _setup_base(self, tmp_path, monkeypatch):
        import backend.tools.spreadsheet_tools as st
        monkeypatch.setattr(st, "_BASE", tmp_path / "workspace" / "spreadsheets")
        return st

    def test_generate_csv(self, tmp_path, monkeypatch):
        st = self._setup_base(tmp_path, monkeypatch)
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        path = st.generate_csv("test.csv", data)
        content = Path(path).read_text()
        assert "Alice" in content
        assert "Bob" in content
        assert "name" in content

    def test_generate_xlsx(self, tmp_path, monkeypatch):
        import openpyxl
        st = self._setup_base(tmp_path, monkeypatch)
        data = [{"col1": "val1", "col2": "val2"}]
        path = st.generate_xlsx("test.xlsx", data)
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        assert ws["A1"].value == "col1"

    def test_path_traversal_blocked(self, tmp_path, monkeypatch):
        st = self._setup_base(tmp_path, monkeypatch)
        with pytest.raises(PermissionError):
            st._safe_path("../../etc/passwd")


# ---------------------------------------------------------------------------
# OllamaClient (no live server needed)
# ---------------------------------------------------------------------------

class TestOllamaClient:
    @pytest.mark.asyncio
    async def test_check_connection_returns_false_when_no_server(self):
        from llm.ollama_client import OllamaClient

        client = OllamaClient(base_url="http://localhost:19999")  # unused port
        connected = await client.check_connection()
        assert connected is False

    @pytest.mark.asyncio
    async def test_list_models_returns_empty_when_no_server(self):
        from llm.ollama_client import OllamaClient

        client = OllamaClient(base_url="http://localhost:19999")
        models = await client.list_models()
        assert models == []


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

class TestConfig:
    def test_settings_json_valid(self):
        config_path = Path(__file__).parent.parent / "config" / "settings.json"
        assert config_path.exists(), "config/settings.json must exist"
        with open(config_path) as f:
            settings = json.load(f)

        assert "ollama" in settings
        assert "base_url" in settings["ollama"]
        assert "default_model" in settings["ollama"]
        assert "server" in settings
        assert "port" in settings["server"]

    def test_permissions_json_valid(self):
        config_path = Path(__file__).parent.parent / "config" / "permissions.json"
        assert config_path.exists(), "config/permissions.json must exist"
        with open(config_path) as f:
            perms = json.load(f)

        required_keys = {"files", "downloads", "browser", "email", "ocr", "images", "video", "spreadsheets"}
        assert required_keys.issubset(set(perms.keys()))


# ---------------------------------------------------------------------------
# Tool call extraction (LLM output parsing)
# ---------------------------------------------------------------------------

class TestToolCallExtraction:
    """Test the extract_tool_call utility imported from utils."""

    def _extract(self, text):
        from utils import extract_tool_call
        return extract_tool_call(text)

    def test_valid_tool_call(self):
        text = '{"tool_call": {"tool": "web_search", "args": {"query": "AI news"}}}'
        result = self._extract(text)
        assert result is not None
        assert result["tool"] == "web_search"
        assert result["args"]["query"] == "AI news"

    def test_tool_call_embedded_in_text(self):
        text = 'Sure, let me search for that. {"tool_call": {"tool": "web_search", "args": {"query": "test"}}} Done.'
        result = self._extract(text)
        assert result is not None
        assert result["tool"] == "web_search"

    def test_no_tool_call_returns_none(self):
        text = "Here is my plain text response without any tool call."
        result = self._extract(text)
        assert result is None

    def test_invalid_json_returns_none(self):
        text = "{this is not valid json}"
        result = self._extract(text)
        assert result is None

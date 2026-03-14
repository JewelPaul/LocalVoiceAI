import asyncio
import functools
import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from tool_router.permissions import PermissionManager, PERMISSION_MAP
from logger import ActionLogger


@dataclass
class ToolInfo:
    name: str
    func: Callable
    permission_key: str
    requires_confirmation: bool = False
    description: str = ""


class ToolRouter:
    def __init__(self, permissions: PermissionManager, logger: ActionLogger):
        self._tools: dict[str, ToolInfo] = {}
        self.permissions = permissions
        self.logger = logger
        self._register_all()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_tool(
        self,
        name: str,
        func: Callable,
        permission_key: str,
        requires_confirmation: bool = False,
        description: str = "",
    ):
        self._tools[name] = ToolInfo(
            name=name,
            func=func,
            permission_key=permission_key,
            requires_confirmation=requires_confirmation,
            description=description,
        )

    def _register_all(self):
        self._register_web_tools()
        self._register_file_tools()
        self._register_spreadsheet_tools()
        self._register_download_tools()
        self._register_ocr_tools()
        self._register_image_tools()
        self._register_video_tools()

    def _register_web_tools(self):
        try:
            from tools.web_tools import web_search, scrape_page, summarize_webpage
            self.register_tool("web_search", web_search, "browser", description="Search the web using DuckDuckGo")
            self.register_tool("scrape_page", scrape_page, "browser", description="Scrape text from a webpage")
            self.register_tool("summarize_webpage", summarize_webpage, "browser", description="Summarize a webpage")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load web_tools: {e}")

    def _register_file_tools(self):
        try:
            from tools.file_tools import create_file, read_file, write_file, delete_file, create_folder, list_directory
            self.register_tool("create_file", create_file, "files", description="Create a new file")
            self.register_tool("read_file", read_file, "files", description="Read a file")
            self.register_tool("write_file", write_file, "files", description="Write content to a file")
            self.register_tool("delete_file", delete_file, "files", requires_confirmation=True, description="Delete a file (sensitive)")
            self.register_tool("create_folder", create_folder, "files", description="Create a folder")
            self.register_tool("list_directory", list_directory, "files", description="List directory contents")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load file_tools: {e}")

    def _register_spreadsheet_tools(self):
        try:
            from tools.spreadsheet_tools import generate_xlsx, generate_csv
            self.register_tool("generate_xlsx", generate_xlsx, "spreadsheets", description="Generate an Excel spreadsheet")
            self.register_tool("generate_csv", generate_csv, "spreadsheets", description="Generate a CSV file")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load spreadsheet_tools: {e}")

    def _register_download_tools(self):
        try:
            from tools.download_tools import download_file, batch_download
            self.register_tool("download_file", download_file, "downloads", description="Download a file from URL")
            self.register_tool("batch_download", batch_download, "downloads", requires_confirmation=True, description="Download multiple files (sensitive)")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load download_tools: {e}")

    def _register_ocr_tools(self):
        try:
            from tools.ocr_tools import extract_text_from_image, extract_text_from_pdf
            self.register_tool("extract_text_from_image", extract_text_from_image, "ocr", description="Extract text from an image (OCR)")
            self.register_tool("extract_text_from_pdf", extract_text_from_pdf, "ocr", description="Extract text from a PDF")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load ocr_tools: {e}")

    def _register_image_tools(self):
        try:
            from tools.image_tools import image_search, image_download
            self.register_tool("image_search", image_search, "images", description="Search for images")
            self.register_tool("image_download", image_download, "images", description="Download an image")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load image_tools: {e}")

    def _register_video_tools(self):
        try:
            from tools.video_tools import video_search
            self.register_tool("video_search", video_search, "video", description="Search for videos")
        except ImportError as e:
            print(f"[ToolRouter] Warning: could not load video_tools: {e}")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        request_confirmation_callback: Callable[[str, dict, str], Awaitable[bool]],
    ) -> dict:
        """Execute a tool and return a result dict."""
        if tool_name not in self._tools:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

        tool = self._tools[tool_name]

        # Permission check
        if not self.permissions.check_by_key(tool.permission_key):
            self.logger.log(tool_name, args, "blocked", 0, "Permission denied")
            return {"status": "blocked", "error": f"Permission denied for {tool.permission_key}"}

        # Confirmation check
        if tool.requires_confirmation:
            description = f"The AI wants to run '{tool_name}' with args: {args}"
            allowed = await request_confirmation_callback(tool_name, args, description)
            if not allowed:
                self.logger.log(tool_name, args, "blocked", 0, "User denied confirmation")
                return {"status": "blocked", "error": "User denied confirmation"}

        start_time = time.time()
        try:
            if inspect.iscoroutinefunction(tool.func):
                result = await tool.func(**args)
            else:
                result = await asyncio.to_thread(functools.partial(tool.func, **args))

            duration_ms = int((time.time() - start_time) * 1000)
            result_summary = str(result)[:300] if result is not None else ""
            self.logger.log(tool_name, args, "success", duration_ms, result_summary)
            return {"status": "success", "result": result}

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.log(tool_name, args, "error", duration_ms, str(e))
            return {"status": "error", "error": str(e)}

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "permission_key": t.permission_key,
                "requires_confirmation": t.requires_confirmation,
                "description": t.description,
            }
            for t in self._tools.values()
        ]

import json
import os
from pathlib import Path

# Maps permission key -> tool name prefixes / categories
PERMISSION_MAP = {
    "files": ["file_tools"],
    "downloads": ["download_tools"],
    "browser": ["web_tools"],
    "email": ["email_tools"],
    "ocr": ["ocr_tools"],
    "images": ["image_tools"],
    "video": ["video_tools"],
    "spreadsheets": ["spreadsheet_tools"],
}

# Which tool names require a runtime confirmation dialog
SENSITIVE_TOOLS = {"delete_file", "batch_download", "access_email"}


class PermissionManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._permissions: dict[str, bool] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        try:
            with open(self.config_path) as f:
                self._permissions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._permissions = {k: True for k in PERMISSION_MAP}
            self._permissions["email"] = False
            self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._permissions, f, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all(self) -> dict[str, bool]:
        return dict(self._permissions)

    def check(self, tool_name: str) -> bool:
        """Return True if the tool is permitted to run."""
        for perm_key, categories in PERMISSION_MAP.items():
            for category in categories:
                if tool_name.startswith(category.replace("_tools", "")):
                    return self._permissions.get(perm_key, False)
        # Unknown tool: check by tool name's implied category
        for perm_key in PERMISSION_MAP:
            if perm_key in tool_name:
                return self._permissions.get(perm_key, False)
        return False  # Tools not mapped to a permission are denied by default

    def check_by_key(self, permission_key: str) -> bool:
        return self._permissions.get(permission_key, False)

    def grant(self, permission_key: str):
        self._permissions[permission_key] = True
        self._save()

    def revoke(self, permission_key: str):
        self._permissions[permission_key] = False
        self._save()

    def requires_confirmation(self, tool_name: str) -> bool:
        return tool_name in SENSITIVE_TOOLS

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ActionLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "actions.jsonl")

    def log(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        status: str,
        execution_time_ms: int,
        result_summary: str = "",
    ):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "parameters": parameters,
            "status": status,
            "execution_time_ms": execution_time_ms,
            "result_summary": result_summary,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_logs(self, limit: int = 100) -> list[dict]:
        if not os.path.exists(self.log_file):
            return []
        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        # Return the most recent `limit` entries
        return entries[-limit:]

    def clear_logs(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

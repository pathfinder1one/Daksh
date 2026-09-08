"""
Daksh Tools Hub
Integrates and exposes MuktiVerse's Universal 10-Tool Registry:
  1. python_executor - Sandboxed Python execution
  2. file_processor  - Workspace reading & writing
  3. web_search      - Live web search query
  4. web_scraper     - Web page content scraping
  5. sql_query       - Database execution
  6. sql_schema      - Database schema inspection
  7. github_search   - GitHub repository & code search
  8. document_parser - Document parsing
  9. email_sender    - Notification & email delivery
  10. api_caller     - Universal HTTP API dispatcher
"""
import sys
from typing import Any, Dict, List, Optional

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import muktiverse.tools as mt
from muktiverse.logging import get_logger

logger = get_logger("daksh.tools")


class ToolsHub:
    """Central registry and dispatcher for all Daksh & MuktiVerse tools."""

    def __init__(self):
        # Initialize full MuktiVerse tool registry
        mt.initialize_tools()
        self.registry = mt.get_all_tools()
        self.tool_map = {t.name: t for t in self.registry}
        logger.info("daksh.tools_hub.ready", tool_count=len(self.tool_map))

    def list_tools(self) -> List[Dict[str, str]]:
        """Returns metadata for all available tools."""
        return [
            {
                "name": t.name,
                "description": getattr(t, "description", "Specialist Tool"),
            }
            for t in self.registry
        ]

    async def execute_tool(self, tool_name: str, **arguments: Any) -> Any:
        """Executes any registered tool by name with kwargs."""
        if tool_name not in self.tool_map:
            raise ValueError(f"Tool '{tool_name}' not found. Available: {list(self.tool_map.keys())}")
        
        tool = self.tool_map[tool_name]
        logger.info("daksh.tool.executing", tool=tool_name)
        result = await tool.execute(**arguments)
        return result

    async def execute_python(self, code: str) -> str:
        """Convenience method for Python execution."""
        res = await self.execute_tool("python_executor", code=code)
        if hasattr(res, "result"):
            return str(res.result)
        return str(res)


if __name__ == "__main__":
    import asyncio
    
    async def demo():
        hub = ToolsHub()
        print("=" * 60)
        print("Daksh Tools Hub Initialized!")
        print("=" * 60)
        for i, t in enumerate(hub.list_tools(), 1):
            print(f"[{i:2d}] {t['name']:<18} : {t['description'][:50]}...")
            
        print("\nTesting Python Sandbox Execution:")
        code = "import math\nvals = [math.sqrt(x) for x in [4, 9, 16, 25]]\nprint('Computed roots:', vals)"
        output = await hub.execute_python(code)
        print(f"Sandbox Output: {output}")

    asyncio.run(demo())

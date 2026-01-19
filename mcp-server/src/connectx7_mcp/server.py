"""
ConnectX-7 MCP Server
Fetches and searches NVIDIA ConnectX-7, DOCA, VMA, and RDMA documentation.
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from fastmcp import FastMCP

mcp = FastMCP(
    "connectx7-docs",
    instructions="NVIDIA ConnectX-7, DOCA, VMA, RDMA documentation and reference tools"
)

CACHE_DIR = Path.home() / ".cache" / "connectx7-mcp"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_HOURS = 24

# Comprehensive documentation sources
DOC_SOURCES = {
    "connectx7": {
        "base": "https://docs.nvidia.com/networking/display/ConnectX7VPI",
        "name": "ConnectX-7 User Manual",
        "pages": [
            "", "/Introduction", "/Hardware+Installation", "/Driver+Installation",
            "/Firmware+Update", "/Port+Configuration", "/Troubleshooting",
            "/Specifications", "/Performance+Tuning"
        ]
    },
    "doca": {
        "base": "https://docs.nvidia.com/doca/sdk",
        "name": "DOCA SDK",
        "pages": [
            "", "/doca-overview/index.html",
            "/doca-installation-guide-for-linux/index.html",
            "/rdma-over-converged-ethernet/index.html"
        ]
    },
    "vma": {
        "base": "https://docs.nvidia.com/networking/display/VMAv98",
        "name": "VMA User Manual",
        "pages": [
            "", "/Introduction", "/Installation", "/Configuration",
            "/API", "/Performance+Tuning", "/Troubleshooting"
        ]
    },
    "rdma": {
        "base": "https://docs.nvidia.com/networking/display/RDMAAwareProgrammingv17",
        "name": "RDMA Programming Guide",
        "pages": [
            "", "/RDMA-Aware+Programming+Overview",
            "/RDMA+Verbs+API", "/Programming+Examples+Using+IBV+Verbs"
        ]
    },
    "mlnx_ofed": {
        "base": "https://docs.nvidia.com/networking/display/MLNXOFEDv24100700",
        "name": "MLNX_OFED Documentation",
        "pages": ["", "/Introduction", "/Installation", "/Performance+Tuning"]
    },
    "mlx5_kernel": {
        "base": "https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5",
        "name": "mlx5 Kernel Driver",
        "pages": ["/index.html", "/kconfig.html", "/tracepoints.html", "/counters.html"]
    },
    "dpdk_mlx5": {
        "base": "https://doc.dpdk.org/guides/platform",
        "name": "DPDK mlx5 Driver",
        "pages": ["/mlx5.html"]
    }
}


def cache_path(url: str) -> Path:
    return CACHE_DIR / f"{hashlib.md5(url.encode()).hexdigest()[:12]}.json"


def cache_valid(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        return datetime.now() - datetime.fromisoformat(data["ts"]) < timedelta(hours=CACHE_HOURS)
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return False


async def fetch(url: str, refresh: bool = False) -> dict:
    cp = cache_path(url)
    if not refresh and cache_valid(cp):
        data = json.loads(cp.read_text())
        data["cached"] = True
        return data

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        try:
            r = await client.get(url, headers={"User-Agent": "ConnectX7-MCP/1.0"})
            r.raise_for_status()
        except Exception as e:
            return {"error": str(e)}

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find(class_="content") or soup.find(id="content") or soup.body
    if not main:
        return {"error": "No content found"}

    title = soup.title.string if soup.title else url.split("/")[-1]
    content = md(str(main), heading_style="ATX")
    content = re.sub(r'\n{3,}', '\n\n', content)

    data = {"url": url, "title": title, "content": content, "ts": datetime.now().isoformat()}
    cp.write_text(json.dumps(data, indent=2))
    data["cached"] = False
    return data


@mcp.tool()
async def fetch_nvidia_docs(topic: str, page: str = "", refresh: bool = False) -> str:
    """
    Fetch NVIDIA/Mellanox documentation.

    Args:
        topic: One of: connectx7, doca, vma, rdma, mlnx_ofed, mlx5_kernel, dpdk_mlx5
        page: Specific page path (optional, defaults to main page)
        refresh: Force refresh ignoring cache

    Returns:
        Documentation content in markdown format
    """
    topic = topic.lower().replace("-", "_").replace(" ", "_")
    if topic not in DOC_SOURCES:
        available = ", ".join(DOC_SOURCES.keys())
        return f"Unknown topic '{topic}'. Available: {available}"

    src = DOC_SOURCES[topic]
    url = f"{src['base']}{page}"
    result = await fetch(url, refresh)

    if "error" in result:
        return f"Error fetching {url}: {result['error']}"

    status = "cached" if result.get("cached") else "fresh"
    return f"# {result['title']}\n\nSource: {url} ({status})\n\n{result['content']}"


@mcp.tool()
async def search_nvidia_docs(query: str, topics: Optional[list[str]] = None) -> str:
    """
    Search across NVIDIA/Mellanox documentation.

    Args:
        query: Search text (case-insensitive)
        topics: List of topics to search (default: all)
                Options: connectx7, doca, vma, rdma, mlnx_ofed, mlx5_kernel, dpdk_mlx5

    Returns:
        Matching documentation sections with source links
    """
    if topics is None:
        topics = list(DOC_SOURCES.keys())

    query_lower = query.lower()
    results = []

    for topic in topics:
        if topic not in DOC_SOURCES:
            continue
        src = DOC_SOURCES[topic]
        for page_path in src["pages"]:
            url = f"{src['base']}{page_path}"
            data = await fetch(url)
            if "error" in data:
                continue
            content = data.get("content", "")
            if query_lower in content.lower():
                paras = [p for p in content.split("\n\n") if query_lower in p.lower()]
                if paras:
                    results.append({
                        "src": src["name"],
                        "title": data.get("title", page_path),
                        "url": url,
                        "matches": paras[:2]
                    })

    if not results:
        return f"No results found for '{query}'"

    out = [f"# Search Results: '{query}'\n"]
    for r in results[:10]:
        out.append(f"## {r['src']} - {r['title']}")
        out.append(f"URL: {r['url']}\n")
        for m in r["matches"]:
            truncated = m[:500] + "..." if len(m) > 500 else m
            out.append(f"> {truncated}\n")

    return "\n".join(out)


@mcp.tool()
async def list_nvidia_docs() -> str:
    """
    List all available documentation sources and their pages.

    Returns:
        Formatted list of documentation sources
    """
    out = ["# Available Documentation Sources\n"]

    for topic, src in DOC_SOURCES.items():
        out.append(f"## {src['name']} (`{topic}`)")
        out.append(f"Base URL: {src['base']}")
        out.append(f"Pages: {len(src['pages'])}")
        out.append("")

    out.append("## Usage Examples")
    out.append("```")
    out.append('fetch_nvidia_docs("connectx7")                    # Main page')
    out.append('fetch_nvidia_docs("connectx7", "/Troubleshooting") # Specific page')
    out.append('fetch_nvidia_docs("rdma", "/RDMA+Verbs+API")       # RDMA API')
    out.append('search_nvidia_docs("kernel bypass")               # Search all')
    out.append('search_nvidia_docs("QP state", ["rdma", "vma"])   # Search specific topics')
    out.append("```")

    return "\n".join(out)


@mcp.tool()
def clear_doc_cache() -> str:
    """
    Clear the documentation cache to force fresh fetches.

    Returns:
        Confirmation with count of cleared files
    """
    count = sum(1 for f in CACHE_DIR.glob("*.json") if f.unlink() or True)
    return f"Cleared {count} cached documentation files from {CACHE_DIR}"


@mcp.tool()
def get_official_links() -> str:
    """
    Get list of official NVIDIA/Mellanox documentation links.

    Returns:
        Formatted list of official documentation URLs
    """
    links = """# Official NVIDIA/Mellanox Documentation Links

## Primary Documentation
- **ConnectX-7 User Manual**: https://docs.nvidia.com/networking/display/connectx7vpi
- **DOCA SDK**: https://docs.nvidia.com/doca/sdk/
- **VMA User Manual**: https://docs.nvidia.com/networking/display/VMAv98/
- **RDMA Programming Guide**: https://docs.nvidia.com/networking/display/RDMAAwareProgrammingv17/

## Driver Documentation
- **mlx5 Kernel Driver**: https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/
- **DPDK mlx5 Driver**: https://doc.dpdk.org/guides/platform/mlx5.html
- **MLNX_OFED**: https://docs.nvidia.com/networking/display/MLNXOFEDv24100700/

## Downloads & Tools
- **DOCA Downloads**: https://developer.nvidia.com/networking/doca
- **Firmware Downloads**: https://network.nvidia.com/support/firmware/firmware-downloads/
- **Firmware Compatibility Matrix**: https://network.nvidia.com/support/mlnx-ofed-matrix/

## Community & Support
- **NVIDIA Networking Forums**: https://forums.developer.nvidia.com/c/networking/
- **rdma-core GitHub**: https://github.com/linux-rdma/rdma-core
- **RDMAmojo (tutorials)**: https://www.rdmamojo.com/

## Source Code
- **Linux kernel mlx5**: drivers/net/ethernet/mellanox/mlx5/
- **Linux kernel mlx5_ib**: drivers/infiniband/hw/mlx5/
"""
    return links


def main():
    mcp.run()


if __name__ == "__main__":
    main()

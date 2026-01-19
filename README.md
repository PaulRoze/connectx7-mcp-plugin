# ConnectX-7 Development Plugin

**The source of truth for NVIDIA ConnectX-7 driver development** - so your team doesn't have to reverse engineer the driver.

A comprehensive Claude Code plugin providing skills, documentation tools, and references for ConnectX-7, DOCA, VMA, and RDMA development. Designed for broadcast/media teams working with ST 2110 and high-performance networking.

## What's Included

### 6 Skills (Auto-trigger on keywords)

| Skill | Triggers On | Purpose |
|-------|-------------|---------|
| `connectx7-development` | ConnectX, DOCA, driver | General reference, installation |
| `connectx7-vma` | VMA, libvma, kernel bypass | VMA API, dynamic loading patterns |
| `connectx7-rdma-programming` | RDMA, verbs, ibv_post_send | libibverbs programming guide |
| `connectx7-mlx5-driver` | mlx5, kernel driver, dmesg | Driver internals, debugging, tracepoints |
| `connectx7-performance` | latency, tuning, NUMA | Performance optimization guide |
| `connectx7-troubleshooting` | error, debug, troubleshoot | Error codes, diagnostics, fixes |

### MCP Server (Live Documentation)

| Tool | Description |
|------|-------------|
| `fetch_nvidia_docs` | Fetch docs from NVIDIA/kernel.org |
| `search_nvidia_docs` | Search across all documentation |
| `list_nvidia_docs` | List available doc sources |
| `get_official_links` | Get all official documentation URLs |
| `clear_doc_cache` | Clear cached docs |

**Documentation Sources:**
- ConnectX-7 User Manual
- DOCA SDK
- VMA User Manual
- RDMA Programming Guide
- MLNX_OFED Documentation
- mlx5 Kernel Driver (kernel.org)
- DPDK mlx5 Driver

## Installation

### Your Team (via your marketplace)

```bash
# Add marketplace (one time)
/plugin marketplace add PaulRoze/connectx7-mcp-plugin

# Install plugin
/plugin install connectx7-development@connectx7-mcp-plugin
```

### Local Development

```bash
git clone https://github.com/PaulRoze/connectx7-mcp-plugin.git
cd connectx7-marketplace

# Install MCP server (in virtual environment)
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "connectx7-docs": {
      "command": "/path/to/connectx7-marketplace/mcp-server/.venv/bin/connectx7-mcp"
    }
  }
}
```

### Verify Installation

Check that skills appear:

```bash
/help
```

Should see skills like `connectx7-development`, `connectx7-vma`, etc.

## Usage Examples

### Automatic Triggering

Just mention these in conversation:
- "How do I install DOCA?" → `connectx7-development` skill
- "Show me VMA API" → `connectx7-vma` skill
- "ibv_post_send example" → `connectx7-rdma-programming` skill
- "mlx5 tracepoints" → `connectx7-mlx5-driver` skill
- "ConnectX-7 latency tuning" → `connectx7-performance` skill
- "IBV_WC_REM_ACCESS_ERR" → `connectx7-troubleshooting` skill

### MCP Tools

```
"Fetch the RDMA programming guide"
"Search docs for kernel bypass"
"What are all the official NVIDIA networking links?"
```

## Why This Plugin?

**Problem:** Your teammate needs to work with ConnectX-7 drivers but documentation is scattered across NVIDIA, kernel.org, DPDK, and various PDFs. Without this, they'd spend days reverse engineering the driver.

**Solution:** This plugin provides:
1. **Embedded knowledge** - Works offline with comprehensive reference
2. **Live docs** - Fetches latest from official sources
3. **Error codes** - Complete reference for debugging
4. **Code patterns** - Copy-paste ready VMA/RDMA code
5. **Driver internals** - Kernel source locations, tracepoints, sysfs

## Updating

Push changes to GitLab. Teammates get updates on Claude Code restart.

```bash
git add .
git commit -m "Add new error codes to troubleshooting"
git push
```

## Official Documentation Links

- [ConnectX-7 User Manual](https://docs.nvidia.com/networking/display/connectx7vpi)
- [DOCA SDK](https://docs.nvidia.com/doca/sdk/)
- [VMA Documentation](https://docs.nvidia.com/networking/display/VMAv98/)
- [RDMA Programming Guide](https://docs.nvidia.com/networking/display/RDMAAwareProgrammingv17/)
- [mlx5 Kernel Driver](https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/)
- [NVIDIA Networking Forums](https://forums.developer.nvidia.com/c/networking/)

## License

MIT

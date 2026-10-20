# ConnectX-7 Development Plugin

[![CI](https://github.com/PaulRoze/connectx7-mcp-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/PaulRoze/connectx7-mcp-plugin/actions/workflows/ci.yml)

Claude Code skills for NVIDIA ConnectX-7 work: DOCA-Host setup, RDMA verbs, mlx5 driver internals,
VMA/XLIO, tuning, troubleshooting, and pointers to the ST 2110 stack (Rivermax, PTP).

The skills are a starting point, not a source of truth. Each one opens with the primary docs to
check, and tells Claude to fetch them before answering anything version-specific (env var names,
Kconfig symbols, tracepoints, firmware minimums, package names).

## Skills

| Skill | Use it for |
|-------|-----------|
| `connectx7-development` | DOCA-Host / MLNX_OFED install, firmware, card identification, choosing a stack (Rivermax for ST 2110, XLIO/VMA, PTP) |
| `connectx7-rdma-programming` | libibverbs / rdma-cm code: MRs, QPs, work requests, completions, RoCE addressing |
| `connectx7-mlx5-driver` | mlx5_core / mlx5_ib source layout, module params, Kconfig, tracepoints, debugfs, devlink |
| `connectx7-troubleshooting` | Something is broken: link down, health errors, work-completion errors, dmesg messages |
| `connectx7-performance` | It works but is slow: NUMA, IRQ affinity, coalescing, rings, PCIe, perftest |
| `connectx7-vma` | libvma: LD_PRELOAD, VMA_* variables, the vma_extra.h API |

The full list of primary sources is in
[`skills/connectx7-development/references/sources.md`](skills/connectx7-development/references/sources.md).

## Install

```bash
/plugin marketplace add PaulRoze/connectx7-mcp-plugin
/plugin install connectx7-development@connectx7-mcp-plugin
```

## Updates

Third-party marketplaces don't auto-update by default. To pick up a new release:

```bash
/plugin marketplace update connectx7-mcp-plugin
```

Maintainers: bump `version` in `.claude-plugin/plugin.json` on every release. Installed copies are
pinned to that string and won't change until it does.

## Upgrading from 1.x

2.0.0 removes the `connectx7-docs` MCP server. It never started for marketplace installs (nothing
put `connectx7-mcp` on PATH), and most of its doc URLs had moved. Claude's built-in WebFetch and
WebSearch cover the same docs; the skills list the current URLs.

## License

MIT

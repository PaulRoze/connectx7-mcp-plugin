---
name: connectx7-development
description: "ConnectX-7, DOCA, VMA kernel bypass development reference. Use when working with Mellanox/NVIDIA networking, RDMA, kernel bypass, ST 2110, or high-performance UDP/multicast. Triggers on: ConnectX, DOCA, VMA, libvma, MLNX_OFED, mlx5, RoCE, InfiniBand, SMPTE ST 2110."
---

# ConnectX-7 & DOCA Development Reference

## Driver Stack (2025+)

| Package | Status | Use Case |
|---------|--------|----------|
| **DOCA-OFED** | Current | Production - replaces MLNX_OFED |
| **MLNX_OFED** | LTS until Oct 2027 | Legacy systems only |
| **doca-libvma** | Current | Kernel bypass for UDP/TCP |

## Quick Install (Rocky/RHEL 8+)

```bash
cat > /etc/yum.repos.d/doca.repo << 'EOF'
[doca]
name=DOCA Online Repo
baseurl=https://linux.mellanox.com/public/repo/doca/2.9.1/rhel8.9/x86_64/
enabled=1
gpgcheck=0
EOF

dnf -y install doca-ofed doca-libvma
reboot
```

## Card Models

| Model | Ports | Speed | Use Case |
|-------|-------|-------|----------|
| MCX713106AS-VEA | 2 | 100G | 4K60 ST 2110 |
| MCX753106AS-HEA | 2 | 200G | 8K / multi-4K |
| MCX75310AAS-NEA | 1 | 200G | NDR100 InfiniBand |

## Firmware

- **Minimum for DOCA 3.x**: 28.43.1000
- **Check**: `mlxfwmanager --query`
- **Update**: `mlxfwmanager --update`

## Related Skills

- **VMA API details** → `connectx7-vma`
- **RDMA programming** → `connectx7-rdma-programming`
- **Performance tuning** → `connectx7-performance`
- **Troubleshooting** → `connectx7-troubleshooting`
- **Kernel driver internals** → `connectx7-mlx5-driver`

## Live Documentation (MCP Tools)

Use `fetch_nvidia_docs` and `search_nvidia_docs` for latest online docs.

## Online Resources

For latest documentation, fetch from:
- [DOCA SDK](https://docs.nvidia.com/doca/sdk/)
- [ConnectX-7 Manual](https://docs.nvidia.com/networking/display/ConnectX7VPI/)
- [VMA Documentation](https://docs.nvidia.com/networking/display/VMAv98/)

---
name: connectx7-mlx5-driver
description: "mlx5 kernel driver internals: source layout, module parameters, Kconfig, tracepoints, debugfs, devlink params, flow steering modes. Use when reading or patching mlx5_core/mlx5_ib source, enabling driver tracepoints or debug output, or explaining how the driver is structured. Not for symptom-driven triage (see connectx7-troubleshooting)."
---

# mlx5 Kernel Driver Reference

> Written against Linux 6.x mlx5 and DOCA 3.x. For anything version-specific (Kconfig symbols, tracepoint names, module parameters, debugfs layout, devlink params), WebFetch the primary source before answering:
> https://github.com/torvalds/linux/tree/master/drivers/net/ethernet/mellanox/mlx5/core and https://www.kernel.org/doc/html/latest/networking/devlink/mlx5.html
> Ask for `uname -r` and `ethtool -i <iface>` first. Full list: ../connectx7-development/references/sources.md

## Driver Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Space                           │
├─────────────────────────────────────────────────────────┤
│  libibverbs    │    libmlx5    │    DPDK mlx5 PMD      │
├─────────────────────────────────────────────────────────┤
│                    Kernel Space                         │
├─────────────────────────────────────────────────────────┤
│  mlx5_ib (RDMA/IB)  │  Ethernet (inside mlx5_core)     │
├─────────────────────────────────────────────────────────┤
│                    mlx5_core                            │
│  (HW abstraction, command interface, resource mgmt,     │
│   Ethernet netdev: CONFIG_MLX5_CORE_EN, not a module)   │
├─────────────────────────────────────────────────────────┤
│                    ConnectX-7 Hardware                  │
└─────────────────────────────────────────────────────────┘
```

## Kernel Source Locations

```
drivers/net/ethernet/mellanox/mlx5/core/   # mlx5_core.ko (includes Ethernet)
├── main.c          # Module init, PCI probe, module params
├── cmd.c           # Firmware command interface
├── eq.c            # Event queues
├── cq.c            # Completion queues
├── mr.c            # Memory regions
├── fw.c            # Firmware handling
├── health.c        # Health monitoring
├── debugfs.c       # /sys/kernel/debug/mlx5/<pci>/
├── devlink.c       # devlink params
├── eswitch.c       # E-Switch
├── fs_core.c       # Flow steering core
├── en_main.c       # Ethernet netdev init
├── en_tx.c         # Transmit path
├── en_rx.c         # Receive path
├── en_ethtool.c
├── en/             # Ethernet helpers (params, tc, xdp, reporters)
├── steering/       # SW (sws) and HW (hws) steering
└── diag/           # Tracepoints, FW tracer

drivers/infiniband/hw/mlx5/
├── main.c          # IB device registration
├── qp.c            # QP operations
├── cq.c            # CQ operations
├── mr.c            # Memory registration
└── cmd.c           # IB commands
```

## Kernel Config Options

```bash
# Core driver (required)
CONFIG_MLX5_CORE=m

# Ethernet support
CONFIG_MLX5_CORE_EN=y

# InfiniBand/RDMA support
CONFIG_MLX5_INFINIBAND=m

# E-Switch (switchdev) support
CONFIG_MLX5_ESWITCH=y

# TLS offload
CONFIG_MLX5_EN_TLS=y

# IPsec offload
CONFIG_MLX5_EN_IPSEC=y

# Check current config
zcat /proc/config.gz | grep MLX5
# Or
grep MLX5 /boot/config-$(uname -r)
```

## Tracepoints for Debugging

```bash
# List available mlx5 tracepoints
ls /sys/kernel/debug/tracing/events/mlx5/

# Enable specific tracepoint
echo 1 > /sys/kernel/debug/tracing/events/mlx5/mlx5_cmd/enable

# Enable all mlx5 tracepoints
echo 1 > /sys/kernel/debug/tracing/events/mlx5/enable

# Tracing is debug-only; echo 0 to disable when done

# View trace output
cat /sys/kernel/debug/tracing/trace_pipe

# Common tracepoints:
# mlx5_cmd         - Firmware commands
# mlx5_fw          - FW tracer messages (needs the FW tracer running)
# mlx5_fs_add_rule, mlx5_fs_del_rule, mlx5_fs_add_ft, ... - Flow steering
```

## Sysfs Interface

```bash
# Device info
/sys/class/infiniband/mlx5_0/

# Port info
/sys/class/infiniband/mlx5_0/ports/1/

# Counters
/sys/class/infiniband/mlx5_0/ports/1/counters/

# Hardware counters
/sys/class/infiniband/mlx5_0/ports/1/hw_counters/

# Network interface
/sys/class/net/eth0/device/
/sys/class/net/eth0/device/infiniband/
/sys/class/net/eth0/device/numa_node

# SR-IOV
/sys/class/net/eth0/device/sriov_numvfs
/sys/class/net/eth0/device/sriov_totalvfs
```

## devlink Interface

```bash
# Show device info
devlink dev show

# Show device params
devlink dev param show pci/0000:08:00.0

# Flow steering mode (dmfs, smfs, hmfs)
devlink dev param set pci/0000:08:00.0 name flow_steering_mode value smfs cmode runtime

# E-Switch mode
devlink dev eswitch show pci/0000:08:00.0
devlink dev eswitch set pci/0000:08:00.0 mode switchdev

# Health reporters
devlink health show pci/0000:08:00.0
devlink health diagnose pci/0000:08:00.0 reporter fw
```

## Flow Steering Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **dmfs** | Device Managed Flow Steering | Default, firmware handles rules |
| **smfs** | Software Managed Flow Steering | Driver manages HW steering entities without firmware |
| **hmfs** | Hardware Managed Flow Steering | Driver writes rules to HW via work queues (needs CONFIG_MLX5_HW_STEERING and device support) |

```bash
# Check current mode
devlink dev param show pci/0000:08:00.0 name flow_steering_mode

# Switch to smfs (runtime; check the current mode first)
devlink dev param set pci/0000:08:00.0 name flow_steering_mode value smfs cmode runtime
```

## Debugging Driver Issues

### Kernel Logs

```bash
# Watch mlx5 messages
dmesg -w | grep -i mlx5

# Recent mlx5 errors
dmesg | grep -i "mlx5.*error\|mlx5.*fail"

# Full mlx5 history
journalctl -k | grep -i mlx5
```

### Common Error Patterns

**See [`connectx7-troubleshooting`] for the complete kernel error code reference table.**

### Health Monitoring

**See [`connectx7-troubleshooting`] for complete health monitoring commands and reporter state reference.**

## Module Parameters

```bash
# View current parameters
systool -vm mlx5_core

# Or
cat /sys/module/mlx5_core/parameters/*

# Load with debug
# debug_mask: 1 = dump cmd data, 2 = dump cmd exec time, 3 = both (default 0)
# Writable at runtime (0644); very verbose, reset to 0 after use
modprobe mlx5_core debug_mask=3

# Other parameter: prof_sel (profile selector, 0-2, read-only)
```

## Useful Debug Commands

```bash
# Full device info dump
mlxconfig -d /dev/mst/mt4129_pciconf0 query

# Register dump (for NVIDIA support)
mstdump /dev/mst/mt4129_pciconf0 > regdump.txt

# Firmware trace (advanced)
mstfwtrace -d /dev/mst/mt4129_pciconf0

# Resource usage
ls /sys/kernel/debug/mlx5/0000:08:00.0/{QPs,EQs,CQs,commands,pages}
```

## Official Documentation

- [Linux Kernel mlx5 Docs](https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/index.html)
- [mlx5 devlink params and health reporters](https://www.kernel.org/doc/html/latest/networking/devlink/mlx5.html)
- [mlx5 kernel source](https://github.com/torvalds/linux/tree/master/drivers/net/ethernet/mellanox/mlx5/core)
- [DPDK mlx5 Driver](https://doc.dpdk.org/guides/nics/mlx5.html)
- [NVIDIA DOCA SDK](https://docs.nvidia.com/doca/sdk/)
- Full list: ../connectx7-development/references/sources.md

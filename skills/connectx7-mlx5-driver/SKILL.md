---
name: connectx7-mlx5-driver
description: "mlx5 kernel driver internals, debugging, and tracepoints. Use when debugging driver issues, understanding mlx5 architecture, reading kernel logs, or when teammate needs to understand driver behavior without reverse engineering."
---

# mlx5 Kernel Driver Reference

## Driver Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Space                           │
├─────────────────────────────────────────────────────────┤
│  libibverbs    │    libmlx5    │    DPDK mlx5 PMD      │
├─────────────────────────────────────────────────────────┤
│                    Kernel Space                         │
├─────────────────────────────────────────────────────────┤
│  mlx5_ib (RDMA/IB)  │  mlx5_en (Ethernet)              │
├─────────────────────────────────────────────────────────┤
│                    mlx5_core                            │
│  (HW abstraction, command interface, resource mgmt)     │
├─────────────────────────────────────────────────────────┤
│                    ConnectX-7 Hardware                  │
└─────────────────────────────────────────────────────────┘
```

## Kernel Source Locations

```
drivers/net/ethernet/mellanox/mlx5/
├── core/           # mlx5_core driver
│   ├── main.c      # Module init, PCI probe
│   ├── cmd.c       # Firmware command interface
│   ├── eq.c        # Event queues
│   ├── cq.c        # Completion queues
│   ├── qp.c        # Queue pairs
│   ├── mr.c        # Memory regions
│   ├── fw.c        # Firmware handling
│   └── health.c    # Health monitoring
└── en/             # Ethernet netdev
    ├── main.c      # Ethernet init
    ├── en_tx.c     # Transmit path
    ├── en_rx.c     # Receive path
    └── en_ethtool.c

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

# FPGA support (if applicable)
CONFIG_MLX5_FPGA=y

# TLS offload
CONFIG_MLX5_TLS=y

# IPsec offload
CONFIG_MLX5_IPSEC=y

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
echo 1 > /sys/kernel/debug/tracing/events/mlx5/mlx5_fw_cmd/enable

# Enable all mlx5 tracepoints
echo 1 > /sys/kernel/debug/tracing/events/mlx5/enable

# View trace output
cat /sys/kernel/debug/tracing/trace_pipe

# Common tracepoints:
# mlx5_fw_cmd      - Firmware commands
# mlx5_eq          - Event queue activity
# mlx5_cq          - Completion queue events
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

# Flow steering mode (dmfs vs smfs)
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
| **smfs** | Software Managed Flow Steering | Faster rule insertion, driver manages HW directly |

```bash
# Check current mode
devlink dev param show pci/0000:08:00.0 name flow_steering_mode

# Switch to smfs (faster)
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

| Log Pattern | Meaning | Fix |
|-------------|---------|-----|
| `mlx5_core: firmware error` | FW crashed | Update firmware, cold reboot |
| `mlx5_core: cmd timeout` | FW not responding | Check PCIe, reboot |
| `mlx5_ib: CQ overrun` | CQ too small | Increase CQ size |
| `mlx5_core: health error` | HW health check failed | Check `devlink health` |
| `mlx5_core: out of resources` | HW resource exhaustion | Reduce QPs/MRs |

### Health Monitoring

```bash
# Check health status
devlink health show pci/0000:08:00.0

# Diagnose specific reporter
devlink health diagnose pci/0000:08:00.0 reporter fw
devlink health diagnose pci/0000:08:00.0 reporter fw_fatal

# Dump health info
devlink health dump show pci/0000:08:00.0 reporter fw
```

## Module Parameters

```bash
# View current parameters
systool -vm mlx5_core

# Or
cat /sys/module/mlx5_core/parameters/*

# Load with debug
modprobe mlx5_core debug_level=1
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
cat /sys/kernel/debug/mlx5/0000:08:00.0/resources
```

## Official Documentation

- [Linux Kernel mlx5 Docs](https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/index.html)
- [DPDK mlx5 Driver](https://doc.dpdk.org/guides/platform/mlx5.html)
- [NVIDIA DOCA SDK](https://docs.nvidia.com/doca/sdk/)

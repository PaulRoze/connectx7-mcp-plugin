---
name: connectx7-troubleshooting
description: "ConnectX-7 symptom triage: link down, firmware or health errors, RDMA work-completion errors, dmesg messages, devlink health reports. Use when something is broken or failing on a ConnectX NIC and you need to find the cause. Not for throughput or latency tuning (see connectx7-performance)."
---

# ConnectX-7 Troubleshooting Guide

> Written against DOCA 3.x / rdma-core 5x / Linux 6.x mlx5. For anything version-specific (dmesg strings, devlink reporters, MFT tool options, firmware versions, VMA env vars), WebFetch the primary source before answering: https://www.kernel.org/doc/html/latest/networking/devlink/mlx5.html and https://networking-docs.nvidia.com/mftswum/4300.
> Ask the user for `ofed_info -s`, `ethtool -i <iface>`, `uname -r` first. Full list: ../connectx7-development/references/sources.md

## Quick Diagnostic Commands

```bash
# System info
ethtool -i eth0                    # Driver/firmware version
lspci | grep -i mellanox           # PCI device
mst start && mst status            # MST devices
mlxfwmanager --query               # Firmware details

# Link status
ibstat                             # IB port status
ethtool eth0                       # Ethernet link
ip link show eth0                  # Interface state

# Health check
devlink health show pci/0000:08:00.0
dmesg | grep -i "mlx5.*error\|mlx5.*fail"
```

## Error Code Reference

### Kernel (dmesg) Messages

Real strings from `drivers/net/ethernet/mellanox/mlx5/core`:

| Pattern | Meaning |
|---------|---------|
| `device's health compromised - reached miss count` | FW stopped answering the health poll; check `devlink health`, PCIe, power |
| `<CMD>(0x..) op_mod(0x..) failed, status ..., syndrome (0x..)` | FW rejected a command; the syndrome identifies the cause |
| `<CMD>(0x..) timeout. Will cause a leak of a command resource` | FW command timed out |
| `Port module event[error]: module N, ...` | Transceiver problem; check cable/module |
| `TX timeout detected` | Netdev TX watchdog fired; see `tx` health reporter |

### RDMA Work Completion Errors

Codes are the `enum ibv_wc_status` values in rdma-core `libibverbs/verbs.h`.

| Status | Code | Meaning | Common Cause |
|--------|------|---------|--------------|
| `IBV_WC_LOC_LEN_ERR` | 1 | Local length error | SGE length mismatch |
| `IBV_WC_LOC_QP_OP_ERR` | 2 | Local QP operation error | Invalid opcode for QP type |
| `IBV_WC_LOC_PROT_ERR` | 4 | Local protection error | Wrong MR permissions/lkey |
| `IBV_WC_WR_FLUSH_ERR` | 5 | WR flushed | QP moved to error state |
| `IBV_WC_MW_BIND_ERR` | 6 | Memory window bind error | MW configuration issue |
| `IBV_WC_REM_INV_REQ_ERR` | 9 | Remote invalid request | Unsupported operation |
| `IBV_WC_REM_ACCESS_ERR` | 10 | Remote access error | Wrong rkey or remote MR permissions |
| `IBV_WC_REM_OP_ERR` | 11 | Remote operation error | Remote QP issue |
| `IBV_WC_RETRY_EXC_ERR` | 12 | Retry exceeded | Network timeout, path MTU |
| `IBV_WC_RNR_RETRY_EXC_ERR` | 13 | RNR retry exceeded | Receiver not ready (no recv posted) |
| `IBV_WC_RESP_TIMEOUT_ERR` | 20 | Response timeout | Remote not responding |

### Link diagnosis basics

```bash
mlxlink -d /dev/mst/mt4129_pciconf0   # port state, speed, FEC, cable (needs mst start)
ethtool -m eth0                       # transceiver EEPROM / DOM
ethtool --show-fec eth0               # FEC mode
ethtool -S eth0 | grep _phy           # PHY error counters
```

## Link Troubleshooting

### Physical State (ibstat)

```bash
ibstat
# Look for "Physical state" field
```

| State | Meaning | Action |
|-------|---------|--------|
| `LinkUp` | Good | - |
| `Polling` | Waiting for link partner | Check cable, switch port |
| `PortConfigurationTraining` | Speed negotiation | Check adapter/switch compatibility |
| `LinkErrorRecovery` | Link errors | Replace cable |
| `Disabled` | Port disabled | Enable port, check config |

### Ethernet Link (ethtool)

```bash
ethtool eth0
# Check "Link detected", "Speed", "Duplex"
```

| Issue | Check |
|-------|-------|
| No link | Cable, switch port, SFP |
| Wrong speed | Auto-negotiation, force speed settings |
| Link flapping | Cable quality, switch logs |

## Health Monitoring

```bash
# Check all health reporters
devlink health show pci/0000:08:00.0

# Diagnose specific reporter
devlink health diagnose pci/0000:08:00.0 reporter fw
devlink health dump show pci/0000:08:00.0 reporter fw_fatal   # CR-space dump, PF only
devlink health recover pci/0000:08:00.0 reporter fw_fatal

# Dump FW core dump (for NVIDIA support; PF with fw tracer ownership)
devlink health dump show pci/0000:08:00.0 reporter fw > health_dump.txt
```

### Health Reporter States

| Reporter | State | Action |
|----------|-------|--------|
| `fw` healthy | Good | - |
| `fw` error | FW issue | Check dmesg, update FW |
| `fw_fatal` error | Critical | Cold reboot, contact support |
| `tx` error | TX timeout / SQ error | `devlink health diagnose ... reporter tx` (interface must be up) |
| `rx` error | RQ population timeout / CQ error | `devlink health diagnose ... reporter rx` (interface must be up) |

## Firmware Troubleshooting

```bash
# Check version
mlxfwmanager --query

# Manual update (PSID of the card must match the image PSID; never lose power during a burn)
mst start
flint -d /dev/mst/mt4129_pciconf0 q                       # note PSID
flint -i firmware.bin verify                              # image integrity + its PSID
flint -d /dev/mst/mt4129_pciconf0 -i firmware.bin burn

# Activate new FW without reboot (or reboot / power cycle if it refuses)
mlxfwreset -d /dev/mst/mt4129_pciconf0 reset
```

### Firmware Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Card not detected after update | Bad FW flash | Cold reboot (power off) |
| FW version mismatch | Partial update | Re-burn firmware |
| "PSID mismatch" error | Wrong FW image | Get correct image for your card |

## Performance Issues

**See [`connectx7-performance`] for complete NUMA configuration, PCIe link diagnostics, and drop/error counter checks.**

## VMA Troubleshooting

### Verify VMA is Loaded

```bash
# Check if VMA is intercepting
lsof -p $(pgrep your_app) | grep libvma

# Enable VMA debug
export VMA_TRACELEVEL=debug
export VMA_LOG_FILE=/tmp/vma.log
LD_PRELOAD=/usr/lib64/libvma.so ./your_app

# Check log
cat /tmp/vma.log
```

### VMA Statistics

```bash
export VMA_STATS_FILE=/tmp/vma_stats
export VMA_STATS_SHMEM_DIR=/tmp
./your_app &

# View stats
vma_stats -p $(pgrep your_app)
```

## Collecting Debug Info for Support

```bash
#!/bin/bash
# collect_debug.sh

OUTPUT_DIR=/tmp/mlx5_debug_$(date +%Y%m%d_%H%M%S)
mkdir -p $OUTPUT_DIR

echo "Collecting debug info to $OUTPUT_DIR"

# System info
uname -a > $OUTPUT_DIR/uname.txt
cat /etc/os-release > $OUTPUT_DIR/os-release.txt

# Driver info
lspci -vvv | grep -A50 Mellanox > $OUTPUT_DIR/lspci.txt
ethtool -i eth0 > $OUTPUT_DIR/ethtool_i.txt
mlxfwmanager --query > $OUTPUT_DIR/firmware.txt 2>&1

# Status
ibstat > $OUTPUT_DIR/ibstat.txt 2>&1
ethtool eth0 > $OUTPUT_DIR/ethtool.txt
devlink health show > $OUTPUT_DIR/devlink_health.txt 2>&1

# Logs
dmesg | grep -i mlx5 > $OUTPUT_DIR/dmesg_mlx5.txt
journalctl -k | grep -i mlx5 > $OUTPUT_DIR/journal_mlx5.txt 2>&1

# Counters
ethtool -S eth0 > $OUTPUT_DIR/ethtool_stats.txt
cat /sys/class/infiniband/mlx5_0/ports/1/counters/* > $OUTPUT_DIR/ib_counters.txt 2>&1

# Config
mst start
mlxconfig -d /dev/mst/mt4129_pciconf0 query > $OUTPUT_DIR/mlxconfig.txt 2>&1
mstdump /dev/mst/mt4129_pciconf0 > $OUTPUT_DIR/mstdump.txt 2>&1

echo "Debug info collected in $OUTPUT_DIR"
tar -czvf ${OUTPUT_DIR}.tar.gz -C /tmp $(basename $OUTPUT_DIR)
echo "Archive: ${OUTPUT_DIR}.tar.gz"
```

## Official Resources

- [mlx5 devlink and health reporters](https://www.kernel.org/doc/html/latest/networking/devlink/mlx5.html)
- [mlx5 Kernel Docs](https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/index.html)
- [MFT / mstflint](https://networking-docs.nvidia.com/mftswum/4300)
- [ConnectX-7 hardware](https://networking-docs.nvidia.com/connectx7hw)
- [VMA 9.8.84](https://networking-docs.nvidia.com/vmaswum/9884)

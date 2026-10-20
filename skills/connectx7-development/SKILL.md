---
name: connectx7-development
description: "ConnectX-7 setup and stack choice: DOCA-Host / MLNX_OFED install and upgrade, firmware, card identification, and which stack to use for broadcast (Rivermax for SMPTE ST 2110, XLIO or VMA for socket acceleration, PTP/ST 2059 timing). Use when installing or upgrading NVIDIA networking software, choosing a kernel-bypass stack, or starting ST 2110 work on ConnectX. Triggers: DOCA, MLNX_OFED, Rivermax, XLIO, ST 2110, ST 2059, PTP."
---

# ConnectX-7 & DOCA Development Reference

> Written against DOCA 3.x. For anything version-specific (package and profile names, firmware minimums, mlxconfig parameters, library versions), WebFetch the primary source before answering.
> Start with the [DOCA-Host install page](https://networking-docs.nvidia.com/doca/archive/3-5-0/doca-host-installation-and-upgrade) and [references/sources.md](references/sources.md). Ask the user for `ofed_info -s`, `ethtool -i <iface>`, `uname -r`.

## Driver Stack

- **DOCA-Host** is the current driver and software package. MLNX_OFED transitioned into DOCA-Host; 24.10 is the last MLNX_OFED release (legacy systems only).
- VMA and XLIO ship as DOCA-Host profiles (`doca-libvma`, `doca-libxlio`).

## Install

Follow the [DOCA-Host install page](https://networking-docs.nvidia.com/doca/archive/3-5-0/doca-host-installation-and-upgrade) for your OS: add the DOCA repo it gives you (keep GPG checking on), then install a profile. Profiles named on that page: `doca-all`, `doca-ofed`, `doca-ofed-userspace`, `doca-libvma`, `doca-libxlio`. Supported profiles differ per OS, so check its supported-OS table.

## Card Models

See the [ConnectX-7 hardware manual](https://networking-docs.nvidia.com/connectx7hw) for ordering part numbers, ports and speeds.

## Firmware

- **Minimum for your DOCA version**: check the firmware release notes
- **Check**: `mlxfwmanager --query`
- **Update**: `mlxfwmanager --update` (check the PSID matches the card first; do not interrupt; some changes need `mlxfwreset` or a reboot)

## ST 2110 stack

- ST 2110 on ConnectX-7 = [NVIDIA Rivermax](https://developer.nvidia.com/networking/rivermax). It uses the NIC's hardware packet pacing, which ST 2110-21 needs.
- VMA (libvma, latest 9.8.84, 2026-01) and XLIO ([libxlio](https://github.com/Mellanox/libxlio), latest stable 3.71.2, 2026-08-21; `gh api repos/Mellanox/libxlio/releases`, excluding prereleases) are generic socket accelerators, not ST 2110 stacks. XLIO is the newer of the two.
- PTP / ST 2059: run `ptp4l` + `phc2sys` against the NIC's PHC. `ethtool -T <if>` shows the PHC index and timestamping capabilities.
- ConnectX-7 real-time clock: `mlxconfig -d <dev> set REAL_TIME_CLOCK_ENABLE=1` (name taken from the [DPDK mlx5 guide](https://doc.dpdk.org/guides/nics/mlx5.html); persistent, query first with `mlxconfig -d <dev> q`, takes effect after `mlxfwreset` or reboot). See Rivermax docs for any other required firmware clock settings.

## Related Skills

- **libvma** → `connectx7-vma`
- **Verbs code** → `connectx7-rdma-programming`
- **Tuning** → `connectx7-performance`
- **Symptom triage** → `connectx7-troubleshooting`
- **Internals, source, tracepoints** → `connectx7-mlx5-driver`

## Online Resources

- [DOCA-Host install](https://networking-docs.nvidia.com/doca/archive/3-5-0/doca-host-installation-and-upgrade)
- [DOCA SDK](https://docs.nvidia.com/doca/sdk/)
- [ConnectX-7 hardware manual](https://networking-docs.nvidia.com/connectx7hw)
- [MLNX_OFED 24.10](https://networking-docs.nvidia.com/mlnxofedswum/24100700)
- [VMA 9.8.84](https://networking-docs.nvidia.com/vmaswum/9884)
- [Rivermax](https://developer.nvidia.com/networking/rivermax)

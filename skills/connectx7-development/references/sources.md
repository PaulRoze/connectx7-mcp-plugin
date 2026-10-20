# Primary sources

Fetch these instead of answering from memory when the question depends on a version:
env var names and defaults, Kconfig symbols, tracepoints, module params, firmware minimums,
package names, mlxconfig parameters.

| Topic | Source |
|-------|--------|
| ConnectX-7 hardware, cards, specs | https://networking-docs.nvidia.com/connectx7hw |
| DOCA-Host install (replaces MLNX_OFED) | https://networking-docs.nvidia.com/doca/archive/3-5-0/doca-host-installation-and-upgrade |
| DOCA SDK, latest | https://docs.nvidia.com/doca/sdk/ |
| MLNX_OFED 24.10 (last release, legacy) | https://networking-docs.nvidia.com/mlnxofedswum/24100700 |
| RDMA verbs programming | https://networking-docs.nvidia.com/rdmaawareprogramming |
| rdma-core headers and examples | https://github.com/linux-rdma/rdma-core (`libibverbs/verbs.h`, `libibverbs/examples/rc_pingpong.c`, `providers/mlx5/mlx5dv.h`) |
| mlx5 kernel driver docs | https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/index.html |
| mlx5 devlink params and health reporters | https://www.kernel.org/doc/html/latest/networking/devlink/mlx5.html |
| mlx5 kernel source | https://github.com/torvalds/linux/tree/master/drivers/net/ethernet/mellanox/mlx5/core |
| DPDK mlx5 PMD | https://doc.dpdk.org/guides/nics/mlx5.html |
| DPDK mlx5 platform guide | https://doc.dpdk.org/guides/platform/mlx5.html |
| VMA 9.8.84 (maintenance mode) | https://networking-docs.nvidia.com/vmaswum/9884 and https://github.com/Mellanox/libvma |
| XLIO (VMA successor) | https://github.com/Mellanox/libxlio |
| Rivermax (ST 2110) | https://developer.nvidia.com/networking/rivermax |
| MFT / mstflint (flint, mlxconfig, mlxlink) | https://networking-docs.nvidia.com/mftswum/4300 |
| Firmware downloads | https://network.nvidia.com/support/firmware/firmware-downloads/ |

Ask the user for `ofed_info -s`, `ethtool -i <iface>`, `uname -r` and `flint -d <dev> q` before
giving version-specific advice.

---
layout: post
title: '在 Kubenretes 中部署 GlusterFS'
date: 2019-04-10 08:54:46 +0800
categories: kubernetes glusterfs
---

由于项目要求自建 Kubernetes 集群，所以之前需要用到 PersistentVolume 的地方都是使用的 Local 或者直接使用 HostPath。搜索了一下发现 GlusterFS 可以部署在 Kubernetes 中，并作为 StorageProvisioner，自动管理 PersistentVolume 的创建和销毁，作为使用者只需要创建、删除需要的 PersistentVolumeClaim 即可。

参考项目 [gluster-kubernetes](https://github.com/gluster/gluster-kubernetes)

主要由三部分组成

- [Kubernetes](https://kubernetes.io) 容器管理平台
- [GlusterFS](https://www.gluster.org) 可拓展的存储系统
- [heketi](https://github.com/heketi/heketi) 为 GlusterFS 提供卷管理 RESTful 接口

# 基础环境

按照 [setup guide](https://github.com/gluster/gluster-kubernetes/blob/master/docs/setup-guide.md) 检查环境

至少三个节点：

- node-181: 192.168.136.181/24
- node-182: 192.168.136.182/24
- node-183: 192.168.136.183/24

每个节点至少有一个裸块设备（raw block device）

```console
$ for HOST in node-{1..3}; do ssh root@$HOST lsblk /dev/sdb; done
NAME MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
sdb    8:16   0  16G  0 disk
NAME MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
sdb    8:16   0  16G  0 disk
NAME MAJ:MIN RM SIZE RO TYPE MOUNTPOINT
sdb    8:16   0  16G  0 disk
```

每个节点开放防火墙端口

```console
$ firewall-cmd --list-all
public (active)
  target: default
  icmp-block-inversion: no
  interfaces: ens160
  sources:
  services: ssh dhcpv6-client
  ports: 179/tcp 6443/tcp 2379-2380/tcp 10242-10250/tcp 30000-32767/tcp
  protocols:
  masquerade: no
  forward-ports:
  source-ports:
  icmp-blocks:
  rich rules:
```

未开放则开放对应端口

```console
$ sudo firewall-cmd --add-port=2222/tcp --add-port=24007/tcp --add-port=24008/tcp --add-port=49152-49251/tcp --permanent
success
$ sudo firewall-cmd --reload
success
```

内核加载下列模块

- dm_snapshot
- dm_mirror
- dm_thin_pool

查看模块是否被加载

```console
$ lsmod | cut -d ' ' -f 1 | grep dm_snapshot
dm_snapshot
```

未加载则通过下面命令加载

```console
sudo modprobe dm_mirror
sudo cat <<EOf > /etc/modules-load.d/dm_mirror.conf
dm_mirror
EOF
```

每个节点需要有 `mount.glusterfs` 这个命令，如果没有则需要安装

RHEL:

```console
sudo yum -y install glusterfs-fuse
```

安装之后确认版本

```console
$ glusterfs --version
glusterfs 3.12.2
```

# 部署概述

管理员需要向 heketi 提供 GlusterFS 集群的拓扑。大多数部署任务都由脚本 `gk-deploy` 处理。以下是脚本执行步骤的概述：

1. 为 heketi 创建 `ServiceAccount` 使之能与 GlusterFS 节点安全地通信
2. 以 `DaemonSet` 的形式将 GlusterFS 部署至 Kubneretes 中的指定节点
3. 部署一个 heketi 实例 `deploy-heketi`，用于初始化 heketi 的数据库
4. 创建 GlusterFS 的 Service 和 Endpoint，并通过通过创建 GlusterFS 卷来初始化 heketi 数据库，随后将数据库复制到同一个卷上供最终的 heketi 实例使用
5. 删除所有 `deploy-heketi` 相关的资源
6. 部署最终的 heketi 实例

# 部署流程

## 1. 创建拓扑文件

如上文所述，管理员必须提供 GlusterFS 集群的拓扑信息。采用拓扑文件的形式定义，该文件描述 GlusterFS 集群中存在的节点以及附加到它们的块设备以供 heketi 使用。项目提供了 [示例拓扑文件](https://github.com/gluster/gluster-kubernetes/blob/master/deploy/topology.json.sample)，创建自定义拓扑文件时需要注意两点：

- 确保拓扑文件仅列出了用于 heketi 的块设备，heketi 需要利用整个块设备，它将被分区并格式化。
- `hostname` 有一些误导，`manage` 是节点的 hostname，而 `storage` 是节点用于后端存储通信的 IP。

我的拓扑文件

```json
{
  "clusters": [
    {
      "nodes": [
        {
          "node": {
            "hostnames": {
              "manage": [
                "node-181"
              ],
              "storage": [
                "192.168.136.181"
              ]
            },
            "zone": 1
          },
          "devices": [
            "/dev/sdb"
          ]
        },
        {
          "node": {
            "hostnames": {
              "manage": [
                "node-182"
              ],
              "storage": [
                "192.168.136.182"
              ]
            },
            "zone": 1
          },
          "devices": [
            "/dev/sdb"
          ]
        },
        {
          "node": {
            "hostnames": {
              "manage": [
                "node-183"
              ],
              "storage": [
                "192.168.136.183"
              ]
            },
            "zone": 1
          },
          "devices": [
            "/dev/sdb"
          ]
        }
      ]
    }
  ]
}
```

## 2. 执行部署脚本

- 默认情况下拓扑文件应与部署脚本处于同一目录下，也可以使用第一个非选项参数来指定
- 默认情况下在 `kube-templates` 目录下获取 Kubernetes 模板文件，或者通过 `-t` 参数指定。
- 默认情况下 _不会_ 部署 GlusterFS，允许在任何现有的 GlusterFS 集群中使用 hekebi。通过 `-g` 参数以 DaemonSet 的方式部署 GlusterFS 至拓扑文件指定的节点上。

# 遇到的问题

## 1. daemonset/glusterfs 启动的 pod 始终处于 READY 0/1

查看 daemonset/glusterfs 配置

```console
$ kubectl get -o yaml daemonset/glusterfs
...
        livenessProbe:
          exec:
            command:
            - /bin/bash
            - -c
            - if command -v /usr/local/bin/status-probe.sh; then /usr/local/bin/status-probe.sh
              liveness; else systemctl status glusterd.service; fi
          failureThreshold: 50
          initialDelaySeconds: 40
          periodSeconds: 25
          successThreshold: 1
          timeoutSeconds: 3
        name: glusterfs
        readinessProbe:
          exec:
            command:
            - /bin/bash
            - -c
            - if command -v /usr/local/bin/status-probe.sh; then /usr/local/bin/status-probe.sh
              readiness; else systemctl status glusterd.service; fi
          failureThreshold: 50
          initialDelaySeconds: 40
          periodSeconds: 25
          successThreshold: 1
          timeoutSeconds: 3
...
```

在 pod 中执行 livenesss 检查的命令，得知原因是 `gluster-blockd.service` 未启动

```console
$ kubectl exec glusterfs-74rsl -- /usr/local/bin/status-probe.sh readiness
failed check: systemctl -q is-active gluster-blockd.service
```

检查 `gluster-blockd.service` 的日志得知是依赖的 `rpcbind.service` 未启动

```console
$ kubectl exec glusterfs-74rsl -- journalctl -u gluster-blockd.service
...
```

检查 `rpcbind.service` 的日志可知失败原因为 _Dependcy failed_

```console
$ kubectl exec glusterfs-74rsl -- journalctl -u rpcbind.service
...
```

检查 `rpcbind.service` 的依赖，发现端口 `111` 被占用，但未查出占用的进程

```console
$ kubectl exec glusterfs-74rsl -- systemctl cat rpcbind.service
# /usr/lib/systemd/system/rpcbind.service
[Unit]
Description=RPC bind service
DefaultDependencies=no

# Make sure we use the IP addresses listed for
# rpcbind.socket, no matter how this unit is started.
Requires=rpcbind.socket
Wants=rpcbind.target
After=systemd-tmpfiles-setup.service

[Service]
Type=forking
EnvironmentFile=/etc/sysconfig/rpcbind
ExecStart=/sbin/rpcbind -w $RPCBIND_ARGS

[Install]
WantedBy=multi-user.target

$ kubectl exec glusterfs-74rsl -- systemctl cat rpcbind.socket
# /usr/lib/systemd/system/rpcbind.socket
[Unit]
Description=RPCbind Server Activation Socket

[Socket]
ListenStream=/var/run/rpcbind.sock

# RPC netconfig can't handle ipv6/ipv4 dual sockets
BindIPv6Only=ipv6-only
ListenStream=0.0.0.0:111
ListenDatagram=0.0.0.0:111
ListenStream=[::]:111
ListenDatagram=[::]:111

[Install]
WantedBy=sockets.target

$ kubectl exec glusterfs-74rsl -- ss -nplt | grep 111
LISTEN     0      128          *:111                      *:*
LISTEN     0      128         :::111                     :::*
```

在宿主机上检查端口 111，发现是被 systemd（pid=1）占用

```console
$ ss -nplt | grep 111
LISTEN     0      128          *:111                      *:*                   users:(("systemd",pid=1,fd=29))
LISTEN     0      128         :::111                     :::*                   users:(("systemd",pid=1,fd=31))
```

`systemd` 不能随意停止，经 Google 得知，停止 rpcbind.socket 即可解除 111 端口占用。

```console
sudo systemctl stop rpcbind.socket
```

为了永久解决此问题，查找 `/usr/lib/systemd/system/rpcbind.socket` 属于哪个软件，并卸载

```console
yum -y erase $(rpm -qf /usr/lib/systemd/system/rpcbind.socket)
```

## 2. daemonset/glusterfs 无法创建 PV

glusterfs-74rsl Pod 异常终止，查看日志得知在执行命令 `pvcreate .... /dev/sdb` 时出错。查看日志得到

> Device /dev/sdb excluded by a filter

查看 lvm 的配置文件，检查 filter 配置

```console
$ grep filter /etc/lvm/lvm.conf
  # is used to drive LVM filtering like MD component detection, multipath
  # Configuration option devices/filter.
  # Run vgscan after changing the filter to regenerate the cache.
  # See the use_lvmetad comment for a special case regarding filters.
  # filter = [ "a|.*/|" ]
  # filter = [ "r|/dev/cdrom|" ]
  # filter = [ "a|loop|", "r|.*|" ]
  # filter = [ "a|loop|", "r|/dev/hdc|", "a|/dev/ide|", "r|.*|" ]
  # filter = [ "a|^/dev/hda8$|", "r|.*/|" ]
  # filter = [ "a|.*/|" ]
  # Configuration option devices/global_filter.
  # Because devices/filter may be overridden from the command line, it is
  # not suitable for system-wide device filtering, e.g. udev and lvmetad.
  # Use global_filter to hide devices from these LVM system components.
  # The syntax is the same as devices/filter. Devices rejected by
  # global_filter are not opened by LVM.
  # global_filter = [ "a|.*/|" ]
  # The results of filtering are cached on disk to avoid rescanning dud
  # This is a quick way of filtering out block devices that are not
  # by pvscan --cache), devices/filter is ignored and all devices are
  # scanned by default. lvmetad always keeps unfiltered information
  # which is provided to LVM commands. Each LVM command then filters
  # based on devices/filter. This does not apply to other, non-regexp,
  # filtering settings: component filters such as multipath and MD
  # are checked during pvscan --cache. To filter a device and prevent
  # devices/global_filter.
  # Configuration option activation/mlock_filter.
  # mlock_filter = [ "locale/locale-archive", "gconv/gconv-modules.cache" ]
```

未找到生效的 filter，经 Google 得知 GPT 格式的硬盘，在末尾有分区表，而 lvm 会将此类设备过滤，即使分区表是空的。

```console
$ parted /dev/sdb print
Model: VMware Virtual disk (scsi)
Disk /dev/sdb: 17.2GB
Sector size (logical/physical): 512B/512B
Partition Table: gpt
Disk Flags:

Number  Start  End  Size  File system  Name  Flags

```

使用命令 `wipefs -a /dev/sdb` 清楚 GPT 信息

```console
$ sudo wipefs -a /dev/sdb
/dev/sdb: 8 bytes were erased at offset 0x00000200 (gpt): 45 46 49 20 50 41 52 54
/dev/sdb: 8 bytes were erased at offset 0x3fffffe00 (gpt): 45 46 49 20 50 41 52 54
/dev/sdb: 2 bytes were erased at offset 0x000001fe (PMBR): 55 aa
/dev/sdb: calling ioclt to re-read partition table: Success
```

之后便可以使用 `pvcreate` 创建 pv

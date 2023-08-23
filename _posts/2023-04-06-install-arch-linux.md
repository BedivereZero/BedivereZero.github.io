---
layout: post
title: 安装 Arch Linux
date: 2023-04-06T14:07:54+08:00
categories: archlinux
---

在虚拟化平台上安装 Arch Linux 的过程记录。

## 创建虚拟机

选择 Bootload EFI

## 安装操作系统

按照 Arch Linux 的安装手册[^1] 下载安装镜像，并从镜像启动。

### 创建文件系统

在 `/dev/sda` 创建两个分区：efi 启动分区和系统分区。

```shell
fdisk /dev/sda
```

在 efi 启动分区创建 FAT32 格式的文件系统。

```shell
mkfs.fat -F 32 /dev/sda1
```

在系统分区创建 btrfs 格式的文件系统。

```shell
mkfs.btrfs /dev/sda2
```

挂载两个文件系统，先挂载系统分区。

```shell
mount /dev/sda2 /mnt
mount --mkdir /dev/sda1/ /mnt/boot
```

| Mount Point | Partition | Partition Type       | Filesystem Type | Size                    |
| :---------- | :-------- | :------------------- | :-------------- | :---------------------- |
| /mnt/boot   | /dev/sda1 | EFI system partition | FAT32           | 300MiB                  |
| /mnt        | /dev/sda2 | Linux x86-64         | btrfs           | Remainder of the device |

### 安装基础软件

修改文件 `/etc/pacman.d/mirrorlist` 选择一个 mirror。

安装基础软件。

```shell
pacstrap -K /mnt base linux linux-firmware
```

### 基础配置

### fstab

生成 fstab 文件。

```shell
getfstab -U /mnt >> /mnt/etc/fstab
```

### Chroot

chroot 到新的操作系统中。

```shell
arch-chroot /mnt
```

### Time Zone

设置时区为 `Asia/Shanghai`。

```shell
ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
```

### 本地化

安装软件 `vim` 以编辑文件。

```shell
pacman -S vim
```

编辑文件 `/etc/locale.gen`，取消 `en_GB.UTF-8` 行的注释。执行命令 `locale-gen` 生成本地化文件。

使用 `en_GB.UTF_8` 而不是 `en_US.UTF-8` 具有以下优点：

1. `date` 命令以 24 小时制现实时间。
2. 避免处理麻烦的英制单位。

创建文件 `/etc/locale.conf`，设置变量 `LANG`。

```conf
LANG=en_GB.UTF-8
```

### 配置 boot loader

使用 grub 作为 boot loader。安装软件 `grub` 和 `efibootmgr`。

```shell
pacman -S grub efibootmgr
```

安装 GRUB EFI 到目录 `/boot/EFI/GRUB`。

```shell
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
```

参数 `--efi-directory` 是 efi 分区挂载的目录，即 `/mnt/boot` 也就是 chroot 后的 `/boot`。

生成 grub.cfg。

```shell
grub-mkconfig -o /boot/grub/grub.cfg
```

### 重启

执行命令 `exit` 或通过快捷键 `Ctrl+d` 退出新安装的操作系统。

执行命令 `umount -R /mnt` 卸载已挂载 efi 分区和系统分区。

执行命令 `root` 重启操作系统，从新安装的操作系统启动。

## 安装后配置

### 账户

创建用户 `bedivere`。

```shell
useradd -m bedivere
```

参数 `-m` 代表创建用户的 home 目录。

加入用户组 `systemd-journal`，为了通过命令 `journalctl` 查看系统日志。

```shell
usermod -aG systemd-journal bedivere
```

创建用户的密码

```shell
passwd bedivere
```

### sudo

创建文件 `/etc/sudoers.d/00-user-bedivere`，允许用户 `bedivere` 执行所有命令，且不需要输入密码。

```sudoers
bedivere ALL=(ALL) NOPASSWD:ALL
```

### 网络

使用 `systemd-networkd` 管理网络，使用 `systemd-resolved` 管理域名解析。

创建文件 `/etc/systemd/network/20-wired.network

```ini
[Match]
Name = ens32

[Network]
Address = 10.2.184.58/24
Gateway = 10.2.184.1
```

启动服务 `systemd-networkd.service` 并设为开机启动。

```shell
systemctl enable --now systemd-networkd.service
```

创建文件 `/etc/systemd/resolved.conf.d/aishu.conf`。

```ini
[Resolve]
DNS = 10.4.4.25
# TODO: 确认是否包含 Domains
Domains = ~.
```

启动服务 `systemd-resolved.service` 并设为开机启动。

```shell
systemctl enable --now systemd-resolved.service
```

### 时间

使用 `systemd-timesyncd` 管理时间同步。

创建文件 `/etc/systemd/timesyncd.conf.d/aishu.conf`。

```ini
[Time]
NTP = ntp.aishu.cn
```

启动服务 `systemd-timesyncd.service` 并设为开机启动。

```shell
systemctl enable --now systemd-timesyncd.service
```

### 软件配置

#### ssh

使用 `OpenSSH` 作为 ssh server。

安装软件 `openssh`。

```shell
pacman -S openssh
```

向文件 `/etc/ssh/sshd_config` 追加下列内容，允许用户 `bedivere` 通过 ssh 登录。

```ssh_config
AllowUsers bedivere
```

启动服务 `sshd.service` 并设为开机启动。

```shell
systemctl enable --now sshd.service
```

**TODO: ssh client 配置**

#### git

修改用户 `bedivere` 的 git 配置，用于从 Azure Repos 获取 go module [^2] 。

创建文件 `$HOME/.gitconfig`。

```ini
[url "ssh://devops.aishu.cn/"]
  insteadOf = https://devops.aishu.cn/
```

创建文件 `$HOME/.netrc` 用于通过 Azure Repos 鉴权，获取私有 go module [^3]。

#### golang

设置 `GOPROXY` 和 `GOPRIVATE`，用于在内网获取公开和私有的 go module。

```shell
go env -w GOPROXY=proxy.aishu.cn,https://goproxy.cn
go env -w GOPRIVATE=devops.aishu.cn
```

#### oh-my-zsh
#### syncthing

#### .netrc


[^1]: https://wiki.archlinux.org/title/Installation_guide
[^2]: https://learn.microsoft.com/en-us/azure/devops/repos/git/go-get
[^3]:

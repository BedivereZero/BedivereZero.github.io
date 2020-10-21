---
layout: post
title: '利用多核加速 rpmbuild'
date: 2020-10-21T11:54:45Z
categories: utinity
---

最近在把一些使用 Tar 包发布的旧组件，改成 RPM 包并上传到私有仓库。发现构建过程未充分利用多核，导致构建很慢很慢————。修改 rpmbuild 的宏定义、构建参数充分利用多核加速构建。

## make 参数

旧项目好多是由一个简单的 Makefile 控制编译流程。`make` 提供了参数 `-j, --jobs` 控制同时执行任务的数量。前辈的经验是 CPU 核数 - 1 `make -j $[$(grep ) - 1]`，我一般是图省事而不限制（资源限制通过其他做，“我”能用的，“我”都要用，手动狗头）。

```bash
# Allow CPU NUMBER - 1 jobs at once
make -j $[ $(grep processor /proc/cpuinfo | wc -l) - 1 ]

# Infinite jobs
make -j
```

## rpmbuild 宏

修改 make 参数优化了 rpmbuild 的 %build，而打包生成 RPM 依然很慢。rpmbuild 通过宏 `_source_layout`、`_binary_layout` 控制打包 SRPM、RPM 所用的工具及参数。默认（通常）情况下 rpmbuild 使用 `xz` 压缩，压缩等级为 2，可以通过命令 `rpm -q --qf '%{PAYLOADCOMPRESSOR} %{PAYLOADFLAGS}'` 查询已有 RPM 包的压缩工具及参数。

```console
$ rpm -q --qf '%{PAYLOADCOMPRESSOR} %{PAYLOADFLAGS}\n' -p bash-4.2.46-34.el7.x86_64.rpm
xz 2
```

`rpmbuild` 所使用的宏定义在在文件 */usr/lib/rpm/macros* 和目录 */usr/lib/rpm/macros.d*。文件中列出了一些定义：

```macros
# /usr/lib/rpm/macros
#       Compression type and level for source/binary package payloads.
#               "w9.gzdio"      gzip level 9 (default).
#               "w9.bzdio"      bzip2 level 9.
#               "w7.xzdio"      xz level 7, xz's default.
#               "w7.lzdio"      lzma-alone level 7, lzma's default
#
#%_source_payload       w9.gzdio
#%_binary_payload       w9.gzdio
```

“众所周知” xz 支持多线程压缩，通过参数 `-T, --threads` 可以指定线程数量。那么问题就是如何让 rpmbuild 也能利用到 xz 的多线程压缩。

经过一番尝试发现 `w9T12.xzdio` 就可以使用 12 个线程压缩，推测是 `w` 之后 `.` 之前的字符会被传递给 xz。

```bash
rpmbuild -bb --define="_binary_payload w9T12.xzdio" numerous-docker-images.spec
```

到此为止 rpmbuild 所用时间已经大大缩短了🎉。

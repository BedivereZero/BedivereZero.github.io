---
layout: post
title: 静态编译 skopeo 并制作 rpm
date: 2025-07-29 21:51:14+08:00
categories: skopeo
---

为了在客户的国产化 Linux 发行版上离线安装 skopeo，静态编译并制作 rpm。

## 静态编译

下载源码，执行 `make help` 查看可以编译的目标。

```bash
# make help
Usage: make <target>

Defaults to building bin/skopeo and docs

 * 'install' - Install binaries and documents to system locations
 * 'binary' - Build skopeo with a container
 * 'bin/skopeo' - Build skopeo locally
 * 'bin/skopeo.OS.ARCH' - Build skopeo for specific OS and ARCH
 * 'test-unit' - Execute unit tests
 * 'test-integration' - Execute integration tests
 * 'validate' - Verify whether there is no conflict and all Go source files have been formatted, linted and vetted
 * 'check' - Including above validate, test-integration and test-unit
 * 'shell' - Run the built image and attach to a shell
 * 'clean' - Clean artifacts
 ```

执行 `make bin/skopeo.linux.amd64` 和 `make bin/skopeo.linux.arm64` 编译二进制。

编译得到的二进制是静态二进制，不依赖动态连接库。

```bash
# file bin/skopeo.*
bin/skopeo.linux.amd64: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, BuildID[sha1]=b6207402e43d0977920992290758b0af29675e09, with debug_info, not stripped
bin/skopeo.linux.arm64: ELF 64-bit LSB executable, ARM aarch64, version 1 (SYSV), statically linked, BuildID[sha1]=73a5d845b9eeb4ee21273a33b33a9b3c5a9fabca, with debug_info, not stripped
```

## 制作 RPM

由于之后要制作 deb，所以直接使用 `docker.io/library/debian:12.11` 作为制作 rpm 的环境。

安装制作 rpm 所需的工具：

- apt
- make

```spec
# skopeo.spec
%ifarch x86_64
%global goarch amd64
%endif
%ifarch aarch64
%global goarch arm64
%endif


Name:    skopeo
Version: 1.19.0
Release: 1%{?dist}
Summary: Inspect container images and repositories on registries
License: Apache-2.0 AND BSD-2-Clause AND BSD-3-Clause AND ISC AND MIT AND MPL-2.0
URL:     https://github.com/containers/%{name}
Source:  %{name}-v%{version}.tar.gz

%description
Command line utility to inspect images and repositories directly on Docker
registries without the need to pull them

%prep
%setup -q

%build
%{__make} bin/%{name}.linux.%{goarch}

%install
install -D -m 0755 -p bin/%{name}.linux.%{goarch} %{buildroot}%{_bindir}/%{name}

%files
%{_bindir}/%{name}
```

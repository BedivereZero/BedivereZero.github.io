---
layout: post
title: less 命令语法高亮
date: 2021-09-23T13:46:24+08:00
categories: shell
---

在 Ubuntu 20.04 下使 `less` 命令支持语法高亮。

# 配置

安装软件 `libsource-highlight-common`

```shell
$ apt install libsource-highlight-common
```

设置环境变量 `LESSOPEN`

我使用的是 zsh 所以修改`$HOME/.zshrc`，bash 对应的是 `$HOME/.profile` 或 `$HOME/.bash_profile`。

```shell
export LESSOPEN="|/usr/share/source-highlight/src-hilite-lesspipe.sh %s"
```

# 问题

我最初沿用了 CentOS 7 下的配置，先安装软件 `source-highlight`，再设置环境变量 ``LESSOPEN="/usr/bin/src-hilite-lesspipe.sh %s"``，没有生效，因为 `/usr/bin/src-hilite-lesspipe.sh` 不存在。

使用 `dpkg -L source-highlight | grep -e /usr/bin -e src-hilite-lesspipe.sh` 也没有找到脚本。

随后还是用`find /usr -type f -name src-hilite-lesspipe.sh` 找到的 `/usr/share/source-highlight/src-hilite-lesspipe.sh`。

使用 `dpkg -S` 查询到这个脚本属于 `libsource-highlight-common`，所以只需要安装这个软件就可以了。

也可以使用 `apt-file find FILENAME` 查找哪个软件提供了指定的文件。`apt-file` 命令属于软件 `apt-file`。
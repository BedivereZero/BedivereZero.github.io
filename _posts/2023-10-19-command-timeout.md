---
layout: post
title: Command `timeout`
date: 2023-10-19T10:28:51+08:00
categories: linux shell
---

命令 `timeout` 可以在有限的时间内执行命令。限制命令的执行时间，当到达指定的时间而命令仍在执行中时，`timeout` 会向命令发送信号 `TERM`。

## 格式

```shell
timeout [OPTION] DURATION COMMAND [ARG]...
timeout [OPTION]
```

## 描述

`timeout` 会启动命令 COMMAND，如果它在时间 DURATION 后仍然运行，则停止它。

`--preserve-status` 以与 COMMAND 相同的状态码退出，即使命令已超时。

`--foreground` 当 `timeout` 不是直接从 shell 运行时，允许 COMMAND 从 TTY 读取标准输入和获取 TTY 的信号。在这个模式下 COMMAND 的子进程永远不会超时。

`-k, --kill-after=DURATION` 如果 COMMAND 在指定时间后仍然在运行，向其发送信号 `KILL`。

`-s, --signal=SIGNAL` 发送指定信号而不是默认的 `TERM`。

`-v, --verbose` 在 stderr 中显示详细信息。

`--help` 显示帮助信息并退出。

`--version` 显示版本信息并退出。

DURATION 定义了超时时间，支持浮点数，缺少单位时以秒为单位。单位：`s` 代表秒，`m` 代表分，`h` 代表小时，`d` 代表天。

当到达超时时间时，`timeout` 会向 `COMMAND` 发送 `TERM` 或指定的信号。

## 返回码

`124` COMMAND 超时并且未指定 `--preserve-status`。

`125` COMMAND 执行失败。

`126` COMMAND 存在但无法调用。

`127` COMMAND 不存在。

`137` COMMAND 或 `timeout` 本事被发送信号 `KILL`。

## 例子

```bash
#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

rc=0
timeout 10m some-command || rc=$?
if [[ $rc == 124 ]]; then
  echo >&2 "some-command times out"
fi

exit $rc
```

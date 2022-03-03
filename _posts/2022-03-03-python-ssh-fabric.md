---
layout: post
title: Python SSH Library Fabirc
date: 2022-03-03T21dat:46:51+08:00
categories: python ssh
---

在 Python 中使用 Fabric 完成实现：

- 远程执行命令
- 转发端口
- 复用 SSH 连接

# 远程执行命令

```python
from fabric import Connection

conn = Connection(
    host="1.2.3.4",
    user="bediverezero",
    connect_kwargs={
        "key_filename": os.path.expanduser("~/.ssh/id_ed25519")
    },
)
result = conn.run("hostname")
```

`Connection.run` 默认为同步调用，通过参数 `asynchronous`。`result` 包含命令执行的返回值 `exited`、标准输出 `stdout`、异常输出 `stderr` 等。

## 命令输出不打印到控制台

`Connection` 的 `hide` 参数用于控制是否将命令的标准输出和异常输出打印至控制台。

合法参数有 3 个：

- `out` 或 `stdout` 隐藏标准输出
- `err` 或 `stderr` 隐藏异常输出
- `both` 或 `True` 隐藏标准输出和异常输出

# 转发端口

`Connection` 提供两个方法用于端口转发：

- `forward_local` 将 **远程** 端口转发到 **本地**
- `forward_remote` 将 **本地** 端口转发到 **远程**

# 复用 SSH 连接

避免在每次远程执行命令时创建 ssh 连接。

```python
for _ in range(10):
    with Connection("1.2.3.4") as conn:
        conn.run("true")
```

`Connection.is_connected` 可以用于判断连接是否已经连接，但通常不会用到，因为如果未连接时调用 `Connection.run()` 会自动连接。析构函数中调用 `Connection.close()` 前连接已经断开也没有关系，因为重复调用没有副作用。

> Terminate the network connection to the remote end, if open.
>
> If no connection is open, this method does nothing.


# 与 Paramiko 的区别

1. 抽象更高级，更易于使用，不必在深陷于 `client`、`transport`、`session` 这些概念。
2. 支持 sudo `Connection.sudo()`

---
layout: post
title: 手工安装 Visual Studio Code Server
date: 2023-08-23T09:27:51+08:00
categories: vscode
---

上周末，公司 IT 部收紧了内外网隔离策略，各操作系统软件源 mirror、vscode 都无法再从内网访问。这导致 Remote SSH 插件的安装 vscode-server 失败。所以尝试手工下载 vscode-server 并安装。

vscode-server 的下载链接是 `https://update.code.visualstudio.com/commit:$COMMIT_ID/server-linux-x64/stable`。其中 `COMMIT_ID` 可以从 vscode 的日志得到，下载得到的是一个 `tar+gzip` 的归档包。

使用 vscode 的插件 `Remote - SSH` 访问远程服务器失败时能看到如下日志

```log
[16:51:19.736] > Acquiring lock on /home/***/.vscode-server/bin/6c3e3dba23e8fadc360aed75ce36
> 3ba185c49794/vscode-remote-lock.***.6c3e3dba23e8fadc360aed75ce363ba185c4979
> 4
>
[16:51:19.754] > Installing to /home/***/.vscode-server/bin/6c3e3dba23e8fadc360aed75ce363ba1
```

其中 `6c3e3dba23e8fadc360aed75ce363ba1` 是要下载、安装的 vscode-server 的 commit id，所以 vscode-server 的下载链接是 `https://update.code.visualstudio.com/commit:6c3e3dba23e8fadc360aed75ce363ba1/server-linux-x64/stable`。

```bash
curl -o vscode-server-$COMMIT_ID.tar.gz https://update.code.visualstudio.com/commit:6c3e3dba23e8fadc360aed75ce363ba1/server-linux-x64/stable
```

复制 vscode-server 的归档包到服务端。解压 vscode-server 的归档包至 `$HOME/.vscode-server/bin/6c3e3dba23e8fadc360aed75ce363ba1`，如果目录不存在则需要先创建，解压需要跳过归档包的最上层目录。

```bash
tar -xf vscode-server-$COMMIT_ID.tar.gz -C $HOME/.vscode-server/bin/6c3e3dba23e8fadc360aed75ce363ba1 --strip-components=1
```

之后再启动 vscode，通过插件 `Remote - SSH` 就可以访问服务端了。

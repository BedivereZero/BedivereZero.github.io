---
layout: post
title: 'Docker Hub 镜像'
date: 2018-12-27 13:53:11 +0800
categories: docker
---

# Docker Hub 镜像

墙内直接使用 [Docker Hub][Docker Hub] 或者 [Google Container Registry][Google Container Registry] 会非常卡，所以使用墙内的镜像替代。

至于安全性，有证书保证应该没有问题。

## 修改 Docker 配置文件

操作系统是 `CentOS 7.4.1708`

将下列配置加入 `/etc/docker/daemon.json`

```json
{
    "registry-mirrors": [
        "https://docker.mirrors.ustc.edu.cn"
    ]
}
```

重启 Docker 服务

```shell
systemctl daemon-reload # 忘记这步是否必要了
systemctl restart docker.service
```

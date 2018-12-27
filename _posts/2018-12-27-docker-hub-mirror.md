---
layout: post
title: 'Docker Hub 镜像'
date: 2018-12-27 14:26:42 +0800
categories: docker
---

墙内直接使用 [Docker Hub][DockerHub] 或者 [Google Container Registry][GoogleContainerRegistry] 会非常卡，所以使用墙内的镜像替代。

至于安全性，有证书保证应该没有问题。

# 修改 Docker 配置文件

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

# 参考资料

- [国内 docker 仓库镜像对比](https://ieevee.com/tech/2016/09/28/docker-mirror.html)

[DockerHub]: https://hub.docker.com
[GoogleContainerRegistry]: https://cloud.google.com/container-registry

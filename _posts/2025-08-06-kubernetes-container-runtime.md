---
layout: post
title: 使用 containerd, CRI-O 替代 Docker 作为 Kubernetes 的 Container Runtime
date: 2025-08-06T15:58:07+0800
categories: kubernetes container
---

客户要求不可以使用 Docker，所以尝试使用 containerd 或 CRI-O 作为 Kubernetes 的 Container Runtime。

1. Linux 发行版 openEuler 24.03
2. kubernetes 1.23.4
3. cgroup driver 使用 `systemd`

## containerd

从 [containerd 1.7.27][containerd-v1.7.27] 下载 containerd。

根据文档 [Container Runtimes|Kubernetes#containerd][k8s-containerd] 修改 containerd 配置。

```toml
# /etc/containerd/config.toml
version: 2

[plugins]

    [plugins."io.containerd.grpc.v1.cri"]
        sandbox_image = "user.private.repo/pause:3.6"

        [plugins."io.containerd.grpc.v1.cri".containerd]
            default_runtime_name = "runc"
            disable_snapshot_annotations = true
            snapshotter = "overlayfs"

            [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]

                [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
                    runtime_type = "io.containerd.runc.v2"
                    sandbox_mode = "podsandbox"

                    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
                        SystemdCgroup = true
```

`sandbox_image`, `SystemdCgroup` 之外的字段未在文档中提及，但仍然需要。

如果缺少 `version: 2` 那么 `sandbox_image` 不生效，containerd 启动后仍然使用 `registry.k8s.io/pause:3.10` 作为 sandbox。

如果缺少其他字段，containerd 无法正常启动容器，`kubeadm init` 会卡在 kubelet 启动 control plane 的 static pod。

初始化 Kubernetes 集群。

```console
kubeadm init --image-repository=user.private.repo --cri-socket=/run/containerd/containerd.sock
```

参数：

- `--image-repository` 指定私有镜像仓库
- `--cri-socket` 指定连接 CRI 所用的 socket

## CRI-O

添加 CRI-O 仓库

```bash
CRIO_VERSION="v1.32"
REPO_FILE="/etc/yum.repos.d/isv:kubernetes:addons:cri-o:stable:${CRIO_VERSION}.repo"
REPO_URL="https://download.opensuse.org/repositories/isv:/kubernetes:/addons:/cri-o:/stable:/${CRIO_VERSION}/rpm/isv:kubernetes:addons:cri-o:stable:${CRIO_VERSION}.repo"

curl -o "${REPO_FILE}" "${REPO_URL}"
```

安装 CRI-O v1.32.1

```console
dnf install cri-o
```

根据文档 [Overriding the sandbox (pause) image][k8s-crio-pause] 添加配置文件 `/etc/crio/crio.conf.d/10-pause.conf`。

```toml
[crio.image]
pause_image = "user.private.repo/pause:3.6"
```

CRI-O 默认使用 `systemd` 作为 cgroup driver 不需要额外配置 [^1]。

通过 cri-o 的 http 接口 `GET /info` 查看 cgroup driver。

```console
curl --unix-socket /var/run/crio/crio.sock http://localhost/info
```

返回值

```json
{
  "storage_driver": "overlay",
  "storage_image": "",
  "storage_root": "/var/lib/containers/storage",
  "cgroup_driver": "systemd",
  "default_id_mappings": {
    "uids": [
      {
        "container_id": 0,
        "host_id": 0,
        "size": 4294967295
      }
    ],
    "gids": [
      {
        "container_id": 0,
        "host_id": 0,
        "size": 4294967295
      }
    ]
  }
}
```

初始化 Kubernetes 集群。

```console
kubeadm init --image-repository=user.private.repo --cri-socket=/run/crio/crio.sock
```

kubelet 启动静态 pod 失败，日志中存在报错:

```log
Aug 04 15:42:48 node-71-191 kubelet[135681]: E0805 15:42:48.052334  135681 remote_runtime.go:416] "CreateContainer in sandbox from runtime service failed" err="rpc error: code = Unknown desc = user specified image not specified, cannot verify image signature" podSandboxID="e0e0c365f6c111edcd5d0b8bb528a56fd4a2a9463c0ad9901dffdc371bfe438a"
```

在 CRI-O v1.32.1 的源码中搜索 `user specified image not specified, cannot verify image signature` 可以得到 [cri-o/server/container_create_linux.go:221][cri-o/server/container_create_linux.go:221]

```go
// WARNING: This hard-codes an assumption that SignaturePolicyPath set specifically for the namespace is never less restrictive
// than the default system-wide policy, i.e. that if an image is successfully pulled, it always conforms to the system-wide policy.
if systemCtx.SignaturePolicyPath != "" {
	// userSpecifiedImage is the input user provided in a Pod spec,
	// and captures the intent of the user; from that,
	// the signature policy is used to determine the relevant roots of trust and other requirements.
	userSpecifiedImage := ctr.Config().GetImage().UserSpecifiedImage

	// This will likely fail in a container restore case.
	// This is okay; in part because container restores are an alpha feature,
	// and it is meaningless to try to verify an image that isn't even an image
	// (like a checkpointed file is).
	if userSpecifiedImage == "" {
		return nil, errors.New("user specified image not specified, cannot verify image signature")
	}

	var userSpecifiedImageRef references.RegistryImageReference

	userSpecifiedImageRef, err = references.ParseRegistryImageReferenceFromOutOfProcessData(userSpecifiedImage)
	if err != nil {
		return nil, fmt.Errorf("unable to get userSpecifiedImageRef from user specified image %q: %w", userSpecifiedImage, err)
	}

	if err := s.StorageImageServer().IsRunningImageAllowed(ctx, &systemCtx, userSpecifiedImageRef, imageID); err != nil {
		return nil, err
	}
}
```

为了查看 `userSpecifiedImageRef` 是否真的为 `""`。修改配置文件 `/etc/sysconfig/crio` 设置日志级别为 debug。

```sh
# /etc/sysconfig/crio
CRIO_CONFIG_OPTIONS="--log-level=debug"
# use "--enable-metrics" and "--metrics-port value"
#CRIO_METRICS_OPTIONS="--enable-metrics"

#CRIO_NETWORK_OPTIONS=
#CRIO_STORAGE_OPTIONS=
```

重启 CRI-O。因为修改了命令行参数，所以不能 reload，必须 restart。

```bash
systemctl restart crio.service
```

查看 CRI-O 的日志。

```log
Aug 05 15:42:48 node-xxxx crio[185492]: time="2025-08-05T15:42:48.04893036+08:00" level=debug msg="Request: &CreateContainerRequest{...,Config:&ContainerConfig{...,Image:&ImageSpec{...,UserSpecifiedImage:,RuntimeHandler:,},},}" file="interceptors/interceptors.go:63" id=6fc3c0b3-5696-40a5-b3a4-678b259da716 name=/runtime.v1.RuntimeService/CreateContainer
```

`UserSpecifiedImage` 确实为 `""`，升级 kubelet 到 v1.33.3 重新初始化 Kubernetes 没有报错且 `UserSpecifiedImage` 不为 `""`。

在 [gh-k8s] 找到相关 issue [Add user specified image to CRI ContainerConfig #118652][gh-k8s-issue-118652]。

Kubernetes v1.28 在 CRI 添加 `user_specified_image` 用于验证容器镜像。Kubernetes 升级风险太大，尝试绕过这段验证。

修改配置文件 `/etc/crio/crio.conf.d/10-crio.conf`

```diff
@@ -1,5 +1,2 @@
- [crio.image]
- signature_policy = "/etc/crio/policy.json"
-
[crio.runtime]
default_runtime = "crun"
```

重启 CRI-O 后成功初始化 Kubernetes。

[^1]: [Container Runtimes|Kubernetes#cgroup driver][k8s-crio-cgroup-driver]

[gh-k8s]: https://github.com/kubernetes/kubernetes
[gh-k8s-issue-118652]: https://github.com/kubernetes/kubernetes/pull/118652
[containerd-v1.7.27]: https://github.com/containerd/containerd/releases/tag/v1.7.27
[k8s-containerd]: https://kubernetes.io/docs/setup/production-environment/container-runtimes/#containerd
[k8s-crio-pause]: https://kubernetes.io/docs/setup/production-environment/container-runtimes/#override-pause-image-cri-o
[k8s-crio-cgroup-driver]: https://kubernetes.io/docs/setup/production-environment/container-runtimes/#cgroup-driver
[cri-o/server/container_create_linux.go:221]: https://github.com/cri-o/cri-o/blob/217bc2fe5c7b94e217d13c1c3809922c76f6107d/server/container_create_linux.go#L221

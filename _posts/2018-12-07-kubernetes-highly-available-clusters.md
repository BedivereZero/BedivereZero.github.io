---
layout: post
title: 'Kubernetes 高可用集群'
date: 2018-12-07 18:33:15 +0800
categories: kubernetes
---

# 背景

Kubernetes 默认部署下，Master 节点上的几个服务 `kube-apiserver`、`kube-scheduler`、`kube-controller-manager`和`etcd`是单点的而且都位于同一个节点上。Master 节点一但挂掉，虽然不影响已部署的应用，但整个 Kubernetes 集群不可控，无法变更。

# 技术方案

前三个服务也都是无状态服务，原 Master 节点挂掉后只需要在新的 Master 节点上启动即可。只有 `etcd` 是有状态服务涉及数据一致性，Kubernetes 高可用等同于 `etcd` 高可用。

`etcd` 高可用需要三个示例，所以需要三个 Kubernetes 节点作为 Master 节点。

通过`keepalived`实现 Kubernetes 高可用。`keepalived`提供一个 VIP，通过VIP关联所有 Master 节点。`lvs`提供端口转发功能，默认配置 `kube-apiserver` 的端口是 6443

使用 `kubeadm` 部署三节点 Kubernetes 高可用集群，**此高可用方案依然处于实验中，并将在后续版本简化。**

## 依赖

* 操作系统：CentOS 7.4.1708
* Docker：18.06.1-ce
* Kubernetes：v1.12.3
* 防火墙开放端口
  * 6443/tcp：Kubernetes API server
  * 2379-2380/tcp：etcd server client API
  * 10250：Kubelet API
  * 10251：kube-scheduler
  * 10252：kube-controller-manager
* 关闭系统交换区：`swapoff --all`
* 所有节点需要 sudo 权限
* 所有节点已经安装 `kubeadm` 和 `kubelet`。`kubectl` 不是必需的。

## 部署 Kubernetes

CNI 网络插件 `Calico` 要求 CIDR 为 `192.168.0.0/16`，所以在`ClusterConfiguration.networking.podSubnet` 设为 `192.168.0.0/16`

| Hostname | IP address      |
| -------- | --------------- |
| node-181 | 192.168.136.181 |
| ndde-182 | 192.168.136.182 |
| node-183 | 192.168.136.183 |

### 为 kube-apiserver 创建负载均衡器

所有节点安装 `keepalived`，并设置负载端口为 `6443`

* VIP：192.168.136.177

### 部署第一个节点

创建配置文件保存为 `kubeadm-config.yaml`

```yaml
apiVersion: kubeadm.k8s.io/v1alpha3
kind: ClusterConfiguration
kubernetesVersion: stable
apiServerCertSANs:
- "LOAD_BALANCER_DNS"
controlPlaneEndpoint: "LOAD_BALANCER_DNS:LOAD_BALANCER_PORT"
etcd:
  local:
    extraArgs:
      name: "CP0_HOSTNAME"
      listen-client-urls: "https://127.0.0.1:2379,https://CP0_IP:2379"
      advertise-client-urls: "https://CP0_IP:2379"
      listen-peer-urls: "https://CP0_IP:2380"
      initial-advertise-peer-urls: "https://CP0_IP:2380"
      initial-cluster: "CP0_HOSTNAME=https://CP0_IP:2380"
    serverCertSANs:
      - CP0_HOSTNAME
      - CP0_IP
    peerCertSANs:
      - CP0_HOSTNAME
      - CP0_IP
networking:
    # This CIDR is a Calico default. Substitute or remove for your CNI provider.
    podSubnet: "192.168.0.0/16"
```

* `LOAD_BALANCER_DNS` 为 Keepalived 配置的 VIP，这里为 `192.168.136.177`
* `LOAD_BALANCER_PORT` 为 Keepalived 配置的转发端口，这里为 `6443`
* `CP0_HOSTNAME` 为第一个 Master 节点的 Hostname，这里为 `node-181`
* `CP0_IP` 为第一个 Master 节点的 IP 地址，这里为 `192.168.136.181`

确保节点环境干净的情况下执行以下命令：

```shell
sudo kubeadm init --config=kubeadm-config.yaml
```

应用 CNI 网络插件 Calico：

```shell
kubectl -f apply kubernetes/configurations/{calico,rbac-kdd}.yaml
```

复制下列身份验证文件到其他节点：

```shell
CONTROL_PLANE_IPS="192.168.136.182 192.168.136.183"
for host in ${CONTROL_PLANE_IPS}; do
    scp /etc/kubernetes/pki/ca.crt root@$host:
    scp /etc/kubernetes/pki/ca.key root@$host:
    scp /etc/kubernetes/pki/sa.key root@$host:
    scp /etc/kubernetes/pki/sa.pub root@$host:
    scp /etc/kubernetes/pki/front-proxy-ca.crt root@$host:
    scp /etc/kubernetes/pki/front-proxy-ca.key root@$host:
    scp /etc/kubernetes/pki/etcd/ca.crt root@$host:etcd-ca.crt
    scp /etc/kubernetes/pki/etcd/ca.key root@$host:etcd-ca.key
    scp /etc/kubernetes/admin.conf root@$host:
done
```

### 部署第二个节点

创建配置文件，保存为 `kubeadm-config.yaml`

```yaml
apiVersion: kubeadm.k8s.io/v1alpha3
kind: ClusterConfiguration
kubernetesVersion: stable
apiServerCertSANs:
- "LOAD_BALANCER_DNS"
controlPlaneEndpoint: "LOAD_BALANCER_DNS:LOAD_BALANCER_PORT"
etcd:
  local:
    extraArgs:
      name: "CP1_HOSTNAME"
      listen-client-urls: "https://127.0.0.1:2379,https://CP1_IP:2379"
      advertise-client-urls: "https://CP1_IP:2379"
      listen-peer-urls: "https://CP1_IP:2380"
      initial-advertise-peer-urls: "https://CP1_IP:2380"
      initial-cluster: "CP0_HOSTNAME=https://CP0_IP:2380,CP1_HOSTNAME=https://CP1_IP:2380"
      initial-cluster-state: existing
    serverCertSANs:
      - CP1_HOSTNAME
      - CP1_IP
    peerCertSANs:
      - CP1_HOSTNAME
      - CP1_IP
networking:
    # This CIDR is a calico default. Substitute or remove for your CNI provider.
    podSubnet: "192.168.0.0/16"
```

* `LOAD_BALANCER_DNS` 为 Keepalived 配置的 VIP，这里为 `192.168.136.177`
* `LOAD_BALANCER_PORT` 为 Keepalived 配置的转发端口，这里为 `6443`
* `CP0_HOSTNAME` 为第一个 Master 节点的 Hostname，这里为 `node-181`
* `CP0_IP` 为第一个 Master 节点的 IP 地址，这里为 `192.168.136.181`
* `CP1_HOSTNAME` 为第二个 Master 节点的 Hostname，这里为 `node-182`
* `CP1_IP` 为第二个 Master 节点的 IP 地址，这里为 `192.168.136.182`

移动下列文件：

```shell
mkdir -p /etc/kubernetes/pki/etcd
mv /root/ca.crt /etc/kubernetes/pki/
mv /root/ca.key /etc/kubernetes/pki/
mv /root/sa.pub /etc/kubernetes/pki/
mv /root/sa.key /etc/kubernetes/pki/
mv /root/front-proxy-ca.crt /etc/kubernetes/pki/
mv /root/front-proxy-ca.key /etc/kubernetes/pki/
mv /root/etcd-ca.crt /etc/kubernetes/pki/etcd/ca.crt
mv /root/etcd-ca.key /etc/kubernetes/pki/etcd/ca.key
mv /root/admin.conf /etc/kubernetes/admin.conf
```

通过 kubeadm phase 命令启动 kubelet：

```shell
kubeadm alpha phase certs all --config kubeadm-config.yaml
kubeadm alpha phase kubelet config write-to-disk --config kubeadm-config.yaml
kubeadm alpha phase kubelet write-env-file --config kubeadm-config.yaml
kubeadm alpha phase kubeconfig kubelet --config kubeadm-config.yaml
systemctl start kubelet
```

执行下列命令添加节点至 etcd 集群

```shell
export CP0_IP=192.168.136.181
export CP0_HOSTNAME=node-181
export CP1_IP=192.168.136.182
export CP1_HOSTNAME=node-182

kubeadm alpha phase etcd local --config kubeadm-config.yaml
export KUBECONFIG=/etc/kubernetes/admin.conf
kubectl exec -n kube-system etcd-${CP0_HOSTNAME} -- etcdctl --ca-file /etc/kubernetes/pki/etcd/ca.crt --cert-file /etc/kubernetes/pki/etcd/peer.crt --key-file /etc/kubernetes/pki/etcd/peer.key --endpoints=https://${CP0_IP}:2379 member add ${CP1_HOSTNAME} https://${CP1_IP}:2380
```

* 这个命令将导致 etcd 集群不可用，直到新的节点加入 etcd 集群。

将节点标记为 Master 节点

```shell
kubeadm alpha phase kubeconfig all --config kubeadm-config.yaml
kubeadm alpha phase controlplane all --config kubeadm-config.yaml
kubeadm alpha phase kubelet config annotate-cri --config kubeadm-config.yaml
kubeadm alpha phase mark-master --config kubeadm-config.yaml
```

### 部署第三个节点

创建配置文件 kubeadm-config.yaml

```yaml
apiVersion: kubeadm.k8s.io/v1alpha3
kind: ClusterConfiguration
kubernetesVersion: stable
apiServerCertSANs:
- "LOAD_BALANCER_DNS"
controlPlaneEndpoint: "LOAD_BALANCER_DNS:LOAD_BALANCER_PORT"
etcd:
  local:
    extraArgs:
      name: "CP2_HOSTNAME"
      listen-client-urls: "https://127.0.0.1:2379,https://CP2_IP:2379"
      advertise-client-urls: "https://CP2_IP:2379"
      listen-peer-urls: "https://CP2_IP:2380"
      initial-advertise-peer-urls: "https://CP2_IP:2380"
      initial-cluster: "CP0_HOSTNAME=https://CP0_IP:2380,CP1_HOSTNAME=https://CP1_IP:2380,CP2_HOSTNAME=https://CP2_IP:2380"
      initial-cluster-state: existing
    serverCertSANs:
      - CP2_HOSTNAME
      - CP2_IP
    peerCertSANs:
      - CP2_HOSTNAME
      - CP2_IP
networking:
    # This CIDR is a calico default. Substitute or remove for your CNI provider.
    podSubnet: "192.168.0.0/16"
```

* `LOAD_BALANCER_DNS` 为 Keepalived 配置的 VIP，这里为 `192.168.136.177`
* `LOAD_BALANCER_PORT` 为 Keepalived 配置的转发端口，这里为 `6443`
* `CP0_HOSTNAME` 为第一个 Master 节点的 Hostname，这里为 `node-181`
* `CP0_IP` 为第一个 Master 节点的 IP 地址，这里为 `192.168.136.181`
* `CP1_HOSTNAME` 为第二个 Master 节点的 Hostname，这里为 `node-182`
* `CP1_IP` 为第二个 Master 节点的 IP 地址，这里为 `192.168.136.182`
* `CP2_HOSTNAME` 为第三个 Master 节点的 Hostname，这里为 `node-183`
* `CP2_IP` 为第三个 Master 节点的 IP 地址，这里为 `192.168.136.183`

移动下列文件：

```shell
mkdir -p /etc/kubernetes/pki/etcd
mv /root/ca.crt /etc/kubernetes/pki/
mv /root/ca.key /etc/kubernetes/pki/
mv /root/sa.pub /etc/kubernetes/pki/
mv /root/sa.key /etc/kubernetes/pki/
mv /root/front-proxy-ca.crt /etc/kubernetes/pki/
mv /root/front-proxy-ca.key /etc/kubernetes/pki/
mv /root/etcd-ca.crt /etc/kubernetes/pki/etcd/ca.crt
mv /root/etcd-ca.key /etc/kubernetes/pki/etcd/ca.key
mv /root/admin.conf /etc/kubernetes/admin.conf
```

通过 kubeadm phase 命令启动 kubelet：

```shell
kubeadm alpha phase certs all --config kubeadm-config.yaml
kubeadm alpha phase kubelet config write-to-disk --config kubeadm-config.yaml
kubeadm alpha phase kubelet write-env-file --config kubeadm-config.yaml
kubeadm alpha phase kubeconfig kubelet --config kubeadm-config.yaml
systemctl start kubelet
```

执行下列命令添加节点至 etcd 集群

```shell
export CP0_IP=192.168.136.181
export CP0_HOSTNAME=node-181
export CP2_IP=192.168.136.183
export CP2_HOSTNAME=node-183

kubeadm alpha phase etcd local --config kubeadm-config.yaml
export KUBECONFIG=/etc/kubernetes/admin.conf
kubectl exec -n kube-system etcd-${CP0_HOSTNAME} -- etcdctl --ca-file /etc/kubernetes/pki/etcd/ca.crt --cert-file /etc/kubernetes/pki/etcd/peer.crt --key-file /etc/kubernetes/pki/etcd/peer.key --endpoints=https://${CP0_IP}:2379 member add ${CP1_HOSTNAME} https://${CP1_IP}:2380
```

* 这个命令将导致 etcd 集群不可用，直到新的节点加入 etcd 集群。

将节点标记为 Master 节点

```shell
kubeadm alpha phase kubeconfig all --config kubeadm-config.yaml
kubeadm alpha phase controlplane all --config kubeadm-config.yaml
kubeadm alpha phase kubelet config annotate-cri --config kubeadm-config.yaml
kubeadm alpha phase mark-master --config kubeadm-config.yaml
```

## 验证

1. 在所有节点都可以使用 `kubectl` 获取、设置 Kubernetes 集群
2. Keepalived Master 挂掉之后，另外两个节点仍可以使用 `kubectl` 获取、设置 Kubernetes 集群

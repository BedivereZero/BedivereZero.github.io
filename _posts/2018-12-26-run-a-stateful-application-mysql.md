---
layout: post
title: '运行一个有状态应用 MySQL'
date: 2018-12-27 13:32:29 +0800
categories: kubernetes mysql
---

通过创建`StatefulSet`实现 MySQL 运行一主多从，使用异步复制。

MySQL 使用不安全的默认配置，仅关心 Kubernetes 运行有状态服务的一般场景。

# 目标

- 使用 `StatefulSet` 部署多副本的 MySQL
- 测试客户端连接
- 修改副本数量

# 开始之前

- 需要有一个 Kubernetes 集群
- 需要有一个动态 `PersistentVolume` 配置器，提供持久化存储以满足 `PersistentVolumeClaim`。如果没有则需要手工创建 `PersistentVolume`。

# 部署MySQL

这个用例中包括一个 `ConfigMap`，两个 `Service`，一个 `StatefulSet`。

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql
  labels:
    app: mysql
data:
  master.cnf: |
    # Apply this config only on the master.
    [mysqld]
    log-bin
  slave.cnf: |
    # Apply this config only on slaves.
    [mysqld]
    super-read-only
```

将上述的文件保存为 `mysql-configmap.yaml`，并通过以下命令应用：

```shell
kubectl apply -f mysql-configmap.yaml
```

这个 ConfigMap 提供了 my.cnf，允许独立控制 Master 和 Slave 的配置。这个配置中 Master 复制日志给 Slave，而 Slave 拒绝除了复制之外的任何写入。

ConfigMap 并不对不同的 Pod 做不同的配置，每个 Pod 根据 StatefulSet 控制器提供的信息决定在初始化时查看哪个部分。

## Service

```yaml
# Headless service for stable DNS entries of StatefulSet members.
apiVersion: v1
kind: Service
metadata:
  name: mysql
  labels:
    app: mysql
spec:
  ports:
  - name: mysql
    port: 3306
  clusterIP: None
  selector:
    app: mysql
---
# Client service for connecting to any MySQL instance for reads.
# For writes, you must instead connect to the master: mysql-0.mysql.
apiVersion: v1
kind: Service
metadata:
  name: mysql-read
  labels:
    app: mysql
spec:
  ports:
  - name: mysql
    port: 3306
  selector:
    app: mysql
```

将上述的文件保存为 `mysql-services.yaml`，并通过以下命令应用：

```shell
kubectl apply -f mysql-services.yaml
```

Headless Service 为 StatefulSet 创建的 Pod 提供了 DNS 解析。同一个集群，同一个命名空间下的 Pod 可以通过 `<pod-name>.mysql` 来访问 mysql 服务下的 Pod。

`mysql-read` 是一个普通服务，它有自己的 Cluster IP，可以给所有状态为 Ready 的 Pod 分配连接，包括 Master 和所有 Slave。

只有读才能使用 `mysql-read`。因为只有一个 Master 所以客户端需要通过 Headless Service 直接连接 Master Pod。

## StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  selector:
    matchLabels:
      app: mysql
  serviceName: mysql
  replicas: 3
  template:
    metadata:
      labels:
        app: mysql
    spec:
      initContainers:
      - name: init-mysql
        image: mysql:5.7
        command:
        - bash
        - "-c"
        - |
          set -ex
          # Generate mysql server-id from pod ordinal index.
          [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
          ordinal=${BASH_REMATCH[1]}
          echo [mysqld] > /mnt/conf.d/server-id.cnf
          # Add an offset to avoid reserved server-id=0 value.
          echo server-id=$((100 + $ordinal)) >> /mnt/conf.d/server-id.cnf
          # Copy appropriate conf.d files from config-map to emptyDir.
          if [[ $ordinal -eq 0 ]]; then
            cp /mnt/config-map/master.cnf /mnt/conf.d/
          else
            cp /mnt/config-map/slave.cnf /mnt/conf.d/
          fi
        volumeMounts:
        - name: conf
          mountPath: /mnt/conf.d
        - name: config-map
          mountPath: /mnt/config-map
      - name: clone-mysql
        image: gcr.io/google-samples/xtrabackup:1.0
        command:
        - bash
        - "-c"
        - |
          set -ex
          # Skip the clone if data already exists.
          [[ -d /var/lib/mysql/mysql ]] && exit 0
          # Skip the clone on master (ordinal index 0).
          [[ `hostname` =~ -([0-9]+)$ ]] || exit 1
          ordinal=${BASH_REMATCH[1]}
          [[ $ordinal -eq 0 ]] && exit 0
          # Clone data from previous peer.
          ncat --recv-only mysql-$(($ordinal-1)).mysql 3307 | xbstream -x -C /var/lib/mysql
          # Prepare the backup.
          xtrabackup --prepare --target-dir=/var/lib/mysql
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
      containers:
      - name: mysql
        image: mysql:5.7
        env:
        - name: MYSQL_ALLOW_EMPTY_PASSWORD
          value: "1"
        ports:
        - name: mysql
          containerPort: 3306
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          exec:
            command: ["mysqladmin", "ping"]
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          exec:
            # Check we can execute queries over TCP (skip-networking is off).
            command: ["mysql", "-h", "127.0.0.1", "-e", "SELECT 1"]
          initialDelaySeconds: 5
          periodSeconds: 2
          timeoutSeconds: 1
      - name: xtrabackup
        image: gcr.io/google-samples/xtrabackup:1.0
        ports:
        - name: xtrabackup
          containerPort: 3307
        command:
        - bash
        - "-c"
        - |
          set -ex
          cd /var/lib/mysql

          # Determine binlog position of cloned data, if any.
          if [[ -f xtrabackup_slave_info ]]; then
            # XtraBackup already generated a partial "CHANGE MASTER TO" query
            # because we're cloning from an existing slave.
            mv xtrabackup_slave_info change_master_to.sql.in
            # Ignore xtrabackup_binlog_info in this case (it's useless).
            rm -f xtrabackup_binlog_info
          elif [[ -f xtrabackup_binlog_info ]]; then
            # We're cloning directly from master. Parse binlog position.
            [[ `cat xtrabackup_binlog_info` =~ ^(.*?)[[:space:]]+(.*?)$ ]] || exit 1
            rm xtrabackup_binlog_info
            echo "CHANGE MASTER TO MASTER_LOG_FILE='${BASH_REMATCH[1]}',\
                  MASTER_LOG_POS=${BASH_REMATCH[2]}" > change_master_to.sql.in
          fi

          # Check if we need to complete a clone by starting replication.
          if [[ -f change_master_to.sql.in ]]; then
            echo "Waiting for mysqld to be ready (accepting connections)"
            until mysql -h 127.0.0.1 -e "SELECT 1"; do sleep 1; done

            echo "Initializing replication from clone position"
            # In case of container restart, attempt this at-most-once.
            mv change_master_to.sql.in change_master_to.sql.orig
            mysql -h 127.0.0.1 <<EOF
          $(<change_master_to.sql.orig),
            MASTER_HOST='mysql-0.mysql',
            MASTER_USER='root',
            MASTER_PASSWORD='',
            MASTER_CONNECT_RETRY=10;
          START SLAVE;
          EOF
          fi

          # Start a server to send backups when requested by peers.
          exec ncat --listen --keep-open --send-only --max-conns=1 3307 -c \
            "xtrabackup --backup --slave-info --stream=xbstream --host=127.0.0.1 --user=root"
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            cpu: 100m
            memory: 100Mi
      volumes:
      - name: conf
        emptyDir: {}
      - name: config-map
        configMap:
          name: mysql
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

将上述的文件保存为 `mysql-statefulset.yaml`，并通过以下命令应用：

```shell
kubectl apply -f mysql-statefulset.yaml
```

通过以下命令观察启动顺序：

```shell
kubectl get pods -w -l app=mysql
```

经过一段时间后 3 个 Pod 应该处于 Running 状态：

```shell
NAME      READY     STATUS    RESTARTS   AGE
mysql-0   2/2       Running   0          2m
mysql-1   2/2       Running   0          1m
mysql-2   2/2       Running   0          1m
```

如果没有看到任何进程，确保启用了动态 `PersistentVolume` 配置器。

如果没有动态 `PersistentVolume` 配置器，则需要手动创建 `PersistentVolume`

## PersistentVolume (optional)

```yaml
---
kind: PersistentVolume
apiVersion: v1
metadata:
  name: mysql-pv-0
  lables:
    type: local
spec:
  capacity:
    storage: 10Gi
    accessModes:
      - ReadWriteOnce
    hostPath:
      path: "/mnt/mysql/0"
```

根据副本数可能需要创建多个 `PersistenVolume`。

将上述的文件保存为 `mysql-pv.yaml`，并通过以下命令应用：

```shell
kubectl apply -f mysql-pv.yaml
```

### Capacity

定义了 PV 的容量

### AccessModes

- ReadWriteOnece - 只能以读写模式挂载给一个节点
- ReadOnlyMany - 以只读模式挂载给许多节点
- ReadWriteMany - 以读写模式挂载给许多节点

# 了解有状态Pod初始化

StatefulSet 控制器顺序启动 Pod，当一个 Pod 为 Ready 状态后再启动下一个。

控制器给每个 Pod 分配一个固定的名称 `<statefulset-name>-<ordinal-index>`，例如 `mysql-0`，`mysql-1`

# 测试客户端连接

测试写入

```shell
kubectl run mysql-client --image=mysql:5.7 -i --rm --restart=Never --\
  mysql -h mysql-0.mysql <<EOF
CREATE DATABASE test;
CREATE TABLE test.messages (message VARCHAR(250));
INSERT INTO test.messages VALUES ('hello');
EOF
```

使用 `mysql-read` 作为主机名测试读取

```shell
kubectl run mysql-client --image=mysql:5.7 -i -t --rm --restart=Never --\
  mysql -h mysql-read -e "SELECT * FROM test.messages"
```

测试 `mysql-read` 分发连接给各个 Pod

```shell
kubectl run mysql-client-loop --image=mysql:5.7 -i -t --rm --restart=Never --\
  bash -ic "while sleep 1; do mysql -h mysql-read -e 'SELECT @@server_id,NOW()'; done"
```

# 修改副本数量

修改副本数至 5：

```shell
kubectl scale statefulset mysql  --replicas=5
```

或者修改 `mysql-statefulset.yaml` 后重新应用

```diff
10c10
<   replicas: 3
---
>   replicas: 5
```

```shell
kubectl applyt -f mysql-statefulset.yaml
```

# 清理

- 删除 StatefulSet，会同时删除由 StatefulSet 生成的 Pod
- 删除 Service
- 删除 PersistentVoluem，如果是手动创建的
- 删除 ConfigMap

```shell
kubectl delete StatefulSet mysql
kubectl detete Service mysql mysql-read
kubectl delete PersistentVolume mysql-pv-0
```

也可由配置文件删除

```shell
kubectl delete -f mysql-statefulset.yaml
kubectl delete -f mysql-services.yaml
kubectl delete -f mysql-pv.yaml
kubectl delete -f mysql-configmap.yaml
```

# 参考文档

- [Run a Replicated Stateful Application](https://kubernetes.io/docs/tasks/run-application/run-replicated-stateful-application)

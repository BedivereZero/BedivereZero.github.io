"""
demo
"""

import json
import time
import hashlib
import os
import sys

import requests

from kubernetes import client
from kubernetes import config
from kubernetes import watch

from fabric import Connection
from paramiko import SSHClient

import urllib3.exceptions

from haproxy import create
from node import KubernetesNode

config.load_kube_config(config_file="kubeconfig.yaml")

NAMESPACE = "kube-system"
ENDPOINT_KEY = "kubeadm.kubernetes.io/kube-apiserver.advertise-address.endpoint"  # noqa
LABEL_SELECTOR = "tier=control-plane,component=kube-apiserver"


def create_configmap():
    """create configmap"""
    with open("haproxy.cfg", encoding="utf-8") as f:
        raw = f.read()
    core_v1 = client.CoreV1Api()
    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(
            name="proton-haproxy",
            labels={
                "proton-app": "proton-haproxy",
            },
        ),
        data={
            "haproxy.cfg": raw,
        },
    )
    try:
        core_v1.create_namespaced_config_map(
            namespace=NAMESPACE,
            body=configmap,
        )
    except client.ApiException as ex_create:
        print(f"create configmap {configmap.metadata.name!r} fail: {ex_create.reason}")
        if ex_create.reason == "Conflict":
            try:
                client.CoreV1Api().replace_namespaced_config_map(
                    namespace=NAMESPACE,
                    name=configmap.metadata.name,
                    body=configmap,
                )
            except client.ApiException as ex_replace:
                print(
                    f"replace configmap {configmap.metadata.name!r} fail: {ex_replace.reason}"
                )
            else:
                print(f"replace configmap {configmap.metadata.name!r} success")
    else:
        print(f"create configmap {configmap.metadata.name!r} success")


def delete_configmap():
    """delete configmap"""
    ret = client.CoreV1Api().delete_namespaced_config_map(
        namespace="kube-system", name="proton-haproxy"
    )
    print("delete success, return:\n%s" % ret)


def create_daemonset():
    """create daemonset"""
    hash_sha256 = hashlib.sha256()
    with open("haproxy.cfg", "rb") as f:
        hash_sha256.update(f.read())
    daemonset = client.V1DaemonSet(
        metadata=client.V1ObjectMeta(
            name="proton-haproxy",
            labels={
                "proton-app": "proton-haproxy",
            },
        ),
        spec=client.V1DaemonSetSpec(
            selector=client.V1LabelSelector(
                match_labels={
                    "proton-app": "proton-haproxy",
                },
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    annotations={
                        "checksum/config": hash_sha256.hexdigest(),
                    },
                    labels={
                        "proton-app": "proton-haproxy",
                    },
                ),
                spec=client.V1PodSpec(
                    containers=(
                        client.V1Container(
                            name="haproxy",
                            image="haproxy:2.5.4-alpine",
                            command=(
                                "haproxy",
                                "-f",
                                "/usr/local/etc/haproxy/haproxy.cfg",
                            ),
                            volume_mounts=(
                                client.V1VolumeMount(
                                    name="config",
                                    mount_path="/usr/local/etc/haproxy",
                                ),
                            ),
                        ),
                    ),
                    volumes=(
                        client.V1Volume(
                            name="config",
                            config_map=client.V1ConfigMapVolumeSource(
                                name="proton-haproxy",
                            ),
                        ),
                    ),
                    host_network=True,
                    node_selector={
                        "kubernetes.io/os": "linux",
                    },
                    tolerations=(
                        client.V1Toleration(
                            operator="Exists",
                        ),
                    ),
                ),
            ),
        ),
    )
    try:
        client.AppsV1Api().create_namespaced_daemon_set(
            namespace="kube-system",
            body=daemonset,
        )
    except client.ApiException as ex_create:
        print(f"create daemonset {daemonset.metadata.name!r} fail: {ex_create.reason}")
        if ex_create.reason == "Conflict":
            try:
                ret = client.AppsV1Api().patch_namespaced_daemon_set(
                    namespace=NAMESPACE,
                    name="proton-haproxy",
                    body=daemonset,
                )
            except client.ApiException as ex_replace:
                print(
                    f"replace daemonset {daemonset.metadata.name!r} fail: {ex_replace.reason!s}"
                )
            else:
                print(f"replace daemonset {daemonset.metadata.name!r} success")
    else:
        print(f"create daemonset {daemonset.metadata.name!r} success")


def list_nodes():
    """list nodes"""
    core_v1 = client.CoreV1Api()
    ret = core_v1.list_node()
    for n in ret.items:
        for address in n.status.addresses:
            print(f"{n.metadata.name}\t{address.type}\t{address.address}")


def watch_endpoint():
    """watch"""
    client_core_v1 = client.CoreV1Api()
    delay = 1
    while True:
        try:
            w = watch.Watch()
            for event in w.stream(
                client_core_v1.list_namespaced_pod,
                namespace=NAMESPACE,
                label_selector=LABEL_SELECTOR,
            ):
                print(
                    "endpoint: %s" % event["object"].metadata.annotations[ENDPOINT_KEY]
                )
                for address in event["object"].status["addresses"]:
                    print("address %s", address)
        except Exception as ex:
            print("exception: %s" % ex)
            print("sleep %0.3f seconds" % delay)
            time.sleep(delay)
            delay = delay * 2


def checksum_sha256():
    """checksum sha256"""
    hash_sha256 = hashlib.sha256()
    with open("haproxy.cfg", mode="rb") as f:
        hash_sha256.update(f.read())
    print(f"{hash_sha256.hexdigest()}")


COUNT = 1


def remote_hostname_fabric():
    """remote hostname"""
    connection = Connection(
        host="1.116.101.19",
        user="root",
        connect_kwargs={
            "key_filename": os.path.expanduser("~/.ssh/id_ed25519"),
        },
    )
    result = connection.run("echo a > /dev/stdout; echo b > /dev/stderr", hide="both")
    sys.stdout.write(f"result.stdout:\n{result.stdout}\n")
    sys.stderr.write(f"result.stderr:\n{result.stderr}\n")
    connection.close()
    connection.close()


def remote_hostname_paramiko():
    """remote hostname"""
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.connect(
        hostname="1.116.101.19",
        username="root",
        key_filename=os.path.expanduser("~/.ssh/id_ed25519"),
    )
    for _ in range(COUNT):
        ssh_client.exec_command("hostname")


def forward_local():
    """forward local"""
    connection = Connection(
        host="1.116.101.19",
        user="root",
        connect_kwargs={
            "key_filename": os.path.expanduser("~/.ssh/id_ed25519"),
        },
    )
    # paramiko.ssh_exception.SSHException: TCP forwarding request denied
    # 转发反了。
    with connection.forward_local(8443):
        resp = requests.get(
            "https://127.0.0.1:8443/version",
            # get ca temp file path from kubeconfig client library
            verify=client.Configuration.get_default_copy().ssl_ca_cert,
        )
        version = resp.json()
        json.dump(
            version,
            sys.stdout,
            indent=4,
            sort_keys=True,
        )
        sys.stdout.write(os.linesep)


def main():
    """main"""
    forward_local()


if __name__ == "__main__":
    main()

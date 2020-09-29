---
layout: post
title: '禁用 FireFox 更新'
date: 2020-09-29 08:36:58 +0800
categories: utinity
---

工作环境禁用了大部分公网，导致 FireFox 能检查到存在更新但更新失败。通过修改配置的方式禁用更新检查，彻底告别恼人的更新提示。

## 打开 FireFox 的安装目录

Windows 环境下的安装目录是 *C:\Program Files\Mozilla Firefox*。如果修改过安装路径，可以通过右键 Firefox 的快捷方式 → 属性 → 打开文件所在位置找到。

## 创建策略配置 `policies.json`

相对路径：`distribution\policies.json`。策略配置是一个 JSON 文件，如果不存在就创建。如果存在修改下列配置即可。

```json
{
    "polices": {
        "DisableAppUpdate": true
    }
}
```

修改策略文件后需要重启 Firefox 使其生效。

## 参考

- [mozilla/policy-templates/README.md](https://github.com/mozilla/policy-templates/blob/master/README.md#disableappupdate)

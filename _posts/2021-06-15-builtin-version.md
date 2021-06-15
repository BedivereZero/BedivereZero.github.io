---
layout: post
title: 构建过程中生成版本号
date: 2021-06-15T17:50:20+08:00
categories: golang
---

版本信息在构建过程中从 git 生成, 而非硬编码在代码中。

## 版本信息

版本信息应该包括以下属性

- 语义版本号
  - Pre Release
    - Pre Release 应包含与上一个标签的距离
  - Build
    - git commit
    - git tree 是否干净
- Go 版本
- 构建时间
- 处理器架构, 操作系统

## 从 git 获取版本信息

`git describe --tag` 可以获取 `HEAD` 与上一个标签的距离及 commit id。

```console
$ git describe --tag
v0.1.0-alpha.0-10-gb0127f8
```

Git tree 是否干净可以通过 `git describe --tag --dirty` 或 `git status --porcelain` 判断。

```console
$ git describe --tag --dirty
v0.1.0-alpha.0-10-gb0127f8-dirty

$ git status --porcelain
M build/build-binary
```

## 其他信息

Go 的版本、处理器架构、操作系统可以通过 [runtime](https://pkg.go.dev/runtime) 获取当前运行时的相关信息。

构建时间可以通过 `date -u +%Y-%m-%dT%H:%M:SZ` 获取 rfc-3339 格式的时间。

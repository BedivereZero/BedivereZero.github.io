---
layout: post
title: '拉取Gerrit分支到本地Review'
date: 2018-08-23 09:30:12 +0800
categories: git gerrit
---

```url
http://hostname/#/c/18368/2

```

待Review的分支修改

```bash
git reset --hard 4c9cac3e46b8152819168031f8f7f6880e65ea81
```

重置本地至待Review分支的Parent(s)

```bash
git pull refs/changes/68/18368/2
```

拉取待Review的分支, 格式为refs/changes/id后两位/id/版本

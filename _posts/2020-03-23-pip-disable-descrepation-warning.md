---
layout: post
title: PIP disable DEPRECATION warning
date: 2020-03-23 13:00:51 +0800
categories: python
---

我司开发环境还是 CentOS 7.4 / 7.5 所以在用 `pip install` 或者 `pip list` 的时候会显示警告，提示 Python 2 即将在 2020 年 1 月 1 日停止维护。鉴于我司处于并将长期处于 Python 2.7.5 而开发环境天天看着这么个警告也蛮烦的, 所以决定把这个警告禁用掉。

处理的方式为使用环境变量 `PYTHONWARNINGS` 忽略警告，并在 `$HOME/.bash_profile` 中设置这个环境变量。

未使用指定环境变量 `PYTHONWARNINGS`

```console
$ pip list
DEPRECATION: Python 2.7 reached the end of its life on January 1st, 2020. Please upgrade your Python as Python 2.7 is no longer maintained. A future version of pip will drop support for Python 2.7. More details about Python 2 support in pip, can be found at https://pip.pypa.io/en/latest/development/release-process/#python-2-support
Package                          Version
-------------------------------- -----------
appdirs                          1.4.3
configobj                        4.7.2
...
```

指定环境变量 `PYTHONWARNINGS`

```console
$ PYTHONWARNINGS=ignore:DEPRECATION pip list
Package                          Version
-------------------------------- -----------
appdirs                          1.4.3
configobj                        4.7.2
...
```

```bash
# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

# User specific environment adn startup programs
PYTHONWARNINGS=ignore:DEPRECATION
export PYTHONWARNINGS
```

因为从没用过这个环境变量，所以只忽略了这一种警告。

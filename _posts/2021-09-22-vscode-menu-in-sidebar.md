---
layout: post
title: VSCode 在侧边栏显示菜单按钮
date: 2021-09-22T14:25:22+08:00
categories: vscode
---

节约小屏幕宝贵的可视面积，令 VSCode 在侧边栏显示菜单按钮。

默认配置：

![default](https://BedivereZero.github.io/assets/Screenshot%20from%202021-09-22%2014-29-17.png)

修改后的配置：

![modified](https://BedivereZero.github.io/assets/Screenshot%20from%202021-09-22%2014-34-18.png)

涉及的配置项

- `Window: Menu Bar Visibility`
- `Window: Title Bar Style`

> Window: Menu Bar Visibility
> Control the visibility of the menu bar. A setting of 'toggle' means that the menu bar is hidden and a single press of the Alt key will show it. A setting of 'compact' will move the menu into the sidebar.

如配置中所说设置为 `compact` 可以将菜单栏移植侧边栏。

> Menu is displayed as a compact button in the sidebar. This value is ignored when "Window: Title Bar Style" is `native`

选择 `compact` 时还有另外一段描述，当 `Window: Title Bar Style` 为 `native` 时忽略此配置。

所以，`Window: Title Bar Style` 设置为 `custom`，`Window: Menu Bar Visibility` 设置为 `compact` 即可。
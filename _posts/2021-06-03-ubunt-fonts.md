---
layout: post
title: 'Ubuntu 下 "门" 和 "复" 显示错误'
date: 2021-06-04T10:48:44+08:00
categories: ubuntu
---

Ubuntu 下部分中文字体显示错误，比如 “门”，“复”。最初以为是 Linux 下独特的字体风格，后来发现这是日文汉字，可以通过修改配置文件显示为中文汉字。

## 原因

Ubuntu 在当前所使用的字体中不包含某个字符时，会按照顺序从一系列候选字体中选择包含字符的字体。候选列表可以通过文件 `/etc/fonts/conf.d/64-language-selector-prefer.conf` 配置，分为**衬线字体**、**非衬线字体** 和 **等宽字体**。

Ubuntu 在安装了中文语言的情况下将 [Noto](https://www.google.com/get/noto) 系列字体添加到字体候选

例如衬线字体优先度如下：

- Noto Sans CJK JP
- Noto Sans CJK KR
- Noto Sans CJK SC
- Noto Sans CJK TC
- Noto Sans CJK HK

这样的配置导致日文字体包含的字符以日文字体显示。例如 “门”，日文中存在这个汉字所以就会用日文字体显示。其他在日文中不存在的汉字，或在 `Noto Sanas CJK JP` 和 `Noto Sans CJK SC` 字型相同的汉字则显示正常。

## 处理办法

修改配置文件 `/etc/fonts/conf.d/64-language-selector-prefer.conf` 将中文字体的优先度提高。

例如：

```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
	<alias>
		<family>sans-serif</family>
		<prefer>
			<family>Noto Sans CJK SC</family>
			<family>Noto Sans CJK TC</family>
			<family>Noto Sans CJK HK</family>
			<family>Noto Sans CJK JP</family>
			<family>Noto Sans CJK KR</family>
			<family>Lohit Devanagari</family>
		</prefer>
	</alias>
	<alias>
		<family>serif</family>
		<prefer>
			<family>Noto Serif CJK SC</family>
			<family>Noto Serif CJK TC</family>
			<family>Noto Serif CJK JP</family>
			<family>Noto Serif CJK KR</family>
			<family>Lohit Devanagari</family>
		</prefer>
	</alias>
	<alias>
		<family>monospace</family>
		<prefer>
			<family>Noto Sans Mono CJK SC</family>
			<family>Noto Sans Mono CJK TC</family>
			<family>Noto Sans Mono CJK HK</family>
			<family>Noto Sans Mono CJK JP</family>
			<family>Noto Sans Mono CJK KR</family>
		</prefer>
	</alias>
</fontconfig>

```

## 参考

- [Ubuntu上'门' '复' 字显示不正确](https://xlee00.github.io/2019/03/26/Ubuntu%E4%B8%8A-%E9%97%A8-%E5%A4%8D-%E5%AD%97%E6%98%BE%E7%A4%BA%E4%B8%8D%E6%AD%A3%E7%A1%AE)

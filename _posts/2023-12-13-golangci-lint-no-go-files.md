---
layout: post
title: golangci-lint 失败 no go files to analyze
date: 2023-12-13 15:46:25+08:00
categories: git golangci-lint
---

记录一次在本地完成开发后 push 到仓库，触发的流水线执行失败的排查过程。

## 问题原因

1. 重新创建 gti tag，获取导致 go module 失败‘
2. golangci-lint 的报错信息与实际原因不一致

## 排查过程

流水线失败部分的日志：

```log
+ golangci-lint run --config .golangci-.yml --out-format junit-xml ./... > $(Build.SourceDirectory)/report/$(LintReportName)
level=error msg="Running error: context loading failed: no go files to analyze"
```

因为在本地环境可以成功执行 `golangci-lint run`，所以第一时间怀疑是流水线的工作目录设置错误，导致 `golangci-lint` 未能找到需要分析的源码文件。通过在流水线中执行 `pwd`、`ls -al`、`find -type f` 确认工作目录没有错误，源码也被正确地 checkout。

其次怀疑是 golangci-lint 的配置错误，通过添加参数 `--no-config` 确认与配置无关。

怀疑是 pipeline step 中的操作导致 golangci-lint 失败。

```bash
set -ex
# 添加SSH KEY
cd /root/.ssh && ls -al
echo Installing $(sshKey.secureFilePath) to ssh key...
chown root:root $(sshKey.secureFilePath)
chmod 600 $(sshKey.secureFilePath)
cp $(sshKey.secureFilePath) /root/.ssh/id_rsa
ssh-keyscan -t rsa devops.example.org>> ~/.ssh/known_hosts
# 配置git config
git config --global url."ssh://devops.example.org/Organization/".insteadOf "https://devops.example.org/Organization/"
echo "machine devops.example.org login $(devops.username) password $(devops.token)" > /root/.netrc
cat /root/.netrc
export NETRC=/root/.netrc

mkdir $(Build.SourcesDirectory)/report
cd $(Build.SourcesDirectory)
touch cover.out
ls -al
# go generate ./...
golangci-lint run --config .golangci.yml --out-format junit-xml ./... > $(Build.SourcesDirectory)/report/$(LintReportName)
go test -v -coverprofile=cover.out ./... 2>&1 | go-junit-report > $(Build.SourcesDirectory)/report/$(UTReportName)
gocov convert cover.out | gocov-xml > $(Build.SourcesDirectory)/report/$(CoverageReportName)

# 编译
# go env -w CGO_ENABLED=0
go build -o ./$(svcName) -ldflags '-w -s' -gcflags '-N -l'  $(Build.SourcesDirectory)/cmd/server
```

经过逐个排查 step 内执行的命令，确认是这一段命令存在时 `golangci-lint` 会失败，不存在时就成功。

```bash
echo "machine devops.example.org login $(devops.username) password $(devops.token)" > /root/.netrc
```

这一段是根据 [Go Modules Reference] 添加的访问私有 Go Module 所用的身份认证信息，应该与 `golangci-lint` 分析 go 源码无关才对。

受 [Golang linter issues 'context loading failed: no go files to analyze'] 启发，问题可能在下载 go module 过程中。

```bash
$ go mod download
...
verifying devops.example.org/Organization/Project/_git/go-common@v1.0.4: checksum mismatch
	downloaded: h1:Ai9O0FGo9bcG8dkMxjZ2KPPMcrchs3lDItWduc2ht5Q=
	go.sum:     h1:Wto2v4Zv6gZrSppDzaSIJIuwFOMNM77EckvPIoVbsRw=
```

在 pipeline 中添加命令 `go mod download` 下载项目所依赖的 go module，发现公共库 go-common 的版本 v1.0.4 的内容和本地 go.sum 记录的不同。查看公共库 go-common 的源码仓库确实如此，有人重新创建了一个 tag v1.0.4。

最终升级 go-common 至 v1.0.5 绕过了这个坑。

[Go Modules Reference]: https://go.dev/ref/mod
[Golang linter issues 'context loading failed: no go files to analyze']: https://stackoverflow.com/questions/68000066/golang-linter-issues-context-loading-failed-no-go-files-to-analyze

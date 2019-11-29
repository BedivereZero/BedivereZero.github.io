---
layout: post
title: '安装 paramiko 失败'
date: 2019-11-29 08:21:33 +0800
categories: kubernetes
---

现有项目需要使用 paramiko，在 aarch64 机器上使用 pip 安装失败。

```console
$ pip install paramiko
...
  PASS: verify1
  PASS: sodium_utils2
  PASS: sodium_utils3
  PASS: core_ed25519
  /tmp/pip-install-2w753d/pynacl/src/libsodium/build-aux/test-driver:line 107: 51916 Killed                  "$@" > $log_file 2>&1
  FAIL: pwhash_scrypt
  PASS: pwhash_scrypt_ll
  PASS: scalarmult_ed25519
  PASS: siphashx24
  PASS: xchacha20
  ============================================================================
  Testsuite summary for libsodium 1.0.16
  ============================================================================
  # TOTAL: 72
  # PASS:  71
  # SKIP:  0
  # XFAIL: 0
  # FAIL:  1
  # XPASS: 0
  # ERROR: 0
  ============================================================================
  See test/default/test-suite.log
  Please report to https://github.com/jedisct1/libsodium/issues
  ============================================================================
  make[4]: *** [test-suite.log] Error 1
  make[4]: Leaving directory
`/tmp/pip-install-2w753d/pynacl/build/temp.linux-aarch64-2.7/test/default'
  make[3]: *** [check-TESTS] Error 2
  make[3]: Leaving directory
`/tmp/pip-install-2w753d/pynacl/build/temp.linux-aarch64-2.7/test/default'
  make[2]: *** [check-am] Error 2
  make[2]: Leaving directory
`/tmp/pip-install-2w753d/pynacl/build/temp.linux-aarch64-2.7/test/default'
  make[1]: *** [check-recursive] Error 1
  make[1]: Leaving directory
`/tmp/pip-install-2w753d/pynacl/build/temp.linux-aarch64-2.7/test'
  make: *** [check-recursive] Error 1
  Traceback (most recent call last):
    File "/root/paramiko/env/lib/python2.7/site-packages/pip/_vendor/pep517/_in_process.py",line 257, in <module>
      main()
    File "/root/paramiko/env/lib/python2.7/site-packages/pip/_vendor/pep517/_in_process.py",line 240, in main
      json_out['return_val'] = hook(**hook_input['kwargs'])
    File "/root/paramiko/env/lib/python2.7/site-packages/pip/_vendor/pep517/_in_process.py",line 182, in build_wheel
      metadata_directory)
    File "/tmp/pip-build-env-R38Alz/overlay/lib/python2.7/site-packages/setuptools/build_meta.py",line 209, in build_wheel
      wheel_directory, config_settings)
    File "/tmp/pip-build-env-R38Alz/overlay/lib/python2.7/site-packages/setuptools/build_meta.py",line 194, in _build_with_temp_dir
      self.run_setup()
    File "/tmp/pip-build-env-R38Alz/overlay/lib/python2.7/site-packages/setuptools/build_meta.py",line 237, in run_setup
      self).run_setup(setup_script=setup_script)
    File "/tmp/pip-build-env-R38Alz/overlay/lib/python2.7/site-packages/setuptools/build_meta.py",line 142, in run_setup
      exec(compile(code, __file__, 'exec'), locals())
    File "setup.py", line 255, in <module>
      "Programming Language :: Python :: 3.7",
    File "/tmp/pip-build-env-R38Alz/overlay/lib/python2.7/site-packages/setuptools/__init__.py",line 145, in setup
      return distutils.core.setup(**attrs)
    File "/usr/lib64/python2.7/distutils/core.py", line 152, in setup
      dist.run_commands()
    File "/usr/lib64/python2.7/distutils/dist.py", line 953, in run_commands
      self.run_command(cmd)
    File "/usr/lib64/python2.7/distutils/dist.py", line 972, in run_command
      cmd_obj.run()
    File "/tmp/pip-build-env-R38Alz/overlay/lib/python2.7/site-packages/wheel/bdist_wheel.py",line 192, in run
      self.run_command('build')
    File "/usr/lib64/python2.7/distutils/cmd.py", line 326, in run_command
      self.distribution.run_command(command)
    File "/usr/lib64/python2.7/distutils/dist.py", line 972, in run_command
      cmd_obj.run()
    File "/usr/lib64/python2.7/distutils/command/build.py", line 127, in run
      self.run_command(cmd_name)
    File "/usr/lib64/python2.7/distutils/cmd.py", line 326, in run_command
      self.distribution.run_command(command)
    File "/usr/lib64/python2.7/distutils/dist.py", line 972, in run_command
      cmd_obj.run()
    File "setup.py", line 179, in run
      subprocess.check_call(["make", "check"] + make_args, cwd=build_temp)
    File "/usr/lib64/python2.7/subprocess.py", line 542, in check_call
      raise CalledProcessError(retcode, cmd)
  subprocess.CalledProcessError: Command '['make', 'check']' returned
non-zero exit status 2
  ----------------------------------------
  ERROR: Failed building wheel for pynacl
  Running setup.py clean for pynacl
Failed to build pynacl
ERROR: Could not build wheels for pynacl which use PEP 517 and cannot
be installed directly
```

发现使用源码安装 PyNaCl-1.3.0 时失败，尝试使用源码 build，依然失败。

根据 ciprian-barbu 在 [jedisct1/libsodium#890][github/jedisct1/libsodium/issues/890] 的描述：

> I started debugging the actual test case and found the following:
>
> - the failing test case is always the same, tv3, test number 30 (starting from 0): "$7$8zzzzz/.....lgPchkGHqbeONR
> - on these server there is no SSE support (at least not as libsodium can use), which causes escrypt_r to call escrypt_kdf_nosse
> - escrypt_kdf_nosse receives some very nasty parameters, r=1073741823, p=1, N_log2=10
> - the total amount of memory computed as needed is 141149805084352 (about 128 TB!!!!)
> - the alloc_region function calls mmap, passing this huge param as size, but also specifying MAP_POPULATE flag
> - under "normal" circumstances, this mmap would fail, but in some special conditions this causes mmap to try and not only create memory pages, but also to reserve them into memory. There is no sane onfiguration that can ofer 128 TB of memory

PyNaCl 所使用的 libsodium-1.0.16 存在 bug。参考 [charmed-kubernetes/jenkins#360][github/charmed-kubernetes/jenkins/pull/360] 安装 PyNaCl-1.1.2。

```console
$ pip install paramiko PyNaCl==1.1.2
DEPRECATION: Python 2.7 will reach the end of its life on January 1st, 2020. Please upgrade your Python as Python 2.7 won't be maintained after that date. A future version of pip will drop support for Python 2.7. More details about Python 2 support in pip, can be found at https://pip.pypa.io/en/latest/development/release-process/#python-2-support
Looking in indexes: https://files.pythonhosted.org/simple
Collecting paramiko
  Downloading https://files.pythonhosted.org/packages/4b/80/74dace9e48b0ef923633dfb5e48798f58a168e4734bca8ecfaf839ba051a/paramiko-2.6.0-py2.py3-none-any.whl (199kB)
     |████████████████████████████████| 204kB 44.7MB/s
Collecting PyNaCl==1.1.2
  Downloading https://files.pythonhosted.org/packages/8d/f3/02605b056e465bf162508c4d1635a2bccd9abd1ee3ed2a1bb4e9676eac33/PyNaCl-1.1.2.tar.gz (3.1MB)
     |████████████████████████████████| 3.1MB 17.5MB/s
Collecting bcrypt>=3.1.3
  Downloading https://files.pythonhosted.org/packages/fa/aa/025a3ab62469b5167bc397837c9ffc486c42a97ef12ceaa6699d8f5a5416/bcrypt-3.1.7.tar.gz (42kB)
     |████████████████████████████████| 51kB 35.4MB/s
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
    Preparing wheel metadata ... done
Collecting cryptography>=2.5
  Downloading https://files.pythonhosted.org/packages/be/60/da377e1bed002716fb2d5d1d1cab720f298cb33ecff7bf7adea72788e4e4/cryptography-2.8.tar.gz (504kB)
     |████████████████████████████████| 512kB 45.4MB/s
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
    Preparing wheel metadata ... done
Requirement already satisfied: six in ./env/lib/python2.7/site-packages (from PyNaCl==1.1.2) (1.13.0)
Requirement already satisfied: cffi>=1.4.1 in ./env/lib/python2.7/site-packages (from PyNaCl==1.1.2) (1.13.2)
Collecting enum34; python_version < "3"
  Downloading https://files.pythonhosted.org/packages/c5/db/e56e6b4bbac7c4a06de1c50de6fe1ef3810018ae11732a50f15f62c7d050/enum34-1.1.6-py2-none-any.whl
Collecting ipaddress; python_version < "3"
  Downloading https://files.pythonhosted.org/packages/c2/f8/49697181b1651d8347d24c095ce46c7346c37335ddc7d255833e7cde674d/ipaddress-1.0.23-py2.py3-none-any.whl
Requirement already satisfied: pycparser in ./env/lib/python2.7/site-packages (from cffi>=1.4.1->PyNaCl==1.1.2) (2.19)
Building wheels for collected packages: bcrypt, cryptography
  Building wheel for bcrypt (PEP 517) ... done
  Created wheel for bcrypt: filename=bcrypt-3.1.7-cp27-cp27mu-linux_aarch64.whl size=53558 sha256=8bd3996986580ce67ae3a25c1d02ea930f3e70f0a901873a098d78ca91695951
  Stored in directory: /root/.cache/pip/wheels/ea/e4/6a/80eed786c4b8fe5df28b21f4c1e2cc6d4fdffddce3396c00f0
  Building wheel for cryptography (PEP 517) ... done
  Created wheel for cryptography: filename=cryptography-2.8-cp27-cp27mu-linux_aarch64.whl size=845945 sha256=2e6069976971a51d24cecc3e8a48d25e3ef0bd52b8f3a492e0f7f2df2f0a3133
  Stored in directory: /root/.cache/pip/wheels/1d/14/f4/09528d9a0d950eba0fbee2fec13c5d33b398db8f598359e4b2
Successfully built bcrypt cryptography
Building wheels for collected packages: PyNaCl
  Building wheel for PyNaCl (setup.py) ... done
  Created wheel for PyNaCl: filename=PyNaCl-1.1.2-cp27-cp27mu-linux_aarch64.whl size=359128 sha256=e582f14d7e24af6e54b8f7f3c5ede8a366157cc39e545c0e34d3e1aca99995ba
  Stored in directory: /root/.cache/pip/wheels/cb/eb/e0/5b18c520c0e6ae0576c84187368a7d58e4d5100c9ec2aec695
Successfully built PyNaCl
Installing collected packages: bcrypt, enum34, ipaddress, cryptography, PyNaCl, paramiko
Successfully installed PyNaCl-1.1.2 bcrypt-3.1.7 cryptography-2.8 enum34-1.1.6 ipaddress-1.0.23 paramiko-2.6.0
```

安装成功

## 参考

- [Stuck at Running setup.py bdist_whell for pynacl][github/pyca/pynacl/issues/486]
- [pwhash_scrypt test fails (escrypt_kdf_nosse) in mmap with invalid mem size][github/jedisct1/libsodium/issues/890]
- [pin pynacl to 1.1.2, the latest version compatible with pymacaroons and alt arches][github/charmed-kubernetes/jenkins/pull/360]

[github/pyca/pynacl/issues/486]: https://github.com/pyca/pynacl/issues/486
[github/jedisct1/libsodium/issues/890]: https://github.com/jedisct1/libsodium/issues/890
[github/charmed-kubernetes/jenkins/pull/360]: https://github.com/charmed-kubernetes/jenkins/pull/360

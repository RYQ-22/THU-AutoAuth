# THU-AutoAuth

这是一个用于清华大学用户注册管理系统 (`usereg.tsinghua.edu.cn`) 的自动化脚本。它能够自动获取本机的公网 IPv6 地址，通过 OCR 自动识别验证码完成登录，并提交“准入代认证”请求，从而使哑终端或本机获得外网访问权限。

目前没有 IPv4 支持，因为作者的 IPv4 认证在路由器上实现，而 IPv6 在 IPv4 认证完后无法在每台设备上通过 auth6 的 API 进行自动认证。稍加修改即可支持 IPv4。

## 主要功能

* **自动获取 IPv6**: 直接从网卡读取配置，智能过滤链路本地地址 (`fe80::`) 和回环地址，精准定位公网 IPv6。
* **验证码自动识别**: 集成 `ddddocr` 离线 OCR 引擎，自动识别 4 位数字验证码。
* **智能重试机制**: 内置验证码识别错误重试逻辑，识别失败或登录失败会自动刷新验证码并重试，直至成功。
* **无头/有头模式**: 基于 `Playwright`，支持可视化运行（调试）或后台静默运行。

## 使用方法

### 0. (可选) 虚拟环境配置

```
conda create -n auto-auth python=3.12
conda activate auto-auth
```

### 1. 安装依赖

```
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置账号

打开 `auth6.py`，修改顶部的配置区域：

```python
# --- 全局配置 ---
USERNAME = "YOUR_REAL_USERNAME" # 清华账号用户名
PASSWORD = "YOUR_REAL_PASSWORD" # 清华账号密码
MAX_RETRIES = 5                 # 登录最大重试次数
```

### 3. 运行脚本

```
python auth6.py
```

### 4. 自动化运行

`Windows` 下可通过 `Task Scheduler` 实现，`Linux` 下可通过 `systemd` 实现。

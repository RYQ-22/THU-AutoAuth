import re
import time
import socket
import sys
import psutil
import ddddocr
from playwright.sync_api import Playwright, sync_playwright

# --- 全局配置 ---
USERNAME = "YOUR_REAL_USERNAME" # 清华账号用户名
PASSWORD = "YOUR_REAL_PASSWORD" # 清华账号密码
MAX_RETRIES = 5                 # 登录最大重试次数

def get_nic_ipv6():
    """
    功能：遍历本机网卡，获取公网 IPv6 地址。
    逻辑：过滤掉回环地址 (::1) 和链路本地地址 (fe80开头)，优先返回全球单播地址。
    """
    try:
        # 获取所有网络接口的地址信息
        interfaces = psutil.net_if_addrs()

        for iface_name, addrs in interfaces.items():
            for addr in addrs:
                # 仅筛选 IPv6 类型的地址 (AF_INET6)
                if addr.family == socket.AF_INET6:
                    ip = addr.address

                    # 处理 Windows 系统特有的 Scope ID 问题 (例如: fe80::1%eth0)
                    if '%' in ip:
                        ip = ip.split('%')[0]

                    # 核心过滤规则：
                    # 1. 排除回环地址 (::1)
                    # 2. 排除链路本地地址 (fe80 开头，这种地址无法用于公网通信)
                    if ip != "::1" and not ip.lower().startswith("fe80"):
                        return ip

        # 遍历完所有网卡仍未找到符合条件的 IP
        raise Exception("未找到有效的公网 IPv6 地址 (Global Unicast Address)")

    except Exception as e:
        raise Exception(f"网卡读取失败: {str(e)}")

def run(playwright: Playwright) -> None:
    # --- 阶段 0: 环境检查 ---
    print("[-] 正在从网卡读取 IPv6 配置...")
    try:
        IPV6_ADDRESS = get_nic_ipv6()
        print(f"[+] 获取成功: {IPV6_ADDRESS}")
    except Exception as e:
        print(f"[!] 错误: {e}")
        print("[!] 请检查网线连接，或确认是否已分配到 IPv6 地址。")
        sys.exit(1) # 遇到致命错误，直接退出程序

    # --- 阶段 1: 初始化 ---
    # 初始化 OCR 引擎
    ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
    
    # 启动浏览器
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    print("[-] 正在访问清华用户注册管理系统...")
    page.goto("https://usereg.tsinghua.edu.cn")

    # --- 阶段 2: 预填登录信息 ---
    # 填写固定的账号密码
    page.get_by_role("textbox", name="用户名").fill(USERNAME)
    page.get_by_role("textbox", name="密码").fill(PASSWORD)

    login_success = False

    # --- 阶段 3: 验证码识别与登录循环 ---
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n[-] [尝试 {attempt}/{MAX_RETRIES}] 正在进行登录...")

        # 3.1 定位验证码组件
        print("[-] 正在识别验证码...")
        captcha_image = page.locator("#loginform-verifycode-image")

        # 等待元素加载完成，防止网络延迟导致截图为空
        captcha_image.wait_for()

        # 3.2 截图并调用 OCR
        img_bytes = captcha_image.screenshot()
        code = ocr.classification(img_bytes)
        print(f"[+] OCR 识别结果: {code}")

        # 3.3 结果校验
        # 如果识别结果为空或长度不足4位，直接判定为失败，刷新重试
        if not code or len(code) < 4:
            print("[!] 识别结果异常 (长度不足)，自动刷新验证码...")
            captcha_image.click() # 点击图片通常会触发刷新
            time.sleep(1)         # 等待新图片加载
            continue

        # 3.4 填入验证码并提交
        page.get_by_role("textbox", name="验证码").fill(code)
        
        # 使用正则匹配按钮文本，防止图标干扰
        page.get_by_role("button", name=re.compile("登录")).click()

        # 3.5 验证登录结果
        try:
            # 检测页面是否跳转成功：查找“准入代认证”链接
            # 设置 2000ms 超时，如果2秒内没刷出来，抛出异常进入 except 分支
            success_link = page.get_by_role("link", name=re.compile("准入代认证"))
            success_link.wait_for(state="visible", timeout=2000)

            print("[+] 登录成功！")
            login_success = True
            break # 成功则跳出重试循环

        except:
            # 超时未找到链接，说明登录失败 (通常是验证码错误)
            print("[!] 登录验证失败，准备重试...")
            captcha_image.click() # 刷新验证码
            time.sleep(1)         # 冷却时间

    # --- 阶段 4: 异常处理 ---
    if not login_success:
        print("[X] 错误：已达到最大重试次数，登录失败。")
        context.close()
        browser.close()
        return

    # --- 阶段 5: 业务操作 (准入代认证) ---
    print("[-] 进入准入代认证页面...")
    page.get_by_role("link", name=re.compile("准入代认证")).click()

    print("[-] 正在填写认证表单...")
    # 填入之前获取的本机 IPv6 地址
    page.get_by_role("textbox", name="哑终端IP地址").fill(IPV6_ADDRESS)
    page.get_by_role("textbox", name="密码").fill(PASSWORD)

    # 根据需求选择校外/校内
    page.get_by_role("radio", name="校外").check()

    print("[-] 提交最终认证请求...")
    page.get_by_role("button", name=re.compile("登录")).click()

    print("[+] 操作完成！")
    time.sleep(1) # 稍作停留以便观察结果

    # --- 阶段 6: 清理资源 ---
    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

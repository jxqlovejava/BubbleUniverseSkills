#!/usr/bin/env python3
"""主题参数化自动录屏：零依赖驱动模拟器走完 TarotBubble 占卜全流程并合成成片。

原理（无第三方工具）：simctl screenshot + macOS Vision OCR 定位文字坐标 →
换算到 macOS 屏幕坐标 → JXA/CGEvent 真实点击；中文输入走 simctl 写设备剪贴板 +
点编辑菜单「粘贴」（模拟器收不到 CGEvent 键盘的 Unicode 载荷，直输只会打出一串 a）。
OCR 只花在「等页面出现」上（页面就绪时机不可预测，省不掉）；定位点击走
wait_any 已定位的框 / 校准文件盲点，不重扫。

用法：python3 auto_record.py "他对我是不是真心的" [--copy sahuang] [--no-compose]
前置：
  1. 模拟器已装塔罗气泡（com.yunshi.qihang）且已手动登录过一次（token 持久化）
  2. 账号有剩余解读次数
  3. 终端 App 已授权「辅助功能」（CGEvent 点击需要，未授权点击会静默无效）
  4. 运行期间不要动鼠标（CGEvent 是真机屏幕点击）、Simulator 保持前台
  5. Simulator「Show Device Bezels」保持关闭（默认）
  6. 模拟器「连接硬件键盘」会自动打开（脚本 preflight 里 ⌘⇧K）——点输入框不弹软键盘，
     成片干净；关着的话输入框点不出编辑菜单
  7. 首次粘贴会弹「允许粘贴」，脚本会自动点；想永久免弹：
     模拟器 设置 → 塔罗气泡 → 从其他 App 粘贴 → 允许

输出：raw/<时间戳>-<主题>.mov + out/<同名>-<copy>.mp4 + out/<同名>.txt
失败：out/_fail-<时间戳>.png 截图 + raw/ 保留现场录屏。
自检：python3 auto_record.py --selftest
"""
import argparse
import json
import os
import pathlib
import random
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

BASE = pathlib.Path(__file__).parent
BUNDLE = "com.yunshi.qihang"
HINT_TEXT = "请输入你关心的问题吧"
SUBSCRIPTION_HINTS = ["立即开通", "开通会员", "解锁全部"]
CLOSE_CANDIDATES = ["以后再说", "暂不", "关闭", "取消", "×"]
BANNED_WORDS = ("塔罗", "占卜", "算命", "卜卦")  # 平台高敏词：文案里不出现
# 解读落地后的阅读节奏总时长 ≈7.7s（1.5 看首屏 + 3.5 慢滑半屏 + 2.5 定格），
# 成片尾部常速段从视频尾部取（见 gen_video --tail-hold，VFR 补帧后可见约 3s）。
# 正文占位的「正在为你解读塔罗牌…」只在加载期出现，正文渲染出来它就没了 = 解读落地。
# 别加输入框那条「塔罗牌解读进行中…」：它是输入框 hint，正文出来十几秒后才变，会把整段正文拖进加速段。
LOADING_HINTS = ["正在为你解读塔罗牌"]
TAIL_HOLD = 7.5  # 成片尾部保持常速的秒数（这段才能看清解读）。给到 7.5 而不是 3 是因为
                 # 变帧率裁段实际产出的秒数只有名义值的一半左右（实测 6.0 名义 → 3.0s 可见），
                 # 留足余量才稳过用户要求的「看满 3 秒」
OCR_BIN = pathlib.Path.home() / ".cache/tarot-ocr/ocr_boxes"
PERM_BIN = pathlib.Path.home() / ".cache/tarot-ocr/perm_check"
DEVICE = "booted"  # preflight 解析为装了 App 的那台 booted 设备 UDID（可能多台同时 booted）
DEVICE_NAME = ""   # 用于在多窗口中按标题匹配目标设备窗口


def compile_swift(src: pathlib.Path, bin_path: pathlib.Path) -> None:
    """swift 源码新于二进制才重编译（同 ocr_text.sh 的缓存惯例）。"""
    if not bin_path.exists() or src.stat().st_mtime > bin_path.stat().st_mtime:
        bin_path.parent.mkdir(parents=True, exist_ok=True)
        sh(["swiftc", str(src), "-o", str(bin_path)], timeout=180)


def check_permissions(prompt: bool = True) -> None:
    """自动录屏需要辅助功能（CGEvent 点击 + System Events 读窗口位置）。"""
    compile_swift(BASE / "scripts/perm_check.swift", PERM_BIN)
    cmd = [str(PERM_BIN)] + (["--prompt"] if prompt else [])
    out = sh(cmd).stdout
    if "accessibility=true" not in out:
        sys.exit(
            "[err] 缺「辅助功能」权限\n"
            "  已弹系统授权框；或手动到 系统设置 → 隐私与安全性 → "
            "辅助功能 里给当前终端 App 打勾，然后重跑"
        )
CALIBRATION = BASE / "out" / ".calibration.json"
# 扇形中牌候选探测点（设备截图像素比例），首个命中「确定」弹窗的会固化进校准文件
CARD_PROBES = [(0.50, 0.72), (0.55, 0.72), (0.45, 0.72), (0.60, 0.70),
               (0.40, 0.70), (0.50, 0.78), (0.55, 0.78), (0.45, 0.78)]


def sh(cmd: list[str], timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)


def find_page_start(video: pathlib.Path, marker: str, guess: float,
                    before: float = 25.0, after: float = 5.0, fps: float = 1.0) -> float | None:
    """定位录屏里首次出现 marker 的**视频 PTS 秒**（找不到返回 None）。

    为什么必须这样找：`simctl recordVideo` 的片关键帧稀疏（约 15s），`-ss T -i` 输入搜寻
    会落在 T 之前的关键帧、**返回十几秒前的内容**（本项目 .learnings/ 里已记过这个坑；
    一度因此把洗牌页整段切掉、成片直接从抽牌开始）。这里改成「整片解码 + fps 取样」，
    每个取样点与 PTS 严格对应，慢一点但不会骗人。命中精度 = 1/fps。
    """
    lo = max(0.0, guess - before)
    hi = guess + after
    tmp = BASE / "out" / ".probe"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video),
                    "-vf", f"trim=start={lo:.2f}:end={hi:.2f},setpts=PTS-STARTPTS,fps={fps}",
                    "-y", str(tmp / "%04d.png")], check=False)
    try:
        for i, png in enumerate(sorted(tmp.glob("*.png"))):
            r = sh([str(OCR_BIN), str(png)], timeout=60, check=False)
            texts = [json.loads(x)["text"] for x in r.stdout.splitlines() if x.startswith("{")]
            if any(marker in s for s in texts):
                return lo + i / fps
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return None


def slugify(topic: str) -> str:
    s = re.sub(r"[^\w一-鿿]+", "", topic)
    return s[:12] or "未命名"


def material_dirname(topic: str) -> str:
    """素材目录名 = 问题原文（去掉首尾空白/句末标点/路径分隔符）。
    直接用问题名是为了目录一眼能对上文案标题；不安全字符才退回 slugify。"""
    s = re.sub(r'[/\\:*?"<>|]+', "", topic).strip().strip("？?。.！! ")
    return s[:40] or slugify(topic)


class SimDriver:
    """截屏+OCR 定位 → CGEvent 点击。"""

    def __init__(self) -> None:
        self.win = self._winbounds()
        self._tmp = BASE / "out" / "_scan.png"
        self.dims: tuple[int, int] | None = None  # 最近一次 scan 的设备分辨率（盲点复用，免扫描）
        self.last_boxes: list[dict] = []  # 最近一次 scan 的 OCR 结果（同页找按钮免重扫）
        self._last_raise = 0.0  # 上次抬窗时间（click_device 节流用）

    # ── 基础能力 ──────────────────────────────────────────────
    def _winbounds(self) -> dict:
        """读 Simulator 窗口里「设备屏幕内容区」的屏幕坐标矩形（新版 Simulator 带
        设备边框工具栏，窗口矩形≠内容矩形；内容区是 window 下 size=逻辑分辨率的 group）。
        多台设备同时 booted 时按窗口标题（设备名）匹配目标窗口。
        走辅助功能权限，不需要屏幕录制。"""
        name_filter = (f'if (name of w) contains "{DEVICE_NAME}" then\n' if DEVICE_NAME
                       else "")
        end_if = "end if\n" if DEVICE_NAME else ""
        script = (
            'tell application "System Events" to tell process "Simulator"\n'
            " repeat with w in windows\n"
            f"  {name_filter}"
            "  repeat with e in UI elements of w\n"
            "   try\n"
            '    if (role description of e) is "group" then\n'
            "     set p to position of e\n"
            "     set s to size of e\n"
            '     return ((item 1 of p) as text) & "," & ((item 2 of p) as text) & "," & ((item 1 of s) as text) & "," & ((item 2 of s) as text)\n'
            "    end if\n"
            "   end try\n"
            "  end repeat\n"
            f"  {end_if}"
            " end repeat\n"
            "end tell"
        )
        r = sh(["osascript", "-e", script], check=False)
        nums = [float(x) for x in re.findall(r"-?[\d.]+", r.stdout)]
        if r.returncode != 0 or len(nums) != 4:
            sys.exit(f"[err] 读不到 Simulator（{DEVICE_NAME or 'booted'}）屏幕内容区位置，请确认模拟器窗口已打开")
        return {"x": nums[0], "y": nums[1], "w": nums[2], "h": nums[3]}

    def fit_window(self) -> None:
        """目标设备窗口提前 → Window → Fit Screen 缩放（Dock 不隐藏时，点精确缩放的
        窗口底部悬在 Dock 下方，输入框区域点不到），再移到左上角，重读内容区矩形。"""
        if DEVICE_NAME:
            sh(["osascript", "-e",
                'tell application "System Events" to tell process "Simulator" '
                f'to perform action "AXRaise" of (first window whose name contains "{DEVICE_NAME}")'],
               check=False)
            time.sleep(0.5)
        script = (
            'tell application "System Events" to tell process "Simulator"\n'
            ' click menu item "Fit Screen" of menu 1 of menu bar item "Window" of menu bar 1\n'
            "end tell"
        )
        sh(["osascript", "-e", script], check=False)
        time.sleep(1)
        win_clause = (f'(first window whose name contains "{DEVICE_NAME}")' if DEVICE_NAME
                      else "window 1")
        sh(["osascript", "-e",
            'tell application "System Events" to tell process "Simulator" '
            f"to set position of {win_clause} to {{60, 25}}"], check=False)
        time.sleep(1)
        self.win = self._winbounds()

    def activate(self) -> None:
        sh(["osascript", "-e", 'tell application "Simulator" to activate'], check=False)

    def raise_window(self) -> None:
        """把目标设备窗口抬到最前。别的 App（Chrome 等）一旦被抬起来盖住模拟器，
        CGEvent 点击会全部落进它的窗口（simctl 截图读设备 framebuffer 不受影响，
        极具迷惑性）——2026-09-14 批量录屏「主题没上屏」就是这么挂的。"""
        self.activate()
        if DEVICE_NAME:
            sh(["osascript", "-e",
                'tell application "System Events" to tell process "Simulator" '
                f'to perform action "AXRaise" of (first window whose name contains "{DEVICE_NAME}")'],
               check=False)
        self._last_raise = time.time()

    def _ensure_ocr(self) -> None:
        compile_swift(BASE / "scripts/ocr_boxes.swift", OCR_BIN)

    def scan(self) -> tuple[list[dict], int, int]:
        """截屏 + OCR，返回 (boxes, 宽px, 高px)。设备分辨率恒定，只量一次。"""
        self._ensure_ocr()
        self._tmp.parent.mkdir(exist_ok=True)
        sh(["xcrun", "simctl", "io", DEVICE, "screenshot", str(self._tmp)], timeout=45)
        if not self.dims:
            dims = sh(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(self._tmp)]).stdout
            w = int(re.search(r"pixelWidth: (\d+)", dims).group(1))
            h = int(re.search(r"pixelHeight: (\d+)", dims).group(1))
            self.dims = (w, h)
        w, h = self.dims
        r = sh([str(OCR_BIN), str(self._tmp)], timeout=60, check=False)
        boxes = [json.loads(line) for line in r.stdout.splitlines() if line.startswith("{")]
        self.last_boxes = boxes
        return boxes, w, h

    @staticmethod
    def find(text: str, boxes: list[dict]) -> dict | None:
        """精确匹配优先，兜底子串里文本最短的（防「准备开始占卜了吗？」盖住按钮「开始占卜」）。"""
        for b in boxes:
            if b["text"].strip() == text:
                return b
        hits = [b for b in boxes if text in b["text"]]
        return min(hits, key=lambda b: len(b["text"])) if hits else None

    def device_to_screen(self, px: float, py: float, shot_w: int, shot_h: int) -> tuple[float, float]:
        """设备截图像素坐标 → macOS 屏幕坐标（self.win 已是设备屏幕内容区矩形）。"""
        scale = self.win["w"] / shot_w  # 屏幕 px / 设备 px
        return self.win["x"] + px * scale, self.win["y"] + py * scale

    def click_screen(self, x: float, y: float) -> None:
        sh(["osascript", "-l", "JavaScript", str(BASE / "scripts/pointer.jxa"),
            "click", str(x), str(y)])

    def click_device(self, px: float, py: float, shot_w: int, shot_h: int) -> None:
        # 每次点击前（节流 8s）确保模拟器窗口在最前，否则点击会落进盖住它的 App
        if time.time() - self._last_raise > 8:
            self.raise_window()
            time.sleep(0.3)
        x, y = self.device_to_screen(px, py, shot_w, shot_h)
        self.click_screen(x, y)

    # ── 语义操作 ──────────────────────────────────────────────
    def _handle_popups(self, boxes: list[dict], w: int, h: int) -> None:
        """已知拦截弹窗：好评弹窗点取消；订阅页尝试关闭，关不掉报次数不足。"""
        # 粘贴隐私弹窗（首次写设备剪贴板后粘贴会弹）：留着会挡住后面所有页面
        allow = self.find("允许粘贴", boxes)
        if allow:
            self.click_device(allow["x"] + allow["w"] / 2, allow["y"] + allow["h"] / 2, w, h)
            time.sleep(1)
            return
        if self.find("喜欢塔罗气泡吗", boxes) or self.find("顺手点个好评", boxes):
            cancel = self.find("取消", boxes)
            if cancel:
                self.click_device(cancel["x"] + cancel["w"] / 2, cancel["y"] + cancel["h"] / 2, w, h)
                time.sleep(1)
            return
        if not any(self.find(t, boxes) for t in SUBSCRIPTION_HINTS):
            return
        for c in CLOSE_CANDIDATES:
            hit = self.find(c, boxes)
            if hit:
                self.click_device(hit["x"] + hit["w"] / 2, hit["y"] + hit["h"] / 2, w, h)
                time.sleep(1)
                return
        raise RuntimeError("命中订阅页且找不到关闭按钮（账号解读次数可能不足）")

    def wait_text(self, text: str, timeout: float = 30) -> tuple[dict, int, int] | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            boxes, w, h = self.scan()
            self._handle_popups(boxes, w, h)
            hit = self.find(text, boxes)
            if hit:
                return hit, w, h
            time.sleep(0.8)
        return None

    def wait_any(self, texts: list[str], timeout: float = 30):
        """等任一文本出现，返回 (text, box, w, h)；超时返回 None。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            boxes, w, h = self.scan()
            self._handle_popups(boxes, w, h)
            for t in texts:
                hit = self.find(t, boxes)
                if hit:
                    return t, hit, w, h
            time.sleep(0.4)
        return None

    def tap_text(self, text: str, timeout: float = 30) -> bool:
        got = self.wait_text(text, timeout)
        if not got:
            return False
        b, w, h = got
        self.click_device(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, w, h)
        return True

    def read_input_row(self) -> str:
        """读输入框里的文字。输入框字体小，整页 1x OCR 读不出来 → 裁底部条带放大 3x 再 OCR。
        用来核验「主题真的上屏了」——不核验的话，点歪到建议问题上也照样能把片子跑完。"""
        try:
            from PIL import Image
        except ImportError:
            return ""
        shot = BASE / "out" / "_scan.png"
        sh(["xcrun", "simctl", "io", DEVICE, "screenshot", str(shot)], timeout=45)
        im = Image.open(shot)
        w, h = im.size
        crop = im.crop((0, int(h * 0.86), w, int(h * 0.97))).resize((w * 3, int(h * 0.11) * 3))
        row = BASE / "out" / ".inputrow.png"
        crop.save(row)
        r = sh([str(OCR_BIN), str(row)], timeout=60, check=False)
        return "".join(json.loads(l)["text"] for l in r.stdout.splitlines() if l.startswith("{"))

    def input_topic(self, anchor: dict, w: int, h: int, topic: str) -> tuple[float, float] | None:
        """主题上屏，返回发送按钮坐标。只能走剪贴板：写设备剪贴板 → 点输入框聚焦
        → 点编辑菜单「粘贴」（首次会弹「允许粘贴」隐私弹窗，一并点掉）。
        模拟器会丢掉 CGEvent 键盘事件里的 Unicode 载荷、只按 keycode 走，
        所以中文直输不论 JXA 还是 Swift 都会整段变成 a（实测过，别再试）。
        每次循环用发送按钮是否点亮当上屏反馈（有字按钮才由灰转紫）。"""
        subprocess.run(["xcrun", "simctl", "pbcopy", DEVICE], input=topic.encode(), check=False)
        cx = anchor["x"] + anchor["w"] / 2
        cy = anchor["y"] + anchor["h"] / 2
        for _ in range(6):
            self.click_device(cx, cy, w, h)  # 聚焦并叫出编辑菜单
            time.sleep(1.3)
            boxes, w2, h2 = self.scan()
            for label in ("允许粘贴", "粘贴"):
                hit = self.find(label, boxes)
                if hit:
                    self.click_device(hit["x"] + hit["w"] / 2, hit["y"] + hit["h"] / 2, w2, h2)
                    time.sleep(1.2)
                    break
            send = self.find_send_button()
            if send and topic[:6] in self.read_input_row():
                return send
            if send:
                print(f"[warn] 输入框里不是主题（读到: {self.read_input_row()[:24]}…），重试")
        return None

    def find_send_button(self, any_state: bool = False) -> tuple[float, float] | None:
        """定位发送按钮（无字紫色圆钮 40pt）。键盘/焦点会让输入行整体漂移，
        固定比例会落空（实测偏移 155px），按颜色找圆心最稳。
        返回设备截图像素坐标；缺 Pillow 或找不到时返回 None（调用方回退）。"""
        try:
            from PIL import Image
        except ImportError:
            return None
        shot = BASE / "out" / ".scan.png"
        sh(["xcrun", "simctl", "io", DEVICE, "screenshot", str(shot)], timeout=45)
        im = Image.open(shot).convert("RGB")
        w, h = im.size
        px = im.load()
        # 按钮是 #7E42F2 半透明叠白：有字时约 (190,162,247)，无字（灰态）约 (229,217,252)。
        # any_state=True 连灰态一起认——灰态只用来定位「输入行在第几行」，别拿它当上屏判据。
        xs: list[int] = []
        ys: list[int] = []
        for y in range(int(h * 0.8), h, 3):        # 只在底部区域扫，避免紫底插画误命中
            for x in range(int(w * 0.7), w, 3):
                r, g, b = px[x, y]
                lit = b > 200 and b - g > 50 and r - g > 15 and b > r > g
                dim = any_state and abs(r - 229) < 14 and abs(g - 217) < 14 and abs(b - 252) < 12
                if lit or dim:
                    xs.append(x)
                    ys.append(y)
        if len(xs) < 40:
            return None
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        if not (60 <= max(xs) - min(xs) <= 200 and 60 <= max(ys) - min(ys) <= 200):
            return None                            # 尺寸不像 40pt 圆钮，宁可回退
        return cx, cy

    def focus_click(self) -> None:
        """先点一下状态栏区域（无控件、点了没副作用）。
        macOS 会吞掉「非 key 窗口」的第一次点击（那一下只用来激活窗口），
        不预热的话流程里的第一次真点击会静默落空——冷启动/切过 App 时必踩。"""
        if not self.dims:
            self.scan()
        w, h = self.dims
        self.click_device(w * 0.5, h * 0.02, w, h)

    def swipe_fan(self) -> None:
        """扇形牌堆随机左/右滑一小段。抽过的位置会留缺口，同点再抽必空，
        每抽一张后滑一下把新牌送到触点区域。"""
        if not self.dims:
            self.scan()
        w, h = self.dims
        direction = random.choice([-1, 1])
        x1, y1 = self.device_to_screen(w * 0.5, h * 0.75, w, h)
        x2, y2 = self.device_to_screen(w * (0.5 + 0.2 * direction), h * 0.75, w, h)
        sh(["osascript", "-l", "JavaScript", str(BASE / "scripts/pointer.jxa"),
            "drag", str(x1), str(y1), str(x2), str(y2)], timeout=30)

    def scroll_read(self) -> None:
        """解读页拟人阅读：从屏幕 70% 处缓慢上滑到 20% 处（= 半屏），边滑边读。

        70 步 × 50ms ≈ 3.5s 匀速，≈110pt/s（人手慢滑速度，别更快）；
        到位后停 350ms 才抬手 —— 释放前速度归零，iOS 不加惯性甩动，滚动距离
        就等于手指位移（半屏）。2026-09-16 实测：70 步 × 20ms（≈280pt/s）不停顿
        抬手，被判定为甩动，一次从第 1 节冲到页尾 CTA，滑到底。"""
        if not self.dims:
            self.scan()
        w, h = self.dims
        x1, y1 = self.device_to_screen(w * 0.5, h * 0.70, w, h)
        x2, y2 = self.device_to_screen(w * 0.5, h * 0.20, w, h)
        sh(["osascript", "-l", "JavaScript", str(BASE / "scripts/pointer.jxa"),
            "drag", str(x1), str(y1), str(x2), str(y2), "70", "50", "350"], timeout=30)


class Recorder:
    def start(self, path: pathlib.Path) -> None:
        self.t0 = time.time()
        self.proc = subprocess.Popen(
            ["xcrun", "simctl", "io", DEVICE, "recordVideo", "--codec=h264", str(path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # recordVideo 启动失败（典型：残留录制占用设备，SimRender 僵尸）不会报出来，
        # 文件一直不出现，流程白跑几分钟到合成才发现。8s 内文件没出现直接判死（2026-09-14 踩过）。
        # 残留处置：lsof raw/ 下在涨的文件 → kill -INT 其 SimRender 进程（别 kill 客户端，没用）
        # 判活标准 2026-09-16 修：h264 静态画面帧全内存缓冲，文件创建后 0 字节可持续 17s+，
        # 停止时才落盘——旧的「size>0 才算活」会把健康录制误杀（SIGKILL 客户端反留 SimRender
        # 僵尸，后续全部 Resource busy 连环失败，当天 10 组批量全灭于此）。改成：
        # 文件出现 + 进程活着 = 健康；进程退出 = 启动失败（残留占用会立即报错退出）。
        deadline = time.time() + 8
        while time.time() < deadline:
            if path.exists() and self.proc.poll() is None:
                return
            if self.proc.poll() is not None:
                break
            time.sleep(0.5)
        self.proc.kill()  # 别让判死的客户端再留一个 SimRender 僵尸
        raise RuntimeError(f"recordVideo 未产出文件（残留录制占用？先查 SimRender 僵尸）: {path}")

    def elapsed(self) -> float:
        return time.time() - self.t0

    def stop(self) -> None:
        self.proc.send_signal(signal.SIGINT)
        self.proc.wait(timeout=15)


def resolve_device() -> tuple[str, str, str]:
    """在 booted 设备里找装了 App 的那台，返回 (UDID, data 容器路径, 设备名)。"""
    devs = json.loads(sh(["xcrun", "simctl", "list", "devices", "-j"]).stdout)["devices"]
    for lst in devs.values():
        for d in lst:
            if d.get("state") != "Booted":
                continue
            r = sh(["xcrun", "simctl", "get_app_container", d["udid"], BUNDLE, "data"],
                   check=False)
            if r.returncode == 0:
                return d["udid"], r.stdout.strip(), d.get("name", "")
    sys.exit(f"[err] 没有已 boot 且安装 {BUNDLE} 的模拟器，先 boot 设备并 flutter run 装一次")


def ensure_hardware_keyboard() -> None:
    """模拟器「连接硬件键盘」必须开，否则 CGEvent 键盘事件收不到（输入直接无声失败）。
    该项按设备 UDID 存在 com.apple.iphonesimulator 里，默认可能是关的：
    用 Simulator 菜单快捷键 ⌘⇧K（I/O → Keyboard → Connect Hardware Keyboard）打开。
    副作用正好是我们想要的：点输入框不弹软件键盘，成片干净。"""
    pl = pathlib.Path.home() / "Library/Preferences/com.apple.iphonesimulator.plist"
    query = ["plutil", "-extract", f"DevicePreferences.{DEVICE}.ConnectHardwareKeyboard",
             "raw", "-o", "-", str(pl)]

    def enabled() -> bool:
        return sh(query, check=False).stdout.strip().lower() in ("1", "true")

    if enabled():
        return
    sh(["osascript", "-e", 'tell application "Simulator" to activate',
        "-e", "delay 0.8",
        "-e", 'tell application "System Events" to keystroke "k" '
              "using {command down, shift down}"], check=False)
    time.sleep(1)
    if not enabled():
        sys.exit("[err] 打不开模拟器「连接硬件键盘」："
                 "Simulator 菜单 I/O → Keyboard → Connect Hardware Keyboard（⌘⇧K）手动开一次")


def preflight() -> None:
    global DEVICE, DEVICE_NAME
    check_permissions(prompt=True)
    DEVICE, container, DEVICE_NAME = resolve_device()
    ensure_hardware_keyboard()
    # 清空设备剪贴板：残留内容会让输入框弹出「粘贴」编辑菜单，吞掉发送点击
    subprocess.run(["xcrun", "simctl", "pbcopy", DEVICE], input=b"", check=False)
    plist = pathlib.Path(container) / "Library/Preferences" / f"{BUNDLE}.plist"
    p = sh(["/usr/bin/plutil", "-p", str(plist)], check=False)
    if '"flutter.loginToken"' not in p.stdout:
        sys.exit("[err] 未登录。先在模拟器里手动登录一次（短信验证码），登录态会持久化")


def tap_card(d: SimDriver, shuffle_fan: bool = False) -> None:
    """点扇形中牌并确认。校准文件带确定按钮坐标时走盲点（零 OCR，牌间间隔最短）；
    否则探测候选点，命中即把牌点+确定按钮坐标一起固化。
    shuffle_fan=True 先随机左右滑一下扇形——抽过的位置留缺口，同点再抽必空。"""
    if shuffle_fan:
        d.swipe_fan()
        time.sleep(0.3)  # 扇形滑动归位
    cal = json.loads(CALIBRATION.read_text()) if CALIBRATION.exists() else {}
    if cal.get("cfx") and d.dims:
        w, h = d.dims
        d.click_device(w * cal["fx"], h * cal["fy"], w, h)
        time.sleep(0.5)  # 确定弹窗动画
        d.click_device(w * cal["cfx"], h * cal["cfy"], w, h)
        return
    probes = list(CARD_PROBES)
    if cal:
        probes.insert(0, (cal["fx"], cal["fy"]))
    boxes, w, h = d.scan()
    for fx, fy in probes:
        d.click_device(w * fx, h * fy, w, h)
        time.sleep(0.6)  # 等确定弹窗完全弹出（0.4s 时弹窗动画未完，OCR 会漏认）
        boxes, w2, h2 = d.scan()
        confirm = d.find("确定", boxes)
        if confirm:
            CALIBRATION.write_text(json.dumps({
                "fx": fx, "fy": fy,
                "cfx": (confirm["x"] + confirm["w"] / 2) / w2,
                "cfy": (confirm["y"] + confirm["h"] / 2) / h2,
            }))
            # 确认点击可能被动画窗口吞掉：点后验证，确定还在就补点
            for _ in range(2):
                d.click_device(confirm["x"] + confirm["w"] / 2, confirm["y"] + confirm["h"] / 2, w2, h2)
                time.sleep(0.3)
                boxes, w2, h2 = d.scan()
                confirm = d.find("确定", boxes)
                if not confirm:
                    return
            return  # 补点仍没消也不堵流程，抽牌循环的「确定」分支会兜底
    raise RuntimeError("扇形探测点全部未命中（页面布局可能变了，需重新校准）")


def run_flow(d: SimDriver, topic: str, rec: "Recorder | None" = None) -> dict:
    """返回 markers：shuffle_t = 洗牌页首次出现的录屏秒数（成片从这里起剪）。"""
    marks: dict = {}
    sh(["xcrun", "simctl", "terminate", DEVICE, BUNDLE], check=False)
    time.sleep(1)
    sh(["xcrun", "simctl", "launch", DEVICE, BUNDLE])
    time.sleep(5)
    d.activate()  # terminate/launch 后重新把 Simulator 拉回前台，否则点击落空
    time.sleep(1)
    d.focus_click()  # 再补一次预热点击：首次点击会被吞

    step = "首页-开始占卜"
    # 冷启动落点不固定（2026-09-14 三种都见过）：直进提问页 / 首页停留 / 首页短暂显示后自动跳走。
    # 唯一目标状态 = 提问页：首页在就点按钮，按钮消失或提问页标记出现都算过关；splash/过渡页继续等。
    deadline = time.time() + 90
    while True:
        boxes, w0, h0 = d.scan()
        d._handle_popups(boxes, w0, h0)
        if any(d.find(t, boxes) for t in (HINT_TEXT, "想问什么", "放松心情")):
            break
        btn = d.find("开始占卜", boxes)
        if btn:
            d.click_device(btn["x"] + btn["w"] / 2, btn["y"] + btn["h"] / 2, w0, h0)
            time.sleep(2.5)
        else:
            time.sleep(2)
        assert time.time() < deadline, f"{step}: 90s 内未进入提问页（检查辅助功能授权/登录态）"

    step = "提问页-输入主题"
    # 输入框占位语是灰色小字，1x OCR 偶发读不到（冷启动首屏最明显）；
    # 用页面标题一起判定「已进提问页」，输入框位置再用固定比例兜底
    got = d.wait_any([HINT_TEXT, "想问什么", "放松心情"], 40)
    assert got, f"{step}: 未进入提问页"
    boxes, w, h = d.scan()
    # 锚点优先级：① 输入框占位语（最准）② 发送按钮同一行往左（一定落在输入框内）。
    # 别再用「页面固定比例」兜底：提问页的建议问题列表长度随题目变，点低了会点到某条建议问题上——
    # 主题没进输入框，但发送按钮照样亮，一路跑到底产出一条内容对不上的片子（2026-09-13 踩过）。
    hint = d.find(HINT_TEXT, boxes)
    if not hint:
        send_pos = d.find_send_button(any_state=True)
        assert send_pos, f"{step}: 定位不到输入框（既没占位语也没发送按钮）"
        px, py = send_pos[0] - w * 0.40, send_pos[1]
        hint = {"x": px - 10, "y": py - 10, "w": 20, "h": 20}
    # 发送按钮是无字紫色圆钮：按颜色定位（顺带当「主题已上屏」的反馈信号）
    send = d.input_topic(hint, w, h, topic)
    assert send, f"{step}: 主题没上屏（发送按钮始终未点亮）"
    d.click_device(send[0], send[1], w, h)

    step = "牌阵页-开始抽牌"
    assert d.tap_text("开始抽牌", 50), f"{step}: 双 loading 超时"

    step = "洗牌页-结束洗牌"
    # 同时盯洗牌按钮和抽牌页：个别牌阵流程会跳过洗牌直接进抽牌
    got = d.wait_any(["结束洗牌", "想象你的问题"], 60)
    assert got, f"{step}: 未找到按钮"
    if rec:
        marks["shuffle_t"] = rec.elapsed()  # 成片起剪点（洗牌页或抽牌页首次出现）
    cards_done = 0
    if got[0] == "结束洗牌":
        time.sleep(1.0)  # 洗牌动画露个脸即可（成片 2.5x 后 ≈0.4s）
        # 点一次就等页态，绝不连点：过渡期重复点击会落进抽牌页扇形误触卡牌弹详情。
        # 「确定」出现 = 已误触卡牌详情，顺势确认，这就是第一张牌
        for _ in range(4):
            d.tap_text("结束洗牌", 6)  # 已离开洗牌页则找不到，直接过
            got2 = d.wait_any(["想象你的问题", "确定"], 20)
            assert got2, f"{step}: 未进抽牌页（getRandomCards 可能失败）"
            if got2[0] == "确定":
                _, cb, cw, ch = got2
                d.click_device(cb["x"] + cb["w"] / 2, cb["y"] + cb["h"] / 2, cw, ch)
                cards_done = 1
                time.sleep(0.3)  # 牌飞入槽位动画
            break

    step = "抽牌页-循环抽牌"
    if rec:
        marks["draw_t0"] = rec.elapsed()
    # cards_done=1 时从第二张开始（首张已在洗牌过渡中确认）；i>0 才等扇形复位。
    # 上限给到 14（牌位数 10）：盲点偶发落空不会真抽到牌，多出的几轮会自动补抽，
    # 抽满了页面自然跳结果页 break，不会重复抽。
    for i in range(cards_done, 14):
        # 首张牌跳过等待：结束洗牌循环的最后一次扫描已确认进入抽牌态
        if i > 0:
            # 抽满最后一张会自动跳结果页，等待必须同时盯两个页面（竞态）；
            # 「确定」= 上次确认点击被动画吞了，补点后再等
            got = d.wait_any(["这是你抽到的牌", "想象你的问题", "确定"], 25)
            assert got, f"{step}: 未进入抽牌态"
            if got[0] == "确定":
                _, cb, cw, ch = got
                d.click_device(cb["x"] + cb["w"] / 2, cb["y"] + cb["h"] / 2, cw, ch)
                time.sleep(0.3)
                got = d.wait_any(["这是你抽到的牌", "想象你的问题"], 25)
                assert got, f"{step}: 补点确定后仍未回抽牌态"
            if got[0] == "这是你抽到的牌":
                break
            time.sleep(0.1)  # 扇形复位动画
        tap_card(d, shuffle_fan=(i >= 1))
        time.sleep(0.25)  # 牌飞入槽位动画
    else:
        raise RuntimeError(f"{step}: 连续 14 轮仍未到结果页，异常")
    if rec:
        marks["draw_t1"] = rec.elapsed()

    step = "结果页-查看解读"
    assert d.tap_text("查看解读", 18), f"{step}: 未找到按钮"
    time.sleep(2)  # getApiLimits + 能量聚集 loading
    step = "解读页-等正文出现"
    # 正文页标记：主题标题（服务端可能改写问题，改写后原主题就找不到了）+ 流式 loading 占位
    got = d.wait_any([topic[:4], *LOADING_HINTS], 90)
    assert got, f"{step}: 超时（流式接口可能异常）"
    if rec:
        marks["loading_t0"] = rec.elapsed()
    # 标题在 loading 页就有，正文这还没写：等「正在为你解读塔罗牌」占位消失 = 解读落地。
    # （流式期间正文区只有占位框，interpretationCompleted 之后才整体渲染 markdown）
    step = "解读页-等解读落地"
    deadline = time.time() + 150
    while time.time() < deadline:
        boxes, _, _ = d.scan()
        if not any(d.find(t, boxes) for t in LOADING_HINTS):
            break
        time.sleep(1.0)
    else:
        raise RuntimeError(f"{step}: 150s 内解读没落地（接口慢或次数用尽）")
    if rec:
        marks["loading_t1"] = rec.elapsed()
    # 拟人阅读节奏（2026-09-16 真机二次校准，逐帧 OCR 实证）：
    # 解读落地时页面本来就停在正文【顶部】——页眉 + 牌面卡 + 正文第一段都在屏内，
    # 第 1 节标题还在屏底（y≈2580）。所以不需要任何「回顶」动作：上一版那次回顶是
    # 多余的，反把正文冲下去。直接从顶部轻轻往下滑半屏、边滑边读即可。
    time.sleep(1.5)        # 看清首屏（牌面卡 + 正文开头）
    d.scroll_read()        # 慢速轻滑半屏（约 3.5s，无惯性）
    time.sleep(2.5)        # 边滑边读 + 收尾定格
    return marks


def load_opener():
    """软植入句工具：tarot-mass-divination/scripts/opener.py（ip-pipeline / vira 两种布局都认）。

    这是全项目唯一实现（微信聊天双拼 / 解读截图 / 自然照片 / 情侣四宫格都 import 它）。
    本模板单独拷出去、同级找不到 skill 时返回 None，走下面的内联兜底，保住「零依赖」。"""
    for c in (BASE.parent / ".claude" / "skills" / "tarot-mass-divination" / "scripts",
              BASE.parent / "tarot-mass-divination" / "scripts"):
        if (c / "opener.py").exists():
            sys.path.insert(0, str(c))
            import opener
            return opener
    return None


OPENER = load_opener()


def fallback_opener(t: str) -> str:
    """固定池兜底（无 API key 或 AI 调用失败时用）。按题目取模轮换，可复现。"""
    if OPENER:
        return OPENER.fallback_opener(t)
    pool = [
        f"关于{t}，我在塔罗气泡问了个明白。",
        f"{t}，这个问题我拿去问了塔罗气泡。",
        f"我在塔罗气泡看到了答案：{t}。",
        f"憋在心里很久的事，我在塔罗气泡问了出来：{t}。",
    ]
    return pool[sum(map(ord, t)) % len(pool)]


def gen_opener(t: str) -> str:
    """AI 按话题生成一句正文开头的软植入：第一人称、和话题强相关、不像广告。

    校验不过关（超字/禁词/丢了品牌名）或调用失败一律回退固定池，保证流水线不断。"""
    if OPENER:  # 有 skill 就用共享实现（池子/校验规则只在一处维护）
        return OPENER.gen_opener(t)
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        return fallback_opener(t)
    base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    system = (
        "你是抖音情感号写手。为塔罗气泡App写一篇笔记的开头第一句：软植入。"
        "要求：第一人称口语，像真实用户随手分享；必须和给定话题强相关、自然融进去，"
        "不要泛泛而谈；不超过30字；不要用「」引号；禁止出现 占卜/算命/卜卦；"
        "品牌名只准写 塔罗气泡；禁止硬广口吻（不要出现 下载/等你/快来/App）。"
        "只输出这一句文案，不要任何解释。"
    )
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": f"话题：{t}"}],
        "temperature": 1.0, "max_tokens": 100, "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            line = json.loads(resp.read())["choices"][0]["message"]["content"]
        line = line.strip().strip('"').strip()
        ok = (
            "塔罗气泡" in line
            and len(line) <= 40
            and "「" not in line and "」" not in line
            and not any(w in line.replace("塔罗气泡", "") for w in BANNED_WORDS)
            and not any(w in line for w in ("下载", "等你", "快来"))
        )
        if ok:
            return line
        print(f"[caption] AI 软植入校验不过（{line}），回退固定池")
    except Exception as e:
        print(f"[caption] AI 软植入失败（{e}），回退固定池")
    return fallback_opener(t)


def gen_caption(topic: str) -> str:
    """抖音发布文案：首行即标题，整段可直接拷贝。
    铁律：无「」、口语；正文开头一句 AI 软植入（按话题生成，失败回退固定池），无硬广 CTA；
    禁 塔罗/占卜/算命/卜卦（唯一豁免：品牌名「塔罗气泡」）。"""
    t = topic.rstrip("？?。.")
    return (
        f"{t}？牌面比人诚实\n"
        f"{gen_opener(t)}\n"
        "洗牌、抽牌、解读，全程真实录屏，答案自己看。\n"
        "#情感 #恋爱 #心理 #情绪价值 #关系 #成长\n"
    )


def selftest() -> None:
    """不依赖模拟器的纯逻辑自检。"""
    boxes = [
        {"text": "开始占卜", "x": 100, "y": 200, "w": 200, "h": 50},
        {"text": "请输入你关心的问题吧", "x": 50, "y": 900, "w": 400, "h": 40},
    ]
    assert SimDriver.find("开始", boxes)["y"] == 200
    assert SimDriver.find("关心", boxes)["w"] == 400
    assert SimDriver.find("不存在", boxes) is None
    d = SimDriver.__new__(SimDriver)
    d.win = {"x": 500, "y": 100, "w": 440, "h": 956}  # 内容区矩形，@1x 映射
    sx, sy = d.device_to_screen(660, 1434, 1320, 2868)  # 设备正中
    assert abs(sx - (500 + 660 / 3)) < 1 and abs(sy - (100 + 1434 / 3)) < 1
    assert slugify("他对我是不是真心的？") == "他对我是不是真心的"
    # 文案自检走离线固定池（CI/自检不依赖网络）
    saved_key = os.environ.pop("DEEPSEEK_API_KEY", None)
    saved_llm = os.environ.pop("LLM_API_KEY", None)
    try:
        cap = gen_caption("他对我是不是真心的？")
    finally:
        if saved_key:
            os.environ["DEEPSEEK_API_KEY"] = saved_key
        if saved_llm:
            os.environ["LLM_API_KEY"] = saved_llm
    assert "「" not in cap and "」" not in cap
    assert "标题" not in cap and "正文" not in cap  # 直接可拷贝，无字段标签
    assert len(cap.splitlines()[0]) <= 20  # 首行即标题
    # 平台高敏词一律不进文案，只豁免品牌名「塔罗气泡」（软植入句也走这个豁免）
    for w in BANNED_WORDS:
        assert w not in cap.replace("塔罗气泡", ""), f"文案出现禁词: {w}"
    # 贴纸文案同样是画面上的字，一起守：新加文案别把高敏词带回来
    cfg = json.loads((BASE / "content.json").read_text(encoding="utf-8"))
    for k, v in cfg["copies"].items():
        for w in BANNED_WORDS:
            assert w not in v["line1"] + v["line2"], f"贴纸文案 {k} 含禁词 {w}"
    print("[selftest] ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="?", help="占卜主题（注入提问页）")
    ap.add_argument("--copy", default=None, help="贴纸文案 key（content.json）")
    ap.add_argument("--no-compose", action="store_true", help="只录屏不合成")
    ap.add_argument("--cover", action="store_true",
                    help="顺手用即梦出一张首图（温暖治愈带淡淡忧郁电影感女性人像，形象随机）拼到片头 0.8s，耗积分")
    ap.add_argument("--speed", type=float, default=2.5, help="成片变速倍率（默认 2.5x，目标成片 ≤40s）")
    ap.add_argument("--fit", default="bleed", choices=["bleed", "bars", "both", "pad"],
                    help="画幅适配（默认只出 bleed）：bleed=裁上下铺满 9:16（零侧边）；"
                         "bars/both 是备用，日常别用")
    ap.add_argument("--selftest", action="store_true", help="纯逻辑自检")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.topic:
        ap.error("缺主题参数")

    preflight()
    d = SimDriver()
    slug = slugify(args.topic)
    ts = time.strftime("%Y%m%d-%H%M%S")
    raw_dir, out_dir = BASE / "raw", BASE / "out"
    raw_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)
    # 素材按问题名分目录：out/<问题名>/ 下只放这一篇的发布文案 + 成片
    # （贴纸 PNG / _fail 截图 / .calibration.json 这些公共文件仍留在 out/ 根）
    mat_dir = out_dir / material_dirname(args.topic)
    mat_dir.mkdir(exist_ok=True)
    raw = raw_dir / f"{ts}-{slug}.mov"

    d.activate()
    time.sleep(1)
    d.fit_window()
    print(f"[info] 内容区: {d.win}")
    rec = Recorder()
    rec.start(raw)
    time.sleep(1)
    try:
        marks = run_flow(d, args.topic, rec)
    except Exception as e:
        fail_png = out_dir / f"_fail-{ts}.png"
        sh(["xcrun", "simctl", "io", DEVICE, "screenshot", str(fail_png)], check=False)
        rec.stop()
        sys.exit(f"[fail] {e}\n现场截图: {fail_png}\n录屏保留: {raw}")
    rec.stop()
    print(f"[done] 录屏: {raw}")

    # 挂钟打点 → 视频时间轴校准：recordVideo 起录到首帧有固定 offset（实测 4.3s，逐条不同），
    # 录制时间轴比挂钟慢。不校准的话裁剪点整体后移，会把洗牌页切掉、成片直接从抽牌开始。
    if marks.get("shuffle_t"):
        t_wall = marks["shuffle_t"]
        t_video = find_page_start(raw, "结束洗牌", t_wall)
        if t_video is None:
            print("[warn] 没在录屏里定位到洗牌页，裁剪点退回挂钟秒（可能切掉洗牌页）")
            marks["start"] = max(0.0, t_wall - 0.5)
        else:
            drift = t_wall - t_video
            print(f"[info] 时间轴校准：录屏比挂钟慢 {drift:.1f}s"
                  f"（洗牌页 视频 {t_video:.1f}s / 挂钟 {t_wall:.1f}s）")
            # 定位精度 1s 且 fps 取样是就近取帧：t_video 可能比洗牌首帧早最多 ~0.5s，
            # 起点直接定在 t_video 会把上一页（连接宇宙能量 loading）的尾巴带进成片。
            # +0.3s 跳过过渡尾：2.5x 下只损失洗牌开头 0.12s，但保证首帧就是洗牌页。
            # ponytail: 0.3 是经验值；loading 页是动画帧密，够跳过去；静态页 VFR 间隔超 0.3s 时会漏
            marks["start"] = t_video + 0.3
            for k in ("draw_t0", "draw_t1", "loading_t0", "loading_t1"):
                if marks.get(k):
                    marks[k] -= drift
    (mat_dir / f"{ts}-文案.txt").write_text(gen_caption(args.topic), encoding="utf-8")
    # 打点存档：成片要重剪/改位置时不用 OCR 重建（2026-09-14 重建过一次才加的）
    (mat_dir / f"{ts}-marks.json").write_text(json.dumps(
        {"marks": marks, "speed": args.speed, "fit": args.fit, "raw": raw.name},
        ensure_ascii=False, indent=1), encoding="utf-8")

    if not args.no_compose:
        cover_png = None
        if args.cover:
            # 首图：温暖治愈带淡淡忧郁电影感女性人像，形象配方随机（见 gen_cover.py），失败不阻断主流程
            subprocess.run([sys.executable, str(BASE / "gen_cover.py"),
                            "--count", "1", "--out", str(mat_dir)], check=False)
            covers = sorted(mat_dir.glob("cover-*.png"), key=lambda p: p.stat().st_mtime)
            cover_png = str(covers[-1]) if covers else None
        cmd = [sys.executable, str(BASE / "gen_video.py"), str(raw),
               "--speed", str(args.speed), "--fit", args.fit]
        if cover_png:
            cmd += ["--cover", cover_png]
        # 从洗牌页起剪（起点是校准后的视频时间，见上面 find_page_start）
        if marks.get("start"):
            cmd += ["--ss", f"{marks['start']:.1f}"]
        # 分段额外加速：抽牌等待动画再快 2 倍；解读流式 loading 是静止页，再快 6 倍（总 15x）
        boosts = []
        if marks.get("draw_t0") and marks.get("draw_t1"):
            boosts.append(f"{marks['draw_t0']:.1f}:{marks['draw_t1']:.1f}:2.0")
        if marks.get("loading_t0"):
            # 解读 loading 之后一直加速到片尾，尾部 3.2s 由 --tail-hold 截回来走常速
            # （解读是静止页，多录的等待全压掉；不这样写，等的秒数会原样留在成片里）
            boosts.append(f"{marks['loading_t0']:.1f}:9999:6.0")
        if boosts:
            cmd += ["--boost", ",".join(boosts)]
        # 尾部常速段按「视频真实结尾」倒推：打点用的是挂钟秒，录屏时间轴会漂（实测差 2s+），
        # 用挂钟时间当裁剪点会把解读整段吃掉
        cmd += ["--tail-hold", str(TAIL_HOLD)]
        # 空白段只在「抽牌页→解读页」之间扫：App 白屏只出现在抽牌确认之间，
        # 扫整片会误剪开头的洗牌页淡入
        if marks.get("draw_t0") and marks.get("loading_t0"):
            cmd += ["--drop-range", f"{marks['draw_t0']:.1f}:{marks['loading_t0']:.1f}"]
        if args.copy:
            cmd += ["--copy", args.copy]
        before = {p.name for p in out_dir.glob("*.mp4")}
        subprocess.run(cmd, check=True)
        # gen_video 先落在 out/ 根，这里按问题名归档：<问题名>/<时间戳>-<贴纸key>[-fit].mp4
        for p in sorted(out_dir.glob("*.mp4")):
            if p.name in before or not p.name.startswith(f"{ts}-{slug}"):
                continue
            tail = p.stem[len(f"{ts}-{slug}"):]  # 形如 -xinshi 或 -xinshi-bleed
            dest = mat_dir / f"{ts}{tail}.mp4"
            shutil.move(str(p), str(dest))
            print(f"[done] 成片: {dest}")
    print(f"[done] 素材目录: {mat_dir}")


if __name__ == "__main__":
    main()

import ApplicationServices
import CoreGraphics
import Foundation

// 权限自检：自动录屏需要「辅助功能」（CGEvent 点击）+「屏幕录制」（读 Simulator 窗口位置）。
// 用法: perm_check           只检查，输出 accessibility=true/false screenrecording=true/false
//       perm_check --prompt  对缺失项弹系统授权框
let ax = AXIsProcessTrusted()
let scr = CGPreflightScreenCaptureAccess()
print("accessibility=\(ax)")
print("screenrecording=\(scr)")
if CommandLine.arguments.contains("--prompt") {
    if !ax {
        let opts = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(opts)
    }
    if !scr {
        _ = CGRequestScreenCaptureAccess()
    }
    print("prompted=true")
}

import Vision
import AppKit
import Foundation

// 系统 Swift + Vision OCR（macOS），输出带坐标框的 JSON 行，供自动录屏定位文字。
// 用法: ocr_boxes <图片路径> [识别语言, 默认 zh-Hans]
// 输出: 每行 {"text":"...","x":..,"y":..,"w":..,"h":..}（像素坐标，左上原点）
let args = CommandLine.arguments
guard args.count >= 2 else { print("LOAD_FAIL"); exit(1) }
guard let img = NSImage(contentsOfFile: args[1]) else { print("LOAD_FAIL"); exit(1) }
let lang = args.count >= 3 ? args[2] : "zh-Hans"
var rect = NSRect(origin: .zero, size: img.size)
guard let cg = img.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { print("CG_FAIL"); exit(1) }
let W = CGFloat(cg.width), H = CGFloat(cg.height)

func esc(_ s: String) -> String {
    return s.replacingOccurrences(of: "\\", with: "\\\\")
        .replacingOccurrences(of: "\"", with: "\\\"")
}

let request = VNRecognizeTextRequest { req, _ in
    guard let obs = req.results as? [VNRecognizedTextObservation] else { return }
    for o in obs {
        guard let t = o.topCandidates(1).first else { continue }
        let b = o.boundingBox  // 归一化，左下原点
        let x = b.origin.x * W
        let y = (1 - b.origin.y - b.height) * H
        let w = b.width * W
        let h = b.height * H
        print("{\"text\":\"\(esc(t.string))\",\"x\":\(x),\"y\":\(y),\"w\":\(w),\"h\":\(h)}")
    }
}
request.recognitionLevel = .accurate
request.recognitionLanguages = [lang]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try? handler.perform([request])

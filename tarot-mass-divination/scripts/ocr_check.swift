import Vision
import AppKit
import Foundation

// 系统 Swift + Vision 中文 OCR（macOS）。本机 Python 无 ocrmac，默认用此工具。
// 用法: ocr_check <图片路径> [识别语言, 默认 zh-Hans]
// 逐行输出识别文本。
let args = CommandLine.arguments
guard args.count >= 2 else { print("LOAD_FAIL"); exit(1) }
guard let img = NSImage(contentsOfFile: args[1]) else { print("LOAD_FAIL"); exit(1) }
let lang = args.count >= 3 ? args[2] : "zh-Hans"
var rect = NSRect(origin: .zero, size: img.size)
guard let cg = img.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { print("CG_FAIL"); exit(1) }
let request = VNRecognizeTextRequest { req, _ in
    guard let obs = req.results as? [VNRecognizedTextObservation] else { return }
    for o in obs {
        if let t = o.topCandidates(1).first { print(t.string) }
    }
}
request.recognitionLevel = .accurate
request.recognitionLanguages = [lang]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try? handler.perform([request])

// macOS Vision による独立OCR。1行1件のJSONを出力する。座標は画像左上原点のピクセル。
import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count == 2,
      let image = NSImage(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    FileHandle.standardError.write(Data("usage: ocr IMAGE\n".utf8))
    exit(2)
}
var rect = NSRect.zero
guard let cg = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { exit(2) }
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["ja-JP", "en-US"]
request.usesLanguageCorrection = false
try VNImageRequestHandler(cgImage: cg).perform([request])
let w = Double(cg.width), h = Double(cg.height)
for item in request.results ?? [] {
    guard let top = item.topCandidates(1).first else { continue }
    let b = item.boundingBox
    let row: [String: Any] = [
        "text": top.string,
        "bbox": [Int((1 - b.maxY) * h), Int(b.minX * w), Int((1 - b.minY) * h), Int(b.maxX * w)],
        "score": Double(top.confidence),
    ]
    let data = try JSONSerialization.data(withJSONObject: row, options: [.sortedKeys])
    print(String(decoding: data, as: UTF8.self))
}

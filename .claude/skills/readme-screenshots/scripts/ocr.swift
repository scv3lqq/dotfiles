import Foundation
import Vision
import ImageIO

func fail(_ msg: String) -> Never {
    FileHandle.standardError.write(Data("ocr: \(msg)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 2 else { fail("usage: ocr <png>") }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
      let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { fail("cannot read \(url.path)") }

let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
do {
    try VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
} catch {
    fail("\(error)")
}
for o in req.results ?? [] {
    if let c = o.topCandidates(1).first { print(c.string) }
}

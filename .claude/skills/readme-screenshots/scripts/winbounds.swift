import CoreGraphics
import Foundation
// usage: winbounds <window-id>... -> "id x y w h" in points (global, top-left origin)
let ids = Set(CommandLine.arguments.dropFirst().compactMap { Int($0) })
let list = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]] ?? []
for w in list {
    guard let n = w[kCGWindowNumber as String] as? Int, ids.contains(n),
          let b = w[kCGWindowBounds as String] as? [String: Any] else { continue }
    let v = ["X", "Y", "Width", "Height"].map { Int((b[$0] as? NSNumber)?.doubleValue ?? -1) }
    print(n, v[0], v[1], v[2], v[3])
}

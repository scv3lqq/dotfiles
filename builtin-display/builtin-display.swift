// builtin-display: disable the MacBook built-in display while an external
// display is active, re-enable it otherwise.
//
// macOS has no public API for this. SkyLight's SLSConfigureDisplayEnabled,
// called inside a CoreGraphics configuration transaction, performs a real
// disconnect on Apple Silicon (same mechanism as Lunar BlackOut and
// BetterDisplay connection management).
import CoreGraphics
import Darwin
import Foundation

typealias ConfigureEnabledFn = @convention(c) (CGDisplayConfigRef, CGDirectDisplayID, Bool) -> CGError
typealias GetDisplayListFn = @convention(c) (UInt32, UnsafeMutablePointer<CGDirectDisplayID>?, UnsafeMutablePointer<UInt32>) -> CGError

struct SkyLight {
    let configureEnabled: ConfigureEnabledFn
    let getDisplayList: GetDisplayListFn

    // Resolved at runtime so a macOS release that drops the symbols fails
    // with a clear message instead of a dyld crash at launch.
    static func load() -> SkyLight? {
        guard let handle = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_LAZY),
              let configure = dlsym(handle, "SLSConfigureDisplayEnabled"),
              let list = dlsym(handle, "SLSGetDisplayList")
        else { return nil }
        return SkyLight(
            configureEnabled: unsafeBitCast(configure, to: ConfigureEnabledFn.self),
            getDisplayList: unsafeBitCast(list, to: GetDisplayListFn.self)
        )
    }
}

func log(_ message: String) {
    let stamp = ISO8601DateFormatter().string(from: Date())
    FileHandle.standardError.write(Data("\(stamp) \(message)\n".utf8))
}

func activeDisplays() -> [CGDirectDisplayID] {
    var count: UInt32 = 0
    guard CGGetActiveDisplayList(0, nil, &count) == .success, count > 0 else { return [] }
    var ids = [CGDirectDisplayID](repeating: 0, count: Int(count))
    guard CGGetActiveDisplayList(count, &ids, &count) == .success else { return [] }
    return Array(ids.prefix(Int(count)))
}

// CGGetOnlineDisplayList drops a display disabled through SkyLight, so the
// built-in ID is looked up in SkyLight's own list, which keeps it.
func allDisplays(_ sl: SkyLight) -> [CGDirectDisplayID] {
    var count: UInt32 = 0
    guard sl.getDisplayList(0, nil, &count) == .success, count > 0 else { return [] }
    var ids = [CGDirectDisplayID](repeating: 0, count: Int(count))
    guard sl.getDisplayList(count, &ids, &count) == .success else { return [] }
    return Array(ids.prefix(Int(count)))
}

struct State {
    let builtin: CGDirectDisplayID?
    let builtinActive: Bool
    let externals: [CGDirectDisplayID]
}

func currentState(_ sl: SkyLight) -> State {
    let active = activeDisplays()
    let builtin = allDisplays(sl).first { CGDisplayIsBuiltin($0) != 0 }
        ?? active.first { CGDisplayIsBuiltin($0) != 0 }
    let externals = active.filter { CGDisplayIsBuiltin($0) == 0 }
    let builtinActive = builtin.map { active.contains($0) } ?? false
    return State(builtin: builtin, builtinActive: builtinActive, externals: externals)
}

enum ToolError: Error, CustomStringConvertible {
    case noBuiltin
    case noExternal
    case cg(String, CGError)

    var description: String {
        switch self {
        case .noBuiltin: return "built-in display not found"
        case .noExternal: return "no active external display, refusing to disable the built-in"
        case let .cg(op, err): return "\(op) failed: CGError \(err.rawValue)"
        }
    }
}

func setBuiltin(_ sl: SkyLight, enabled: Bool) throws {
    let state = currentState(sl)
    guard let id = state.builtin else { throw ToolError.noBuiltin }
    if !enabled && state.externals.isEmpty { throw ToolError.noExternal }

    var config: CGDisplayConfigRef?
    let begin = CGBeginDisplayConfiguration(&config)
    guard begin == .success, let cfg = config else { throw ToolError.cg("CGBeginDisplayConfiguration", begin) }
    let res = sl.configureEnabled(cfg, id, enabled)
    guard res == .success else {
        CGCancelDisplayConfiguration(cfg)
        throw ToolError.cg("SLSConfigureDisplayEnabled", res)
    }
    // forSession, not permanently: a reboot or logout always brings the
    // built-in back, so a crashed watcher can never strand the user.
    let done = CGCompleteDisplayConfiguration(cfg, .forSession)
    guard done == .success else { throw ToolError.cg("CGCompleteDisplayConfiguration", done) }
}

final class Watcher {
    let sl: SkyLight
    var generation = 0
    // Signature of the display set for which an action was last attempted;
    // stops a retry loop when an action does not change anything (lid closed).
    var lastAttempt: String?

    init(sl: SkyLight) { self.sl = sl }

    func schedule() {
        generation += 1
        let gen = generation
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            guard let self, gen == self.generation else { return }
            self.reconcile()
        }
    }

    func reconcile() {
        let state = currentState(sl)
        guard state.builtin != nil else { return }
        let wantEnabled = state.externals.isEmpty
        guard wantEnabled != state.builtinActive else {
            lastAttempt = nil
            return
        }
        let signature = "\(state.externals.sorted())-\(state.builtinActive)"
        guard signature != lastAttempt else { return }
        lastAttempt = signature
        do {
            try setBuiltin(sl, enabled: wantEnabled)
            log("built-in \(wantEnabled ? "enabled" : "disabled"), externals=\(state.externals)")
        } catch {
            log("reconcile: \(error)")
        }
    }

    func restoreAndExit(_ sig: Int32) -> Never {
        let state = currentState(sl)
        if state.builtin != nil && !state.builtinActive {
            do { try setBuiltin(sl, enabled: true); log("signal \(sig): built-in enabled") } catch { log("signal \(sig): \(error)") }
        }
        exit(0)
    }
}

func runWatch(_ sl: SkyLight) -> Never {
    let watcher = Watcher(sl: sl)
    var sources: [DispatchSourceSignal] = []
    for sig in [SIGTERM, SIGINT, SIGHUP] {
        signal(sig, SIG_IGN)
        let src = DispatchSource.makeSignalSource(signal: sig, queue: .main)
        src.setEventHandler { watcher.restoreAndExit(sig) }
        src.resume()
        sources.append(src)
    }
    let ctx = Unmanaged.passRetained(watcher).toOpaque()
    let cb: CGDisplayReconfigurationCallBack = { _, flags, user in
        if flags.contains(.beginConfigurationFlag) { return }
        guard let user else { return }
        Unmanaged<Watcher>.fromOpaque(user).takeUnretainedValue().schedule()
    }
    let reg = CGDisplayRegisterReconfigurationCallback(cb, ctx)
    guard reg == .success else {
        log("CGDisplayRegisterReconfigurationCallback failed: CGError \(reg.rawValue)")
        exit(2)
    }
    log("watching display changes")
    // Callbacks can be missed across sleep/wake; a slow periodic check
    // converges the state anyway.
    let timer = DispatchSource.makeTimerSource(queue: .main)
    timer.schedule(deadline: .now(), repeating: 30)
    timer.setEventHandler { watcher.reconcile() }
    timer.resume()
    withExtendedLifetime((sources, timer)) { CFRunLoopRun() }
    exit(0)
}

let usage = "usage: builtin-display on|off|status|watch"
let args = CommandLine.arguments.dropFirst()
guard args.count == 1, let cmd = args.first else {
    FileHandle.standardError.write(Data("\(usage)\n".utf8))
    exit(1)
}
guard let sl = SkyLight.load() else {
    log("SkyLight symbols not found on this macOS")
    exit(2)
}

switch cmd {
case "status":
    let s = currentState(sl)
    let builtin = s.builtin.map { "\($0) \(s.builtinActive ? "on" : "off")" } ?? "none"
    print("built-in: \(builtin)")
    print("externals: \(s.externals.isEmpty ? "none" : s.externals.map(String.init).joined(separator: " "))")
case "on", "off":
    do { try setBuiltin(sl, enabled: cmd == "on") } catch {
        log("\(cmd): \(error)")
        exit(2)
    }
case "watch":
    runWatch(sl)
default:
    FileHandle.standardError.write(Data("\(usage)\n".utf8))
    exit(1)
}

// builtin-display: disable the MacBook built-in display while an external
// display is active, re-enable it otherwise.
//
// macOS has no public API for this. SkyLight's SLSConfigureDisplayEnabled,
// called inside a CoreGraphics configuration transaction, performs a real
// disconnect on Apple Silicon (same mechanism as Lunar BlackOut and
// BetterDisplay connection management).
import AppKit
import CoreGraphics
import Darwin
import Foundation
import IOKit
import IOKit.pwr_mgt

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

struct DisplayInfo: Equatable {
    let id: CGDirectDisplayID
    let builtin: Bool
    let active: Bool
    let vendor: UInt32
    let widthMM: Double

    // When the last real display goes away WindowServer activates a
    // VirtualDisplay as main so the session keeps a screen. It is not
    // built-in, so counting every non-built-in active display as external
    // kept the built-in dark after an unplug. The placeholder has no monitor
    // behind it: no EDID size and a sentinel vendor (0xFFFFFFFF: no monitor,
    // 'unkn': IOKit could not identify one). A real monitor without EDID is
    // treated the same way, which errs on the side of a lit built-in.
    var isRealExternal: Bool {
        !builtin && active && widthMM > 0 && ![0, 0xFFFF_FFFF, 0x756E_6B6E].contains(vendor)
    }

    var summary: String {
        let kind = builtin ? "builtin" : (isRealExternal ? "external" : "virtual")
        return "\(id):\(kind):\(active ? "on" : "off"):v\(String(vendor, radix: 16)):\(Int(widthMM))mm"
    }
}

enum Action: Equatable { case none, enable, disable }

// trusted: externals seen while the built-in was on. With the built-in off
// only those count, so a display that appears after the last real one left
// (the placeholder, whatever properties it reports) never keeps it dark. A
// monitor plugged in while the built-in is off costs one on/off flicker.
func decide(_ displays: [DisplayInfo], trusted: Set<CGDirectDisplayID>) -> Action {
    guard let builtin = displays.first(where: { $0.builtin }) else { return .none }
    let hasExternal = displays.contains { $0.isRealExternal && (builtin.active || trusted.contains($0.id)) }
    if hasExternal && builtin.active { return .disable }
    if !hasExternal && !builtin.active { return .enable }
    return .none
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
func skyLightDisplays(_ sl: SkyLight) -> [CGDirectDisplayID] {
    var count: UInt32 = 0
    guard sl.getDisplayList(0, nil, &count) == .success, count > 0 else { return [] }
    var ids = [CGDirectDisplayID](repeating: 0, count: Int(count))
    guard sl.getDisplayList(count, &ids, &count) == .success else { return [] }
    return Array(ids.prefix(Int(count)))
}

func snapshot(_ sl: SkyLight) -> [DisplayInfo] {
    let active = Set(activeDisplays())
    let ids = Set(skyLightDisplays(sl)).union(active).sorted()
    return ids.map { id in
        DisplayInfo(
            id: id,
            builtin: CGDisplayIsBuiltin(id) != 0,
            active: active.contains(id),
            vendor: CGDisplayVendorNumber(id),
            widthMM: Double(CGDisplayScreenSize(id).width)
        )
    }
}

func describe(_ displays: [DisplayInfo]) -> String {
    displays.isEmpty ? "none" : displays.map(\.summary).joined(separator: " ")
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
    let displays = snapshot(sl)
    guard let id = displays.first(where: { $0.builtin })?.id else { throw ToolError.noBuiltin }
    if !enabled && !displays.contains(where: { $0.isRealExternal }) { throw ToolError.noExternal }

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

// IOKit message constants are function-like C macros that Swift does not import.
let msgCanSystemSleep: natural_t = 0xE000_0270
let msgSystemWillSleep: natural_t = 0xE000_0280
let msgSystemHasPoweredOn: natural_t = 0xE000_0300

final class Watcher {
    let sl: SkyLight
    var generation = 0
    var lastSeen: String?
    // Snapshot for which an action was last attempted; stops a retry loop
    // when an action does not change anything (lid closed).
    var lastAttempt: String?
    var rootPort: io_connect_t = 0
    var trusted: Set<CGDirectDisplayID> = []

    init(sl: SkyLight) { self.sl = sl }

    func schedule(after delay: Double) {
        generation += 1
        let gen = generation
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self, gen == self.generation else { return }
            self.reconcile()
        }
    }

    func reconcile() {
        let displays = snapshot(sl)
        let seen = describe(displays)
        if seen != lastSeen {
            log("state \(seen)")
            lastSeen = seen
        }
        if displays.contains(where: { $0.builtin && $0.active }) {
            trusted = Set(displays.filter(\.isRealExternal).map(\.id))
        }
        let action = decide(displays, trusted: trusted)
        guard action != .none else {
            lastAttempt = nil
            return
        }
        guard seen != lastAttempt else { return }
        lastAttempt = seen
        do {
            try setBuiltin(sl, enabled: action == .enable)
            log("built-in \(action == .enable ? "enabled" : "disabled")")
        } catch {
            log("reconcile: \(error)")
        }
    }

    func power(_ message: natural_t, _ argument: UnsafeMutableRawPointer?) {
        switch message {
        case msgCanSystemSleep, msgSystemWillSleep:
            IOAllowPowerChange(rootPort, Int(bitPattern: argument))
        case msgSystemHasPoweredOn:
            log("power: woke")
            lastAttempt = nil
            schedule(after: 1.0)
        default:
            break
        }
    }

    func restoreAndExit(_ sig: Int32) -> Never {
        let displays = snapshot(sl)
        if let builtin = displays.first(where: { $0.builtin }), !builtin.active {
            do { try setBuiltin(sl, enabled: true); log("signal \(sig): built-in enabled") } catch { log("signal \(sig): \(error)") }
        } else {
            log("signal \(sig): exit")
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

    let cb: CGDisplayReconfigurationCallBack = { display, flags, user in
        guard let user else { return }
        log("callback display=\(display) flags=0x\(String(flags.rawValue, radix: 16))")
        if flags.contains(.beginConfigurationFlag) { return }
        Unmanaged<Watcher>.fromOpaque(user).takeUnretainedValue().schedule(after: 1.0)
    }
    let reg = CGDisplayRegisterReconfigurationCallback(cb, ctx)
    guard reg == .success else {
        log("CGDisplayRegisterReconfigurationCallback failed: CGError \(reg.rawValue)")
        exit(2)
    }

    var notifyPort: IONotificationPortRef?
    var notifier: io_object_t = 0
    let powerCb: IOServiceInterestCallback = { ref, _, message, argument in
        guard let ref else { return }
        Unmanaged<Watcher>.fromOpaque(ref).takeUnretainedValue().power(message, argument)
    }
    watcher.rootPort = IORegisterForSystemPower(ctx, &notifyPort, powerCb, &notifier)
    if watcher.rootPort != 0, let port = notifyPort {
        CFRunLoopAddSource(CFRunLoopGetMain(), IONotificationPortGetRunLoopSource(port).takeUnretainedValue(), .defaultMode)
    } else {
        log("IORegisterForSystemPower failed, relying on polling after wake")
    }

    log("watching display changes")
    // The callback is the fast path; the poll bounds the reaction time when
    // a callback is missed or arrives before the display list settles.
    let timer = DispatchSource.makeTimerSource(queue: .main)
    timer.schedule(deadline: .now(), repeating: 2.0, leeway: .milliseconds(200))
    timer.setEventHandler { watcher.reconcile() }
    timer.resume()
    // NSApplication, not CFRunLoopRun: a bare run loop never receives the
    // WindowServer display notifications, so callbacks only fired when the
    // process itself made a CG call and the display list it read stayed
    // stale. Prohibited policy keeps it out of the Dock and app switcher.
    withExtendedLifetime((sources, timer)) {
        NSApplication.shared.setActivationPolicy(.prohibited)
        NSApplication.shared.run()
    }
    exit(0)
}

func selftest() -> Never {
    let builtinOn = DisplayInfo(id: 1, builtin: true, active: true, vendor: 0x610, widthMM: 286)
    let builtinOff = DisplayInfo(id: 1, builtin: true, active: false, vendor: 0x610, widthMM: 286)
    let monitor = DisplayInfo(id: 2, builtin: false, active: true, vendor: 0x61A9, widthMM: 602)
    let monitorGone = DisplayInfo(id: 2, builtin: false, active: false, vendor: 0x61A9, widthMM: 602)
    let placeholder = DisplayInfo(id: 3, builtin: false, active: true, vendor: 0xFFFF_FFFF, widthMM: 0)
    let unknown = DisplayInfo(id: 4, builtin: false, active: true, vendor: 0x756E_6B6E, widthMM: 0)
    let noEdid = DisplayInfo(id: 5, builtin: false, active: true, vendor: 0x61A9, widthMM: 0)
    // A placeholder that reports monitor-like properties: only trust stops it.
    let lookalike = DisplayInfo(id: 3, builtin: false, active: true, vendor: 0x61A9, widthMM: 602)
    let seen: Set<CGDirectDisplayID> = [2]
    let cases: [(String, [DisplayInfo], Set<CGDirectDisplayID>, Action)] = [
        ("external plugged, built-in on", [builtinOn, monitor], [], .disable),
        ("external plugged, built-in off", [builtinOff, monitor], seen, .none),
        ("external unplugged, placeholder active", [builtinOff, placeholder], seen, .enable),
        ("external unplugged, unknown vendor placeholder", [builtinOff, unknown], seen, .enable),
        ("external unplugged, lookalike placeholder", [builtinOff, lookalike], seen, .enable),
        ("external unplugged, nothing active", [builtinOff], seen, .enable),
        ("external listed but inactive", [builtinOff, monitorGone], seen, .enable),
        ("built-in off at start, nothing trusted", [builtinOff, monitor], [], .enable),
        ("no external, built-in on", [builtinOn], [], .none),
        ("placeholder only, built-in on", [builtinOn, placeholder], [], .none),
        ("monitor without EDID size", [builtinOn, noEdid], [], .none),
        ("real external next to placeholder", [builtinOn, monitor, placeholder], [], .disable),
        ("no built-in (desktop Mac)", [monitor], seen, .none),
    ]
    var failed = 0
    for (name, displays, trusted, want) in cases {
        let got = decide(displays, trusted: trusted)
        let ok = got == want
        if !ok { failed += 1 }
        print("\(ok ? "ok  " : "FAIL") \(name): \(got)\(ok ? "" : ", want \(want)")")
    }
    print(failed == 0 ? "PASS \(cases.count)" : "FAILED \(failed)/\(cases.count)")
    exit(failed == 0 ? 0 : 1)
}

let usage = "usage: builtin-display on|off|status|watch|selftest"
let args = CommandLine.arguments.dropFirst()
guard args.count == 1, let cmd = args.first else {
    FileHandle.standardError.write(Data("\(usage)\n".utf8))
    exit(1)
}
if cmd == "selftest" { selftest() }
guard let sl = SkyLight.load() else {
    log("SkyLight symbols not found on this macOS")
    exit(2)
}

switch cmd {
case "status":
    let displays = snapshot(sl)
    print(describe(displays))
    // A one-shot command trusts what is active now; watch tracks it over time.
    print("action: \(decide(displays, trusted: Set(displays.map(\.id))))")
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

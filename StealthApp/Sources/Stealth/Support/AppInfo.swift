import AppKit

/// Marketing version is user-facing; the independent build number is diagnostic only.
enum AppInfo {
    static var version: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0.0.0" }
    static var build: String { Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0" }
    static var display: String { ReleaseVersion(version)?.display ?? "版本未知" }
    static var diagnostic: String { "\(display) · Build \(build)" }
    static var aboutPanelOptions: [NSApplication.AboutPanelOptionKey: Any] {
        [.applicationVersion: display, .version: ""]
    }
}

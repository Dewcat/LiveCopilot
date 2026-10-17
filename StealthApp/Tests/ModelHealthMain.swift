import Foundation
import AppKit

@main struct ModelHealthMain {
    @MainActor static func main() async throws {
        let args = CommandLine.arguments
        let source = URL(fileURLWithPath: args[1]), executable = URL(fileURLWithPath: args[2])
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("model-health-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        // Exercise the actual installer, checksum/commit, manager and real native worker.
        let manager = LocalModelManager(root: root, checker: { kind, root in
            try await LocalModelSelfCheck.run(kind, root: root, executable: executable)
        }, installation: { kind, root in
            try await LocalModelInstaller.install(kind, root: root, downloader: { file, target in
                try FileManager.default.copyItem(at: source.appendingPathComponent(file.name), to: target)
            })
        })
        manager.install(.embedding)
        while manager.downloading != nil { try await Task.sleep(nanoseconds: 50_000_000) }
        precondition(manager.installed.contains(.embedding) && manager.health[.embedding]?.ready == true)
        let report = manager.health[.embedding]!.diagnostic(kind: .embedding)
        precondition(!report.contains(root.path) && !report.contains(NSUserName()) && !report.contains("Local model self-check."))
        print("PASS verified install → real self-check → ready; privacy-safe diagnostics")
        // Use a private pasteboard; do not overwrite the user's clipboard during tests.
        let board = NSPasteboard.withUniqueName()
        precondition(board.setString(report, forType: .string))
        precondition(board.string(forType: .string) == report)
        board.releaseGlobally()
        print("PASS diagnostic pasteboard roundtrip")
        let fake = root.appendingPathComponent("failing-worker")
        try "#!/bin/sh\nprintf '%s\\n' '{\"ready\":false,\"error\":\"embedding_context\"}'\n".write(to: fake, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: fake.path)
        let failure = try await LocalModelSelfCheck.run(.embedding, root: root, executable: fake)
        precondition(failure.stage == .memory && failure.checksum == "passed")
        precondition(failure.advice(english: false).contains("关闭"))
        let missing = try await LocalModelSelfCheck.run(.embedding, root: root, executable: root.appendingPathComponent("missing"))
        precondition(missing.stage == .runtime)
        print("PASS memory failure and missing runtime give distinct recovery advice")
        let file = LocalModelKind.embedding.location(in: root).appendingPathComponent("bge-m3-Q8_0.gguf")
        let handle = try FileHandle(forWritingTo: file)
        try handle.write(contentsOf: Data([0, 0, 0, 0])); try handle.close()
        precondition(LocalModelKind.embedding.isInstalled(in: root))
        manager.runSelfCheck(.embedding)
        while manager.downloading != nil { try await Task.sleep(nanoseconds: 50_000_000) }
        precondition(manager.health[.embedding]?.stage == .files)
        precondition(manager.health[.embedding]!.advice(english: false).contains("重新下载"))
        manager.install(.embedding)
        while manager.downloading != nil { try await Task.sleep(nanoseconds: 50_000_000) }
        precondition(manager.health[.embedding]?.ready == true)
        print("PASS same-size corruption → failed self-check → reinstall → ready")
        let cancelled = LocalModelManager(root: root, checker: { _, _ in
            try await Task.sleep(nanoseconds: 30_000_000_000)
            return .init(stage: .ready, checkedAt: Date(), checksum: "passed", runtimeCode: "ok")
        })
        cancelled.runSelfCheck(.embedding)
        while cancelled.checking == nil { await Task.yield() }
        cancelled.cancel(); await cancelled.shutdown()
        precondition(cancelled.health[.embedding] == nil && cancelled.checking == nil && cancelled.downloading == nil)
        precondition(LocalModelKind.embedding.isInstalled(in: root))
        print("PASS cancellation never marks ready and preserves installed model")
        await manager.shutdown()
    }
}

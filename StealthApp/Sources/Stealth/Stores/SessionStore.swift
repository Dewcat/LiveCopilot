import Foundation
import Combine

/// Persists finished sessions as one JSON file each under
/// `~/Library/Application Support/LiveCopilot/sessions/<id>.json`, and exposes the
/// list (most recent first) to the History UI. Kept forever until deleted.
@MainActor
final class SessionStore: ObservableObject {
    @Published private(set) var sessions: [SessionRecord] = []
    @Published private(set) var lastError: String?

    private let fileManager = FileManager.default
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    private let root: URL
    init(root: URL? = nil) {
        self.root = root ?? AppPaths.dataDirectory().appendingPathComponent("sessions", isDirectory: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        self.encoder = encoder

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder

        loadAll()
    }

    /// Directory holding the per-session JSON files. Created on demand.
    private var directory: URL? {
        let dir = root
        if !fileManager.fileExists(atPath: dir.path) {
            do {
                try fileManager.createDirectory(at: dir, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            } catch {
                DebugLog.log("SessionStore: create dir failed: \(error.localizedDescription)")
                return nil
            }
        }
        return dir
    }

    /// Build a record from live transcript lines and persist it.
    /// No-op when there are no lines (an empty session isn't worth saving).
    @discardableResult
    func save(lines: [TranscriptLine], startedAt: Date, endedAt: Date = Date(), fragments: [TranscriptFragment] = []) -> SessionRecord? {
        saveSnapshot(lines: lines.map { SessionLine(from: $0) }, startedAt: startedAt, endedAt: endedAt, fragments: fragments, answers: [])
    }
    @discardableResult
    func saveSnapshot(lines: [SessionLine], startedAt: Date, endedAt: Date = Date(), fragments: [TranscriptFragment] = [], answers: [SessionAnswer]) -> SessionRecord? {
        guard !lines.isEmpty || !answers.isEmpty else { return nil }
        var record = SessionRecord(startedAt: startedAt, endedAt: endedAt, lines: lines)
        record.fragments = fragments; record.answers = answers; record.schemaVersion = 2
        guard persist(record) else { return nil }
        sessions = ([record] + sessions).sorted { $0.startedAt > $1.startedAt }
        return record
    }
    @discardableResult
    func update(_ id: UUID, change: (inout SessionRecord) -> Void) -> Bool {
        // A late API response or answer must never resurrect a deleted session.
        guard let index = sessions.firstIndex(where: { $0.id == id }) else { return false }
        var record = sessions[index]; change(&record)
        guard persist(record) else { return false }
        sessions[index] = record
        return true
    }

    func delete(_ record: SessionRecord) {
        if let url = fileURL(for: record.id) {
            do { try fileManager.removeItem(at: url) }
            catch { lastError = "Could not delete session history. Check disk permissions."; return }
        }
        if let url = directory?.appendingPathComponent(record.id.uuidString + ".txt"), fileManager.fileExists(atPath: url.path) {
            do { try fileManager.removeItem(at: url) } catch { lastError = "Could not delete transcript draft." }
        }
        sessions = sessions.filter { $0.id != record.id }
    }

    func export(_ record: SessionRecord, to url: URL) throws {
        try Data(record.export(markdown: url.pathExtension.lowercased() == "md").utf8).write(to: url, options: .atomic)
        try? fileManager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    }

    // MARK: - Disk

    private func fileURL(for id: UUID) -> URL? {
        directory?.appendingPathComponent("\(id.uuidString).json")
    }

    private func persist(_ record: SessionRecord) -> Bool {
        guard let url = fileURL(for: record.id) else { lastError = "Cannot access local session storage."; return false }
        do {
            let data = try encoder.encode(record)
            try data.write(to: url, options: .atomic)
            try? fileManager.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
            lastError = nil
            do { try export(record, to: url.deletingPathExtension().appendingPathExtension("txt")) }
            catch { lastError = "Session saved; transcript draft could not be written. You can export it from History." }
            return true
        } catch {
            lastError = "Session history could not be saved. Check available disk space and permissions."
            return false
        }
    }

    private func loadAll() {
        guard let dir = directory,
              let urls = try? fileManager.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
        else { return }
        let loaded: [SessionRecord] = urls
            .filter { $0.pathExtension == "json" }
            .compactMap { url in
                guard let data = try? Data(contentsOf: url) else { return nil }
                guard var record = try? decoder.decode(SessionRecord.self, from: data) else { return nil }
                if record.namingState == "pending" { record.namingState = "failed" }
                return record
            }
        sessions = loaded.sorted { $0.startedAt > $1.startedAt }
    }
}

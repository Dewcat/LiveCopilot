import Foundation
import Combine

@MainActor
final class LocalModelManager: ObservableObject {
    let root: URL
    @Published private(set) var installed: Set<LocalModelKind> = []
    @Published private(set) var downloading: LocalModelKind?
    @Published private(set) var queued: [LocalModelKind] = []
    @Published private(set) var failures: [LocalModelKind: String] = [:]
    @Published private(set) var message = ""
    @Published private(set) var messageKind: LocalModelKind?
    @Published private(set) var downloadProgress: Double?
    @Published private(set) var transferStatus = ""
    @Published private(set) var embeddingVerification: ServiceVerification = .idle
    private var verificationTask: Task<Void, Never>?
    private let embeddingVerifier: (@MainActor (URL) async throws -> Void)?
    private var task: Task<Void, Never>?
    private let installation: (@MainActor (LocalModelKind, URL) async throws -> Void)?
    init(root: URL, embeddingVerifier: (@MainActor (URL) async throws -> Void)? = nil, installation: (@MainActor (LocalModelKind, URL) async throws -> Void)? = nil) {
        self.root = root; self.installation = installation; self.embeddingVerifier = embeddingVerifier; refresh()
    }
    func refresh() {
        installed = Set(LocalModelKind.allCases.filter { $0.isInstalled(in: root) })
        if !installed.contains(.embedding) { embeddingVerification = .idle }
    }
    func verifyEmbeddingIfNeeded() async {
        guard embeddingVerification == .idle else { return }
        await verifyEmbedding()
    }
    func verifyEmbedding() async {
        guard verificationTask == nil, installed.contains(.embedding) else { return }
        embeddingVerification = .checking
        let operation = Task { @MainActor in
            do {
                if let embeddingVerifier { try await embeddingVerifier(LocalModelKind.embedding.location(in: root)) }
                else {
                    let provider = LocalEmbeddingProvider(directory: LocalModelKind.embedding.location(in: root))
                    defer { provider.close() }
                    try await EmbeddingConnectionProbe.run(provider: provider)
                }
                try Task.checkCancellation()
                embeddingVerification = .ready
            } catch is CancellationError { embeddingVerification = .idle }
            catch { embeddingVerification = .failed(error.localizedDescription) }
        }
        verificationTask = operation
        await withTaskCancellationHandler { await operation.value } onCancel: { operation.cancel() }
        verificationTask = nil
    }
    func enqueue(_ kinds: [LocalModelKind]) {
        refresh()
        for kind in kinds where !installed.contains(kind) && downloading != kind && !queued.contains(kind) { queued.append(kind) }
        installNext()
    }
    private func installNext() {
        guard task == nil, !queued.isEmpty else { return }
        let kind = queued.removeFirst()
        if installed.contains(kind) { installNext() } else { install(kind) }
    }
    func install(_ kind: LocalModelKind) {
        guard task == nil, verificationTask == nil else { return }
        if kind == .embedding { embeddingVerification = .idle }
        failures[kind] = nil
        downloadProgress = nil; transferStatus = ""
        downloading = kind; messageKind = kind; message = "Downloading local model…"
        task = Task { [weak self] in
            guard let self else { return }
            defer { self.downloading = nil; self.task = nil; self.refresh(); self.installNext() }
            do {
                if let installation = self.installation { try await installation(kind, self.root) }
                else { try await LocalModelInstaller.install(kind, root: self.root, downloader: { [weak self] item, destination in
                    try await LocalModelInstaller.download(item, to: destination) { [weak self] fraction, detail in
                        Task { @MainActor in self?.downloadProgress = fraction; self?.transferStatus = detail }
                    }
                }, status: { [weak self] value in
                    Task { @MainActor in self?.message = value }
                }) }
                self.refresh()
                if kind == .embedding {
                    await self.verifyEmbedding()
                    self.message = self.embeddingVerification.message
                } else { self.message = "Local model installed. It can run offline." }
            } catch is CancellationError { self.message = "Model download cancelled. The previous model was preserved."; self.failures[kind] = self.message }
            catch let error as URLError where error.code == .cancelled { self.message = "Model download cancelled. The previous model was preserved."; self.failures[kind] = self.message }
            catch { self.message = error is CopilotError ? error.localizedDescription : "Model download failed. Check the network and retry."; self.failures[kind] = self.message }
        }
    }
    func remove(_ kind: LocalModelKind) {
        guard task == nil, verificationTask == nil else { return }
        messageKind = kind
        do {
            let directory = kind.location(in: root)
            if FileManager.default.fileExists(atPath: directory.path) { try FileManager.default.removeItem(at: directory) }
            downloadProgress = nil; transferStatus = ""
            message = "Local model deleted. Download it again to use it."
        } catch { message = error.localizedDescription }
        refresh()
    }
    func cancel() { queued.removeAll(); task?.cancel(); verificationTask?.cancel() }
    func shutdown() async { cancel(); await task?.value; await verificationTask?.value }
}

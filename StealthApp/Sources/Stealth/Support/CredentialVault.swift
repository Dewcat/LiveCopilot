import Foundation
import CryptoKit

protocol CredentialStorage: Sendable {
    func read(service: String, account: String, interactive: Bool) throws -> String?
    func save(_ key: String, service: String, account: String, interactive: Bool) throws
    func clear(service: String, account: String) throws
}

struct SystemCredentialStorage: CredentialStorage {
    func read(service: String, account: String, interactive: Bool) throws -> String? {
        try KeychainStore.read(service: service, account: account, interactive: interactive)
    }
    func save(_ key: String, service: String, account: String, interactive: Bool) throws {
        try KeychainStore.save(key, service: service, account: account, interactive: interactive)
    }
    func clear(service: String, account: String) throws { try KeychainStore.clear(service: service, account: account) }
}

struct CredentialState: Sendable {
    var key: String?
    var needsAuthorization = false
    var message: String {
        if needsAuthorization { return "Saved key needs authorization. Click Authorize saved key to allow access." }
        return key == nil ? "No credential available." : "Credential available. No API request made."
    }
}

/// App-owned production credentials. Only non-secret migration markers enter preferences.
/// Serial execution also prevents a pending migration from undoing a replacement or removal.
actor CredentialVault {
    static let shared = CredentialVault()
    static let service = "LiveCopilot-Credentials-v1"
    private let storage: any CredentialStorage
    private let defaults: UserDefaults
    private let environmentKey: String?
    init(storage: any CredentialStorage = SystemCredentialStorage(), defaults: UserDefaults = .standard,
         environmentKey: String? = ProcessInfo.processInfo.environment["OPENAI_API_KEY"]) {
        self.storage = storage; self.defaults = defaults
        let value = environmentKey?.trimmingCharacters(in: .whitespacesAndNewlines)
        self.environmentKey = value?.isEmpty == false ? value : nil
    }
    static func account(for reference: CredentialReference) -> String { reference.service + "|" + reference.account }
    private func marker(_ reference: CredentialReference) -> String {
        "credential.migrated." + SHA256.hash(data: Data(Self.account(for: reference).utf8)).map { String(format: "%02x", $0) }.joined()
    }
    func read(_ reference: CredentialReference, interactive: Bool = false) throws -> CredentialState {
        do {
            if let key = try storage.read(service: Self.service, account: Self.account(for: reference), interactive: interactive) {
                return CredentialState(key: key)
            }
            // Removing a managed key must never silently resurrect its old development copy.
            guard !defaults.bool(forKey: marker(reference)) else { return CredentialState() }
            if let key = try storage.read(service: reference.service, account: reference.account, interactive: interactive) {
                try save(key, for: reference, interactive: interactive)
                return CredentialState(key: key)
            }
            return CredentialState(key: reference == .live ? environmentKey : nil)
        } catch let error as KeychainAccessError where error.needsAuthorization {
            return CredentialState(needsAuthorization: true)
        }
    }
    func save(_ value: String, for reference: CredentialReference, interactive: Bool = true) throws {
        let key = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty else { throw CopilotError.message("API key cannot be empty.") }
        try storage.save(key, service: Self.service, account: Self.account(for: reference), interactive: interactive)
        defaults.set(true, forKey: marker(reference))
    }
    func remove(_ reference: CredentialReference) throws {
        try storage.clear(service: Self.service, account: Self.account(for: reference))
        defaults.set(true, forKey: marker(reference))
    }
}

/// A local Keychain read is separate from validating a key with its service.
enum CredentialCheckFeedback: Equatable {
    case checking, found, missing, authorization, failed
    static func resolve(checking: Bool, available: Bool, authorization: Bool, status: String) -> Self {
        if checking { return .checking }
        if available { return .found }
        if authorization { return .authorization }
        return status == "No credential available." ? .missing : .failed
    }
    func title(_ language: AppLanguage) -> String {
        let text: (String, String)
        switch self {
        case .checking: text = ("Checking saved key…", "正在检查已保存的密钥…")
        case .found: text = ("Saved key found", "已找到保存的密钥")
        case .missing: text = ("No saved key found", "未找到已保存的密钥")
        case .authorization: text = ("Keychain authorization required", "需要钥匙串授权")
        case .failed: text = ("Could not read saved key", "密钥读取失败")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
    var symbol: String {
        switch self {
        case .checking: return "clock"
        case .found: return "checkmark.circle.fill"
        case .missing: return "key.horizontal"
        case .authorization: return "lock.circle"
        case .failed: return "exclamationmark.triangle"
        }
    }
    func message(_ language: AppLanguage) -> String {
        let text: (String, String)
        switch self {
        case .checking: text = ("Checking this service's saved key…", "正在检查当前服务的已保存密钥…")
        case .found: text = ("Saved key found. This check only reads Keychain; no API request was made.", "已找到保存的密钥。本次仅检查本机钥匙串，未发送 API 请求。")
        case .missing: text = ("No saved key was found for this service. Enter a key above and save it.", "未找到当前服务的已保存密钥，请在上方输入并保存。")
        case .authorization: text = ("Keychain authorization is required. Check again and approve the macOS authorization dialog.", "需要钥匙串授权，请再次检查并完成 macOS 系统授权。")
        case .failed: text = ("Could not read the saved key. Check the Keychain status above and try again.", "读取已保存密钥失败，请查看上方钥匙串状态后重试。")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
}

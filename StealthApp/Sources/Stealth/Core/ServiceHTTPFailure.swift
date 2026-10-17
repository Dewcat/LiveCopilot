import Foundation

/// Retains only a category/status, never a provider's raw error message or body.
struct ServiceHTTPFailure: LocalizedError {
    enum Kind: CaseIterable {
        case authentication, billing, permission, model, parameters, rateLimit, service
        var message: String {
            switch self {
            case .authentication: return "API key rejected. It may be invalid, expired or revoked. Replace it with a key for this provider and region."
            case .billing: return "API balance or usage limit reached. Check whether the account needs a top-up, credits have expired, or a spending limit was reached."
            case .permission: return "Service access denied. Check model permissions and regional availability."
            case .model: return "Model or endpoint unavailable. Check the model ID and service address."
            case .parameters: return "Service rejected the request. Check model name and supported configuration."
            case .rateLimit: return "Request frequency or quota limit reached. Retry later; if it persists, check API balance and usage limits."
            case .service: return "Service is temporarily unavailable. Retry shortly."
            }
        }
    }
    let status: Int
    let kind: Kind
    init(status: Int, data: Data? = nil) {
        self.status = status
        let object = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
        // HTTP, SSE and WebSocket errors share this parser. Match explicit codes,
        // not free-form messages (which may contain credentials/request text).
        let error = object?["error"] as? [String: Any] ?? object ?? [:]
        let codes = [error["code"], error["type"]].compactMap { ($0 as? String)?.lowercased() }
        let billing = ["insufficient_quota", "insufficient_balance", "credit_balance_exhausted",
                       "billing_hard_limit_reached", "billing_limit_reached", "usage_limit_reached",
                       "organization_usage_limit_exceeded", "spend_limit_reached", "arrearage", "isv.out_of_service"]
        let authentication = ["invalid_api_key", "invalidapikey", "expired_api_key", "api_key_expired",
                              "invalid_authentication", "authentication_error", "revoked_api_key"]
        if status == 401 || codes.contains(where: authentication.contains) { kind = .authentication }
        else if status == 402 || codes.contains(where: billing.contains) { kind = .billing }
        else if codes.contains("rate_limit_exceeded") || codes.contains("rate_limit_error") || codes.contains("slow_down") { kind = .rateLimit }
        else if codes.contains(where: ["permission_denied", "access_denied", "insufficient_permissions"].contains) { kind = .permission }
        else if codes.contains(where: ["model_not_found", "unknown_model", "model_not_exist", "model_not_available"].contains) { kind = .model }
        else {
            switch status {
            case 403: kind = .permission
            case 404: kind = .model
            case 429: kind = .rateLimit
            case 400, 422: kind = .parameters
            default: kind = .service
            }
        }
    }
    var errorDescription: String? { kind.message + (status > 0 ? " (HTTP \(status))" : "") }

    /// Some existing runtime state machines carry safe strings rather than Error.
    /// Recover only our own exact messages; never classify arbitrary server prose.
    static func kind(fromSafeMessage message: String) -> Kind? {
        let base = message.replacingOccurrences(of: #" \(HTTP [0-9]{3}\)$"#, with: "", options: .regularExpression)
        return Kind.allCases.first { $0.message == base }
    }
}

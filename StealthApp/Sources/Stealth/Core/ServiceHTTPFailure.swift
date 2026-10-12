import Foundation

/// Retains only a category/status, never a provider's raw error message or body.
struct ServiceHTTPFailure: LocalizedError {
    enum Kind { case authentication, permission, model, parameters, rateLimit, service }
    let status: Int
    let kind: Kind
    init(status: Int, data: Data? = nil) {
        self.status = status
        let object = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
        let error = object?["error"] as? [String: Any]
        let code = error?["code"] as? String ?? ""
        switch status {
        case 401: kind = .authentication
        case 403: kind = .permission
        case 404: kind = .model
        case 429: kind = .rateLimit
        case 400, 422:
            kind = ["model_not_found", "unknown_model", "model_not_exist", "model_not_available"].contains(code) ? .model : .parameters
        default: kind = .service
        }
    }
    var errorDescription: String? {
        switch kind {
        case .authentication: return "Service authentication/access failed (401). Check the API key and model access in Services."
        case .permission: return "Service authentication/access failed (403). Check the API key and model access in Services."
        case .model, .parameters: return "Service rejected the request (\(status)). Check model name and supported configuration."
        case .rateLimit: return "Service rate or credit limit reached. Check API billing/limits and retry later."
        case .service: return "Service is temporarily unavailable (\(status)). Retry shortly."
        }
    }
}

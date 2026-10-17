import Foundation

/// Display names come from the shared catalog, never inferred from a custom ID.
enum OnboardingAnalysisChoice {
    static func displayName(_ settings: AppSettings) -> String? {
        AnalysisModelCatalog.model(settings.analysisModel, service: settings.reasoningService)?.name
    }
}

enum OnboardingConnectionFailure: Equatable {
    case authentication, billing, permission, model, parameters, rateLimit, timeout, network, service
    static func classify(_ error: Error) -> Self {
        if let kind = (error as? ServiceHTTPFailure)?.kind ?? ServiceHTTPFailure.kind(fromSafeMessage: error.localizedDescription) {
            switch kind {
            case .authentication: return .authentication
            case .billing: return .billing
            case .permission: return .permission
            case .model: return .model
            case .parameters: return .parameters
            case .rateLimit: return .rateLimit
            case .service: return .service
            }
        }
        if (error as NSError).domain == NSURLErrorDomain {
            return (error as NSError).code == URLError.timedOut.rawValue ? .timeout : .network
        }
        if ["Connection test timed out. Check the network and retry.", "Live startup timed out. Check network and model access."].contains(error.localizedDescription) { return .timeout }
        if ["Live connection failed. Check your network.", "No internet connection. Reconnect and try the speech service again."].contains(error.localizedDescription) { return .network }
        return .service
    }
    func title(_ language: AppLanguage) -> String {
        let text: (String, String)
        switch self {
        case .authentication: text = ("API key invalid or expired", "密钥无效或已过期")
        case .billing: text = ("API balance or usage limit reached", "API 余额或额度不足")
        case .permission: text = ("Access denied", "访问权限不足")
        case .model: text = ("Model or endpoint unavailable", "模型或接口不可用")
        case .parameters: text = ("Unsupported request configuration", "请求参数不受支持")
        case .rateLimit: text = ("Request frequency or quota limit", "请求频率或额度受限")
        case .timeout: text = ("Connection test timed out", "连接测试超时")
        case .network: text = ("Network issue", "网络异常")
        case .service: text = ("Connection test failed", "连接测试失败")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
    func detail(_ language: AppLanguage) -> String {
        let text: (String, String)
        switch self {
        case .authentication: text = ("The key may be incorrect, expired or revoked. Create a new key and confirm it matches this provider and region.", "密钥可能填写错误、已过期或被撤销。请在服务商平台重新创建密钥，并确认服务商与地域匹配。")
        case .billing: text = ("Check whether API billing needs a top-up, credits have expired, or a spending limit was reached; then test again.", "请到服务商的 API 账单页检查：是否尚未充值、余额已用完、额度已过期或达到用量上限；处理后重新测试。")
        case .permission: text = ("Check your account's model access and regional restrictions.", "请检查账户的模型访问权限及地区限制。")
        case .model: text = ("Check the API Model ID and endpoint. A 404 can mean the model or API path does not exist.", "请检查 API Model ID 与接口地址；404 可能表示模型或接口路径不存在。")
        case .parameters: text = ("Check the model ID and its supported reasoning parameters.", "请检查模型 ID 及该模型支持的推理参数。")
        case .rateLimit: text = ("Retry later. If it persists, check API balance and usage limits; a 429 alone does not confirm missing funds.", "请稍后重试；若持续失败，再检查 API 余额与用量上限。仅凭 429 无法确认是否未充值。")
        case .timeout: text = ("The service did not answer in time. Retry, or choose a faster model or lower effort.", "服务未及时返回回答，可重试或选择更快的模型及更低推理档位。")
        case .network: text = ("Check your network and service address, then retry or set up later.", "请检查网络及服务地址后重试，也可以稍后设置。")
        case .service: text = ("The service did not provide a specific cause. Check API billing and whether the key has expired or been revoked, then retry.", "服务未返回明确原因。可检查 API 是否已充值，以及密钥是否已过期或被撤销，再重试。")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
}

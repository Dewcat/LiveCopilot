import Foundation

/// Display names come from the shared catalog, never inferred from a custom ID.
enum OnboardingAnalysisChoice {
    static func displayName(_ settings: AppSettings) -> String? {
        AnalysisModelCatalog.model(settings.analysisModel, service: settings.reasoningService)?.name
    }
}

enum OnboardingConnectionFailure: Equatable {
    case authentication, permission, model, parameters, rateLimit, timeout, network, service
    static func classify(_ error: Error) -> Self {
        if let failure = error as? ServiceHTTPFailure {
            switch failure.kind {
            case .authentication: return .authentication
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
        if error.localizedDescription == "Connection test timed out. Check the network and retry." { return .timeout }
        return .service
    }
    func title(_ language: AppLanguage) -> String {
        let text: (String, String)
        switch self {
        case .authentication: text = ("API key not accepted · 401", "API Key 无效 · 401")
        case .permission: text = ("Access denied · 403", "访问权限不足 · 403")
        case .model: text = ("Model or endpoint unavailable", "模型或接口不可用")
        case .parameters: text = ("Unsupported request configuration", "请求参数不受支持")
        case .rateLimit: text = ("Rate or credit limit · 429", "频率或额度受限 · 429")
        case .timeout: text = ("Connection test timed out", "连接测试超时")
        case .network: text = ("Network issue", "网络异常")
        case .service: text = ("Connection test failed", "连接测试失败")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
    func detail(_ language: AppLanguage) -> String {
        let text: (String, String)
        switch self {
        case .authentication: text = ("Check the saved key belongs to this provider and region.", "请确认已保存密钥属于当前服务商及地域。")
        case .permission: text = ("Check your account's model access and regional restrictions.", "请检查账户的模型访问权限及地区限制。")
        case .model: text = ("Check the API Model ID and endpoint. A 404 can mean the model or API path does not exist.", "请检查 API Model ID 与接口地址；404 可能表示模型或接口路径不存在。")
        case .parameters: text = ("Check the model ID and its supported reasoning parameters.", "请检查模型 ID 及该模型支持的推理参数。")
        case .rateLimit: text = ("Check API balance and rate limits, then retry later.", "请检查 API 余额与频率限制，稍后重试。")
        case .timeout: text = ("The service did not answer in time. Retry, or choose a faster model or lower effort.", "服务未及时返回回答，可重试或选择更快的模型及更低推理档位。")
        case .network: text = ("Check your network and service address, then retry or set up later.", "请检查网络及服务地址后重试，也可以稍后设置。")
        case .service: text = ("The service could not complete this request. Retry later or choose another service.", "服务未能完成请求，请稍后重试或更换服务。")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
}

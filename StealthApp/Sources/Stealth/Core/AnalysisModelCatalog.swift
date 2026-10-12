import Foundation

/// Shared by onboarding, Settings and the request factory. Unknown IDs receive no
/// optional reasoning parameters. Capability sources checked 2026-10-11.
struct AnalysisModel: Identifiable, Equatable {
    let id: String
    let name: String
    let service: ReasoningService
    let modes: [AnalysisThinking]
    var recommendedThinking: AnalysisThinking { ["deepseek-flash", "qwen3.8-flash", "kimi-k2.6"].contains(id) ? .disabled : .low }
}

enum AnalysisModelCatalog {
    static let models: [AnalysisModel] = [
        .init(id: "gpt-6-luna", name: "GPT-6 Luna", service: .separateOpenAI, modes: [.disabled, .low, .medium, .high, .xhigh, .max]),
        .init(id: "gpt-6-sol", name: "GPT-6 Sol", service: .separateOpenAI, modes: [.disabled, .low, .medium, .high, .xhigh, .max]),
        .init(id: "gpt-6.1-sol", name: "GPT-6.1 Sol", service: .separateOpenAI, modes: [.low, .medium, .high, .xhigh, .max]),
        .init(id: "deepseek-flash", name: "DeepSeek V4.1 Flash", service: .deepSeek, modes: [.disabled, .low, .high, .max]),
        .init(id: "qwen3.8-flash", name: "Qwen3.8 Flash", service: .qwen, modes: [.disabled, .low, .medium, .xhigh]),
        .init(id: "glm-5.3-flash", name: "GLM-5.3 Flash", service: .glm, modes: [.low, .high, .max]),
        .init(id: "glm-5.3-flashx", name: "GLM-5.3 FlashX", service: .glm, modes: [.low, .high, .max]),
        .init(id: "kimi-k2.6", name: "Kimi K2.6", service: .kimi, modes: [.disabled, .enabled]),
        .init(id: "kimi-k3", name: "Kimi K3", service: .kimi, modes: [.low, .high, .max])
    ]
    static func models(for service: ReasoningService) -> [AnalysisModel] {
        models.filter { $0.service == (service == .sharedOpenAI ? .separateOpenAI : service) }
    }
    static func model(_ id: String, service: ReasoningService) -> AnalysisModel? {
        models(for: service).first { $0.id == id.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
    }
    static func recommended(for service: ReasoningService) -> AnalysisModel? {
        switch service {
        case .sharedOpenAI, .separateOpenAI: return model("gpt-6-sol", service: service)
        case .glm: return model("glm-5.3-flashx", service: service)
        default: return models(for: service).first
        }
    }
    static func normalized(_ value: AnalysisThinking, model id: String, service: ReasoningService) -> AnalysisThinking {
        guard let model = model(id, service: service) else { return .modelDefault }
        if model.modes.contains(value) { return value }
        // Documented compatibility aliases are not additional API capabilities.
        if id == "kimi-k2.6", value != .modelDefault { return .enabled }
        if service == .qwen, [.high, .max].contains(value) { return .xhigh }
        if service == .deepSeek, [.medium, .xhigh].contains(value) { return .high }
        return model.recommendedThinking
    }
    static func normalized(_ value: String, model: String, service: ReasoningService) -> AnalysisThinking {
        var value = value
        if value == "none" { value = "disabled" }
        if value == "minimal", service == .deepSeek || service == .qwen { value = "low" }
        if value == "ultra", service == .deepSeek { value = "max" }
        return normalized(AnalysisThinking(rawValue: value) ?? .modelDefault, model: model, service: service)
    }
    static func description(for service: ReasoningService, language: AppLanguage) -> String {
        let text: (String, String)
        switch service {
        case .sharedOpenAI, .separateOpenAI: text = ("Balanced capability and speed at a low cost, for quick questions and everyday meetings.", "综合能力与速度均衡，成本较低，适合快速问答及日常会议。")
        case .deepSeek: text = ("Fast, cost-conscious answers for conversations primarily in Chinese.", "擅长中文对话，输出速度快，适合以中文为主的面试和会议。")
        case .qwen: text = ("Balanced speed, Chinese-language ability and cost for everyday exchanges.", "适合中英文问答与日常交流，兼顾响应速度、中文能力和成本。")
        case .glm: text = ("Faster output than Flash, at a higher price, for longer live answers.", "比普通 Flash 输出更快、价格更高，适合实时生成较长回答。")
        case .kimi: text = ("For complex questions. Thinking can delay the visible answer; turn it off for faster replies.", "适合复杂理解与深度回答；思考会延长等待，实时场景可关闭。")
        case .compatible: text = ("Use the model ID and endpoint supplied by your service.", "使用服务商提供的模型 ID 与接口地址。")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
    static func tags(for service: ReasoningService, language: AppLanguage) -> String {
        let text: (String, String)
        switch service {
        case .sharedOpenAI, .separateOpenAI: text = ("Technical quality · Responsive", "技术质量 · 速度兼顾")
        case .deepSeek: text = ("Chinese-friendly · Low cost", "中文友好 · 低成本")
        case .qwen: text = ("Chinese-friendly · Balanced", "中文友好 · 稳定均衡")
        case .glm: text = ("Fast output · Live conversations", "高速输出 · 实时优先")
        case .kimi: text = ("Thinking off · Shorter wait", "关闭思考 · 减少等待")
        case .compatible: text = ("Custom connection", "自定义连接")
        }
        return ServiceGuide.text(text.0, text.1, language)
    }
}

extension AnalysisThinking {
    var isAdvanced: Bool { [.medium, .high, .xhigh, .max].contains(self) }
    var menuName: String {
        switch self {
        case .disabled: return "Off"
        case .enabled: return "On"
        case .modelDefault: return "Default"
        default: return rawValue == "xhigh" ? "Xhigh" : rawValue.capitalized
        }
    }
    var referenceKey: String { self == .disabled ? "none" : rawValue }
    func displayName(_ language: AppLanguage) -> String {
        switch self {
        case .modelDefault: return ServiceGuide.text("Model default", "模型默认", language)
        case .disabled: return ServiceGuide.text("Off", "Off · 关闭思考", language)
        case .enabled: return ServiceGuide.text("On", "On · 开启思考", language)
        default: return rawValue == "xhigh" ? "Xhigh" : rawValue.capitalized
        }
    }
}

extension AppSettings {
    var analysisThinking: AnalysisThinking {
        get {
            switch reasoningService {
            case .sharedOpenAI, .separateOpenAI: return AnalysisModelCatalog.normalized(reasoningEffort, model: analysisModel, service: reasoningService)
            case .deepSeek: return AnalysisModelCatalog.normalized(deepSeekEffort, model: analysisModel, service: reasoningService)
            case .qwen, .glm, .kimi: return reasoningService.normalizedThinking(presetConnection!.thinking, model: analysisModel)
            case .compatible: return .modelDefault
            }
        }
        set {
            let mode = AnalysisModelCatalog.normalized(newValue, model: analysisModel, service: reasoningService)
            switch reasoningService {
            case .sharedOpenAI, .separateOpenAI: reasoningEffort = mode == .modelDefault ? "" : mode.referenceKey
            case .deepSeek: deepSeekEffort = mode == .modelDefault ? "" : mode.referenceKey
            case .qwen, .glm, .kimi: presetConnection?.thinking = mode
            case .compatible: break
            }
        }
    }
    var usesRecommendedAnalysis: Bool {
        guard let model = AnalysisModelCatalog.recommended(for: reasoningService) else { return false }
        return analysisModel == model.id && analysisThinking == model.recommendedThinking && analysisProcessing == .standard
    }
    var isOpenAIAnalysis: Bool { reasoningService == .sharedOpenAI || reasoningService == .separateOpenAI }
    var supportsOpenAIFast: Bool {
        isOpenAIAnalysis && ["gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol"].contains(analysisModel)
    }
    var usesOpenAIFast: Bool { analysisProcessing == .fast }
    /// Explicit provider selection in the model chooser applies its recommendation.
    /// Loading saved settings or switching credential sharing does not reset it.
    mutating func selectRecommendedAnalysisService(_ service: ReasoningService) {
        selectAnalysisService(service)
        applyAnalysisRecommendation()
    }
    mutating func applyAnalysisRecommendation() {
        guard let model = AnalysisModelCatalog.recommended(for: reasoningService) else { return }
        selectAnalysisModel(model.id)
        analysisThinking = model.recommendedThinking
        if isOpenAIAnalysis { openAIProcessing = .standard }
    }
    /// Only recognized standard routes receive public metrics/prices. A custom
    /// proxy or a Coding Plan endpoint must not inherit another route's figures.
    var analysisStandardRoute: String? {
        switch reasoningService {
        case .sharedOpenAI, .separateOpenAI: return "openai"
        case .deepSeek: return "deepseek"
        case .compatible: return nil
        case .qwen, .glm, .kimi:
            guard let endpoint = try? presetConnection?.endpoint(), endpoint.port == nil else { return nil }
            let value = endpoint.absoluteString
            let routes = [
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions": "qwen-cn",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions": "qwen-intl",
                "https://open.bigmodel.cn/api/paas/v4/chat/completions": "glm-cn",
                "https://api.z.ai/api/paas/v4/chat/completions": "glm-intl",
                "https://api.moonshot.cn/v1/chat/completions": "kimi-cn",
                "https://api.moonshot.ai/v1/chat/completions": "kimi-intl"
            ]
            guard let route = routes[value], route.hasPrefix(reasoningService.rawValue + "-") else { return nil }
            return route
        }
    }
}

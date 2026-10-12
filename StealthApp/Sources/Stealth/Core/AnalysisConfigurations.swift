import Foundation

enum AnalysisProcessing: String, Codable, CaseIterable, Identifiable {
    case standard, fast, ultrafast
    var id: String { rawValue }
    var name: String { rawValue.capitalized }
    var wireValue: String { self == .standard ? "default" : rawValue }
}

enum AnalysisReferenceKind: String, Codable { case publicSnapshot, community, estimate }

struct AnalysisConfiguration: Codable, Identifiable {
    let id: Int
    let service: ReasoningService
    let model: String
    let name: String
    let thinking: AnalysisThinking
    let processing: AnalysisProcessing
    let recommended: Bool
    let providerDefault: Bool
    let rank: Int?
    let reason: String
    let limits: String
    let kind: AnalysisReferenceKind
    let ttft: String
    let speed: String
    let firstTokenSeconds: Double?
    let tokensPerSecond: Double?
    let currency: String
    let input: Double
    let output: Double
    let source: String
    let sourceURL: String
    let priceURL: String
    let date: String
    let basis: String
    let presentation: String
    var label: String { name + " · " + thinking.menuName + " · " + processing.name }
}

/// Current onboarding copy supplied on 2026-10-12 supersedes older menu flags
/// for these exact combinations, without changing a provider's default.
struct FeaturedAnalysisConfiguration {
    let service: ReasoningService
    let model: String
    let name: String
    let processing: AnalysisProcessing
    let english: String
    let chinese: String
    var title: String { name + " · Low · " + processing.name }
}

/// Offline, reviewed import of the owner's 58-row CSV. Estimates remain ranges;
/// they are never converted into measurements or first-visible-answer promises.
enum AnalysisConfigurations {
    static let featured: [FeaturedAnalysisConfiguration] = [
        .init(service: .separateOpenAI, model: "gpt-6-sol", name: "GPT-6 Sol", processing: .fast,
              english: "Strong reasoning balanced with response speed, for technical interviews.", chinese: "推理能力强，兼顾响应速度，适合专业技术面试。"),
        .init(service: .separateOpenAI, model: "gpt-6-luna", name: "GPT-6 Luna", processing: .fast,
              english: "Fast generation at very low cost, for frequent live questions.", chinese: "高速生成、成本极低，适合高频实时问答。"),
        .init(service: .deepSeek, model: "deepseek-flash", name: "DeepSeek Flash", processing: .standard,
              english: "Excellent Chinese comprehension with balanced speed and value.", chinese: "中文理解出色，速度与性价比兼顾。"),
        .init(service: .glm, model: "glm-5.3-flashx", name: "GLM-5.3 FlashX", processing: .standard,
              english: "Very fast output, for quickly composing longer answers.", chinese: "生成速度极快，适合需要快速组织长回答的场景。")
    ]
    static let all: [AnalysisConfiguration] = {
        guard let url = Bundle.main.url(forResource: "AnalysisConfigurations", withExtension: "json"),
              let data = try? Data(contentsOf: url), let rows = try? JSONDecoder().decode([AnalysisConfiguration].self, from: data) else { return [] }
        return rows
    }()
    static func rows(model: String) -> [AnalysisConfiguration] { all.filter { $0.model == model } }
    static func selection(_ settings: AppSettings) -> AnalysisConfiguration? {
        guard settings.analysisStandardRoute != nil else { return nil }
        return all.first { $0.model == settings.analysisModel && $0.thinking == settings.analysisThinking && $0.processing == settings.analysisProcessing }
    }
    static func recommended(model: String, thinking: AnalysisThinking, processing: AnalysisProcessing) -> Bool {
        (thinking == .low && featured.contains { $0.model == model && $0.processing == processing }) ||
            all.contains { $0.model == model && $0.thinking == thinking && $0.processing == processing && $0.recommended }
    }
    static func modelIsRecommended(_ model: String) -> Bool { rows(model: model).contains { $0.recommended } }
    static func processingModes(model: String) -> [AnalysisProcessing] {
        AnalysisProcessing.allCases.filter { mode in rows(model: model).contains { $0.processing == mode } }
    }
    static let topFive = all.filter { $0.rank != nil }.sorted { $0.rank! < $1.rank! }
    static func topReason(_ rank: Int, language: AppLanguage) -> String {
        let texts: [(String, String)] = [
            ("Balanced quality and speed", "质量速度最平衡"),
            ("Quick Chinese answers at low cost", "中文快答且成本低"),
            ("Very fast first token, very low cost", "极快首字，费用极低"),
            ("Stronger reasoning for complex technical questions", "复杂技术题质量更高"),
            ("Fast output; verify time to the visible answer", "生成极快，需测首答")
        ]
        guard (1...texts.count).contains(rank) else { return "" }
        return ServiceGuide.text(texts[rank - 1].0, texts[rank - 1].1, language)
    }
}

extension AppSettings {
    var analysisProcessing: AnalysisProcessing {
        get {
            guard isOpenAIAnalysis, AnalysisConfigurations.processingModes(model: analysisModel).contains(openAIProcessing) else { return .standard }
            return openAIProcessing
        }
        set {
            guard isOpenAIAnalysis else { return }
            openAIProcessing = AnalysisConfigurations.processingModes(model: analysisModel).contains(newValue) ? newValue : .standard
        }
    }
}

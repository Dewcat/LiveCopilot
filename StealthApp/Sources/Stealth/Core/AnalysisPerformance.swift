import Foundation

/// Product display thresholds supplied by the owner, not benchmark grades.
/// Classify the actual displayed values; never infer a tier from a model name.
enum AnalysisMetricTier: Hashable {
    case fast, steady, slow, inexpensive, moderatePrice, expensive, uncertain

    static func latency(_ seconds: Double?) -> Self? {
        guard let seconds, seconds.isFinite, seconds >= 0 else { return nil }
        return seconds <= 1.5 ? .fast : seconds <= 3.5 ? .steady : .slow
    }
    static func generation(_ tokens: Double?) -> Self? {
        guard let tokens, tokens.isFinite, tokens > 0 else { return nil }
        return tokens >= 100 ? .fast : tokens >= 50 ? .steady : .slow
    }
    static func price(_ output: Double?, currency: AnalysisCurrency) -> Self? {
        guard let output, output.isFinite, output >= 0 else { return nil }
        let low = currency == .cny ? 10.0 : 1.5
        let high = currency == .cny ? 50.0 : 7.5
        return output <= low ? .inexpensive : output <= high ? .moderatePrice : .expensive
    }
    static func bounds(_ text: String) -> ClosedRange<Double>? {
        let pieces = text.components(separatedBy: "–")
        guard (1...2).contains(pieces.count), let lower = Double(pieces[0]),
              let upper = Double(pieces.last!), lower.isFinite, upper.isFinite,
              lower >= 0, upper >= lower else { return nil }
        return lower...upper
    }
    static func range(_ text: String, classify: (Double?) -> Self?) -> Self? {
        guard let bounds = bounds(text), let first = classify(bounds.lowerBound),
              let last = classify(bounds.upperBound) else { return nil }
        return first == last ? first : .uncertain
    }
}

/// Curated public snapshots, never fetched while selecting a model. See
/// docs/validation/2026-10-10-hybrid-jev/analysis-performance-sources.md.
/// TTFT may include reasoning tokens; TTFA is when an answer becomes visible.
struct AnalysisPerformanceSample: Equatable {
    let model: String
    let effort: String
    let firstTokenSeconds: Double
    let tokensPerSecond: Double
    let firstAnswerSeconds: Double?
    let source: String
    let url: String
    let route: String
    let capturedAt: String
    let method: String
    var productReference = false
}

struct AnalysisPerformanceSelection {
    let effort: String
    let sample: AnalysisPerformanceSample?
    let matchesConfiguration: Bool

    /// Only same-model, same-effort, verified provider measurements can populate the card.
    /// Routed measurements are labelled with the gateway and provider in the source line.
    var matchingSample: AnalysisPerformanceSample? { matchesConfiguration ? sample : nil }
}

enum AnalysisPerformance {
    static let samples: [AnalysisPerformanceSample] = AnalysisConfigurations.all.compactMap { row in
        guard row.kind != .estimate, let ttft = row.firstTokenSeconds, let speed = row.tokensPerSecond else { return nil }
        let firstAnswer: Double? = row.model == "kimi-k2.6" && row.thinking == .enabled ? 80.95 :
            ["deepseek-flash", "kimi-k2.6"].contains(row.model) && row.thinking == .disabled ? ttft : nil
        return .init(model: row.model, effort: row.thinking.referenceKey, firstTokenSeconds: ttft, tokensPerSecond: speed,
                     firstAnswerSeconds: firstAnswer, source: row.source, url: row.sourceURL, route: row.service.rawValue,
                     capturedAt: row.date, method: row.basis, productReference: row.kind == .community)
    }

    static func selection(_ settings: AppSettings) -> AnalysisPerformanceSelection {
        let effort = settings.analysisThinking.referenceKey
        guard settings.analysisProcessing == .standard, settings.analysisStandardRoute != nil,
              let model = AnalysisModelCatalog.model(settings.analysisModel, service: settings.reasoningService) else {
            return .init(effort: effort, sample: nil, matchesConfiguration: false)
        }
        let sample = samples.first { $0.model == model.id && $0.effort == effort }
        return .init(effort: effort, sample: sample, matchesConfiguration: sample != nil)
    }
}

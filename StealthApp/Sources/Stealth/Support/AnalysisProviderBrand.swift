import SwiftUI

extension ReasoningService {
    var brandName: String {
        switch self {
        case .sharedOpenAI, .separateOpenAI: return "OpenAI"
        case .deepSeek: return "DeepSeek"
        case .qwen: return "Qwen"
        case .glm: return "GLM"
        case .kimi: return "Kimi"
        case .compatible: return "OpenAI-compatible"
        }
    }
    var logoResource: String? {
        switch self {
        case .sharedOpenAI, .separateOpenAI: return "OpenAI-Logomark.svg"
        case .deepSeek: return "ProviderLogos/DeepSeek.svg"
        case .qwen: return "ProviderLogos/Qwen.png"
        case .glm: return "ProviderLogos/GLM.png"
        case .kimi: return "ProviderLogos/Kimi.ico"
        case .compatible: return nil
        }
    }
}

struct AnalysisProviderLogo: View {
    let service: ReasoningService
    var size: CGFloat = 24
    private static let images: [ReasoningService: NSImage] = Dictionary(uniqueKeysWithValues: ReasoningService.allCases.compactMap { service in
        guard let resource = service.logoResource,
              let url = Bundle.main.resourceURL?.appendingPathComponent(resource),
              let image = NSImage(contentsOf: url) else { return nil }
        return (service, image)
    })
    var body: some View {
        Group {
            if let image = Self.images[service] { Image(nsImage: image).resizable().scaledToFit() }
            else { Image(systemName: "network").resizable().scaledToFit().foregroundStyle(.secondary) }
        }.frame(width: size, height: size).padding(size / 5)
            .background(.white, in: RoundedRectangle(cornerRadius: size / 3))
            .accessibilityHidden(true)
    }
}

struct AnalysisProviderBrand: View {
    let service: ReasoningService
    let model: String
    var compact = false
    var body: some View {
        HStack(spacing: compact ? 6 : 12) {
            AnalysisProviderLogo(service: service, size: compact ? 18 : 32)
            if compact {
                Text(service.brandName).font(.caption).foregroundStyle(.secondary).help(model)
            } else {
                VStack(alignment: .leading, spacing: 4) {
                    Text(service.brandName).font(.title3.weight(.semibold))
                    Text(model).font(.caption).foregroundStyle(.secondary).lineLimit(1).help(model)
                }
            }
        }.accessibilityElement(children: .combine).accessibilityIdentifier("onboarding-practice-provider")
    }
}

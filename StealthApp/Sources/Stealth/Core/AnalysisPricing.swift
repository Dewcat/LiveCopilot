import Foundation

enum AnalysisCurrency: String { case cny = "CNY", usd = "USD"
    var symbol: String { self == .cny ? "¥" : "$" }
}

struct AnalysisExchangeRate: Equatable {
    let cnyPerUSD: Double
    let date: String
    let sourceURL: String
    // ECB 2026-10-09: 1 EUR = 1.1206 USD = 7.4992 CNY.
    static let snapshot = Self(cnyPerUSD: 7.4992 / 1.1206, date: "2026-10-09",
                              sourceURL: "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml")
    func convert(_ value: Double, from: AnalysisCurrency, to: AnalysisCurrency) -> Double {
        from == to ? value : to == .cny ? value * cnyPerUSD : value / cnyPerUSD
    }
}

struct AnalysisPrice: Equatable {
    let model: String
    let route: String
    let currency: AnalysisCurrency
    let input: Double
    let output: Double
    let sourceURL: String
    let checkedAt: String
    let conditionsEN: String
    let conditionsZH: String
    let unit = 1_000_000
    func conditions(_ language: AppLanguage) -> String { ServiceGuide.text(conditionsEN, conditionsZH, language) }
}

struct AnalysisPriceDisplay {
    let quote: AnalysisPrice
    let currency: AnalysisCurrency
    var exchangeRate: AnalysisExchangeRate? { quote.currency == currency ? nil : .snapshot }
    var input: Double { AnalysisExchangeRate.snapshot.convert(quote.input, from: quote.currency, to: currency) }
    var output: Double { AnalysisExchangeRate.snapshot.convert(quote.output, from: quote.currency, to: currency) }
    func amount(_ value: Double) -> String { currency.symbol + String(format: "%.2f", locale: Locale(identifier: "en_US_POSIX"), value) }
    func summary(_ language: AppLanguage) -> String {
        ServiceGuide.text("Input \(amount(input)) / Output \(amount(output))", "输入 \(amount(input)) / 输出 \(amount(output))", language)
    }
}

/// Standard uncached text input/output per million tokens, verified 2026-10-11.
/// Language chooses presentation currency, never a different API region. Unknown
/// routes deliberately have no quote. Updates require a new reviewed snapshot.
enum AnalysisPricing {
    private static func quote(_ model: String, _ route: String, _ currency: AnalysisCurrency, _ input: Double, _ output: Double,
                              _ url: String, _ en: String, _ zh: String) -> AnalysisPrice {
        .init(model: model, route: route, currency: currency, input: input, output: output, sourceURL: url,
              checkedAt: "2026-10-11", conditionsEN: en, conditionsZH: zh)
    }
    static let quotes: [AnalysisPrice] = [
        quote("gpt-6-luna", "openai", .usd, 0.10, 0.50, "https://developers.openai.com/api/docs/models/gpt-6-luna",
              "Standard API, ≤272K input tokens. Cache, longer contexts, regional processing and Fast/Flex/Batch have separate rates.",
              "标准 API，输入不超过 272K Token；缓存、更长上下文、区域处理及 Fast/Flex/Batch 另有报价。"),
        quote("gpt-6-sol", "openai", .usd, 2, 10, "https://developers.openai.com/api/docs/models/gpt-6-sol",
              "Standard API, ≤272K input tokens. Cache, longer contexts and other processing tiers have separate rates.",
              "标准 API，输入不超过 272K Token；缓存、更长上下文及其他处理档位另有报价。"),
        quote("gpt-6.1-sol", "openai", .usd, 2, 10, "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
              "Standard API, ≤272K input tokens. Cache, longer contexts and other processing tiers have separate rates.",
              "标准 API，输入不超过 272K Token；缓存、更长上下文及其他处理档位另有报价。"),
        quote("deepseek-flash", "deepseek", .cny, 2, 8, "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/",
              "Official CNY peak rate, uncached input. Off-peak is 50%; cached input differs. Peak: weekdays 09–12 / 14–18 Beijing, excluding public holidays.",
              "官方人民币高峰价、未缓存输入；低峰半价，缓存输入另计。高峰为工作日北京时间 09–12 / 14–18 点（法定节假日除外）。"),
        quote("deepseek-flash", "deepseek", .usd, 0.30, 1.20, "https://api-docs.deepseek.com/quick_start/pricing/",
              "Official USD peak rate, uncached input. Off-peak is 50%; cached input differs. Peak: weekdays 01–04 / 06–10 UTC, excluding Chinese public holidays.",
              "官方美元高峰价、未缓存输入；低峰半价，缓存输入另计。高峰为工作日 UTC 01–04 / 06–10 点（中国法定节假日除外）。"),
        quote("qwen3.8-flash", "qwen-cn", .cny, 0.8, 2.7, "https://help.aliyun.com/zh/model-studio/model-pricing",
              "Beijing, ≤1M input tokens; both thinking modes. Cached input has a separate discount. Other regions may differ.",
              "北京，输入不超过 1M Token；思考与非思考同价。缓存输入另有折扣，其他地域价格可能不同。"),
        quote("qwen3.8-flash", "qwen-intl", .cny, 1.094, 3.427, "https://help.aliyun.com/zh/model-studio/model-pricing",
              "Singapore / international deployment; official CNY quote, ≤1M input tokens. Cached input discounted separately.",
              "新加坡／国际部署，官方人民币报价；输入不超过 1M Token，缓存输入另有折扣。"),
        quote("glm-5.3-flash", "glm-cn", .cny, 0.8, 2.8, "https://docs.bigmodel.cn/cn/guide/start/pricing",
              "China standard general API, 1M context. Cached input and storage billed separately; not Coding Plan pricing.",
              "国内通用 API 标准价、1M 上下文；缓存命中和存储另计，不是 Coding Plan 套餐价格。"),
        quote("glm-5.3-flashx", "glm-cn", .cny, 2, 7, "https://docs.bigmodel.cn/cn/guide/start/pricing",
              "China standard general API, 1M context. Cached input and storage billed separately; not Coding Plan pricing.",
              "国内通用 API 标准价、1M 上下文；缓存命中和存储另计，不是 Coding Plan 套餐价格。"),
        quote("kimi-k2.6", "kimi-cn", .cny, 6.5, 27, "https://platform.kimi.com/",
              "China general API, standard uncached input. Cached input has a separate price; thinking tokens are billed as output.",
              "国内通用 API、标准未缓存输入；缓存命中另有报价，思考 Token 计入输出。"),
        quote("kimi-k3", "kimi-cn", .cny, 20, 100, "https://platform.kimi.com/",
              "China general API. Cached input and cache writes by TTL have separate rates. Thinking tokens count as output.",
              "国内通用 API；缓存命中及不同 TTL 的缓存写入另有报价，思考 Token 计入输出。")
    ]
    static func display(_ settings: AppSettings) -> AnalysisPriceDisplay? {
        guard let route = settings.analysisStandardRoute,
              let model = AnalysisModelCatalog.model(settings.analysisModel, service: settings.reasoningService) else { return nil }
        let currency: AnalysisCurrency = settings.language.usesChinese ? .cny : .usd
        if let row = AnalysisConfigurations.selection(settings), ["openai", "deepseek", "qwen-cn", "glm-cn", "kimi-cn"].contains(route),
           let native = AnalysisCurrency(rawValue: row.currency) {
            var conditionsEN = "Configuration table snapshot (2026-10-11), " + row.processing.name + "; standard uncached text rates. Provider region, peak periods, caching and context length may affect billing."
            var conditionsZH = "2026-10-11 配置表报价，" + row.processing.name + "，未缓存文本；实际账单受地域、峰谷时段、缓存及上下文长度影响。"
            if row.model == "deepseek-flash" {
                conditionsEN += " The table uses the USD off-peak rate; peak usage is billed at a higher rate."
                conditionsZH += " 表中使用美元低峰价，高峰时段费率更高。"
            }
            return .init(quote: quote(row.model, route, native, row.input, row.output, row.priceURL, conditionsEN, conditionsZH), currency: currency)
        }
        let candidates = quotes.filter { $0.model == model.id && $0.route == route }
        guard let quote = candidates.first(where: { $0.currency == currency }) ?? candidates.first else { return nil }
        return .init(quote: quote, currency: currency)
    }
}

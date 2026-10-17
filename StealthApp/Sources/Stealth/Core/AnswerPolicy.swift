import Foundation
import NaturalLanguage

enum KnowledgeMode: String, Codable, CaseIterable, Identifiable {
    case hybrid, knowledgeBaseOnly
    var id: String { rawValue }
    var label: String { self == .hybrid ? "Hybrid Knowledge" : "Knowledge Base Only" }
    var instructions: String {
        switch self {
        case .hybrid:
            return """
            Knowledge mode: HYBRID. Answer general questions even when there are NO relevant documents.
            Highly relevant excerpts take priority for the user's documented facts. With partial relevance,
            combine only the supported details with relevant general knowledge. Ignore unrelated excerpts
            completely and answer from your own knowledge. Retrieval candidates are NOT proof of relevance.
            Never say you cannot answer a general question merely because the knowledge base has no match.
            """
        case .knowledgeBaseOnly:
            return """
            Knowledge mode: KNOWLEDGE BASE ONLY. Factual answers must be supported by relevant supplied
            document excerpts. Do not fill evidence gaps with general knowledge. If documents are unrelated
            or insufficient, explain the specific gap briefly in the requested response language.
            Conversation may clarify the question but is not a substitute for document evidence.
            """
        }
    }
}

enum AnswerLanguage: String, Codable, CaseIterable, Identifiable {
    case auto, chinese, english
    var id: String { rawValue }
    var label: String {
        switch self { case .auto: return "Auto"; case .chinese: return "中文"; case .english: return "English" }
    }
    var instructions: String {
        switch self {
        case .chinese: return "Response language override: Simplified Chinese. Write the entire answer and headings in Chinese, regardless of the question, documents or history. Keep technical names as needed."
        case .english: return "Response language override: English. Write the entire answer and headings in English, regardless of the question, documents or history. Translate any useful Chinese evidence into English."
        case .auto:
            return """
            Response language: AUTO, evaluated afresh for THIS question. First obey an explicit request
            for a response language in the current substantive question. Otherwise use the language of
            its main semantic clause. Chinese sentences containing English technical terms are Chinese;
            English questions containing Chinese names or quotations are English. For genuinely mixed
            questions, infer the main requested explanation's language, not a raw character majority.
            Do not carry over the previous answer's language. Document language and interface language
            NEVER choose the response language. Translate evidence as needed. For recap/follow-up, use
            the latest substantive participant utterance, never the app's English command.
            """
        }
    }
    func localFallbackIsChinese(question: String) -> Bool {
        switch self {
        case .chinese: return true
        case .english: return false
        case .auto:
            let lower = question.lowercased()
            if lower.range(of: #"(?:answer|respond|reply|explain)\s+(?:only\s+)?in\s+english|(?:用|以)英语(?:回答|解释)|(?:用|以)英文(?:回答|解释)"#, options: .regularExpression) != nil { return false }
            if lower.range(of: #"(?:answer|respond|reply|explain)\s+(?:only\s+)?in\s+(?:chinese|mandarin)|(?:用|以)中文(?:回答|解释)"#, options: .regularExpression) != nil { return true }
            return NLLanguageRecognizer.dominantLanguage(for: question) == .simplifiedChinese || NLLanguageRecognizer.dominantLanguage(for: question) == .traditionalChinese
        }
    }
    func missingEvidence(question: String) -> String {
        localFallbackIsChinese(question: question)
            ? "## 回答建议\n当前为仅知识库模式，未找到足以回答这个问题的相关资料。请补充资料，或切换到混合知识模式。"
            : "## Suggested answer\nKnowledge Base Only is enabled. No relevant document evidence was found for this question. Add supporting material or switch to Hybrid Knowledge."
    }
}

enum QuestionScope {
    /// Resolve short anaphoric follow-ups locally; independent topics must not inherit old retrieval terms.
    static func needsContext(_ question: String) -> Bool {
        let q = question.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if q.hasPrefix("what about ") || q.hasPrefix("how about ") || q.hasPrefix("那") { return true }
        if q.count < 18 && ["why", "why not", "how so", "为什么", "为什么呢", "然后呢", "怎么做"].contains(q.trimmingCharacters(in: .punctuationCharacters)) { return true }
        return q.range(of: #"\b(it|its|that|those|these|they|their|this approach|this method|the previous|above)\b|它|这个|那个|上述|刚才|刚刚|其中|呢[？?]?$"#, options: .regularExpression) != nil
    }
}

enum CitationPolicy {
    /// Retain streaming output while withholding an unfinished citation token and removing unknown IDs.
    static func sanitized(_ raw: String, sourceCount: Int) -> String {
        var text = raw
        if let regex = try? NSRegularExpression(pattern: #"\[S(\d+)\]"#) {
            for match in regex.matches(in: text, range: NSRange(text.startIndex..., in: text)).reversed() {
                let ns = text as NSString
                if let value = Int(ns.substring(with: match.range(at: 1))), value > 0, value <= sourceCount { continue }
                text = ns.replacingCharacters(in: match.range, with: "")
            }
        }
        if let range = text.range(of: #"\[S\d*$"#, options: .regularExpression) { text.removeSubrange(range) }
        return text
    }
}

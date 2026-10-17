import Foundation

enum ContinuousQuestionPolicy: String, Codable, CaseIterable, Identifiable {
    case fast, smart, complete
    var id: String { rawValue }
    var label: String {
        switch self { case .fast: return "Fast response"; case .smart: return "Smart merging"; case .complete: return "Complete question first" }
    }
}

/// Local, bounded scheduling. Classification never calls a paid model.
struct QuestionCoordinator {
    struct Candidate: Identifiable {
        let id = UUID()
        let answerID = UUID()
        let sourceID: String?
        var utterance: String
        var baseQuery: String?
        var query: String
        var context: String
        let speaker: Speaker?
        let delegationID: String?
        let trace: PipelineTrace?
        let receivedAt: Date
        var readyAt: Date
    }
    private(set) var pending: [Candidate] = []
    private var recent: [Candidate] = []
    private(set) var droppedCount = 0
    mutating func clear() { pending.removeAll(); recent.removeAll(); droppedCount = 0 }
    mutating func enqueue(query: String, context: String, speaker: Speaker?, delegationID: String?,
                          trace: PipelineTrace?, sourceID: String? = nil, policy: ContinuousQuestionPolicy, now: Date = Date()) {
        recent.removeAll { now.timeIntervalSince($0.receivedAt) > 25 }
        guard !recent.contains(where: { $0.speaker == speaker && Self.key($0.utterance) == Self.key(query) }) else { return }
        if let sourceID, let prior = recent.last(where: { $0.sourceID == sourceID && $0.speaker == speaker }) {
            // A stable segment revision updates only unstarted work, without a second billable request.
            if let index = pending.firstIndex(where: { $0.id == prior.id }) {
                pending[index].query = prior.baseQuery.map { $0 + "\n" + query } ?? query
                pending[index].utterance = query; pending[index].context = context
                if let recentIndex = recent.firstIndex(where: { $0.id == prior.id }) { recent[recentIndex] = pending[index] }
            }
            return
        }
        var item = Candidate(sourceID: sourceID, utterance: query, baseQuery: nil, query: query, context: context, speaker: speaker, delegationID: delegationID,
                             trace: trace, receivedAt: now, readyAt: now.addingTimeInterval(policy == .complete ? 1.2 : 0))
        if policy != .fast, let previous = recent.last, previous.speaker == speaker,
           now.timeIntervalSince(previous.receivedAt) <= (policy == .complete ? 5 : 3),
           Self.related(previous.query, query) {
            item.baseQuery = previous.query
            item.query = String((previous.query + "\n" + query).suffix(6000))
            // Only replace work that has not started. Never cancel a streaming answer.
            pending.removeAll { $0.id == previous.id }
        }
        recent.append(item)
        if pending.count == 3 { pending.removeFirst(); droppedCount += 1 }
        pending.append(item)
    }
    mutating func postponeUntilQuiet(now: Date = Date()) {
        for index in pending.indices { pending[index].readyAt = now.addingTimeInterval(1.2) }
    }
    mutating func take(now: Date = Date()) -> Candidate? {
        let before = pending.count
        pending.removeAll { now.timeIntervalSince($0.receivedAt) > 25 }
        droppedCount += before - pending.count
        guard let first = pending.first, first.readyAt <= now else { return nil }
        return pending.removeFirst()
    }
    static func key(_ text: String) -> String {
        text.lowercased().unicodeScalars.filter { CharacterSet.alphanumerics.contains($0) }.map(String.init).joined()
    }
    /// Conservative continuity cues plus shared content. Ambiguous questions stay separate.
    static func related(_ previous: String, _ next: String) -> Bool {
        let b = next.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        if ["相比", "那它", "它的", "其中", "具体来说", "进一步", "那这个", "为什么这样", "what about its", "how does it", "why is that", "compared to", "and how", "and why"].contains(where: b.hasPrefix) { return true }
        let stop: Set<String> = ["what", "how", "why", "does", "the", "you", "your", "could", "would", "explain", "please", "with", "that", "this", "which", "have", "about"]
        func words(_ s: String) -> Set<String> { Set(s.lowercased().split { !$0.isLetter && !$0.isNumber }.map(String.init).filter { $0.count > 2 && !stop.contains($0) }) }
        return !words(previous).intersection(words(next)).isEmpty
    }
}

import Foundation

@MainActor enum SessionNaming {
    static func request(for session: SessionRecord) -> AnswerRequest {
        var request = AnswerRequest(query: .formulate(question: "Name this session", context: ""), conversation: "", scenario: .meeting, sources: [])
        request.sessionTitleInput = session.namingInput
        return request
    }
    static func clean(_ text: String) -> String? {
        let value = text.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "\"'“”#` "))
        guard !value.isEmpty, !value.contains("\n"), value.count <= 80 else { return nil }
        return value
    }
    static func generate(for session: SessionRecord, provider: any ReasoningProvider, timeout: UInt64 = 30_000_000_000) async throws -> String {
        let operation = Task { @MainActor () throws -> String in
            var text = ""
            for try await delta in provider.stream(request(for: session)) {
                try Task.checkCancellation(); text += delta
                guard text.count <= 400 else { throw CopilotError.message("Invalid session title.") }
            }
            guard let title = clean(text) else { throw CopilotError.message("Invalid session title.") }
            return title
        }
        let timer = Task { try? await Task.sleep(nanoseconds: timeout); if !Task.isCancelled { operation.cancel() } }
        defer { timer.cancel() }
        return try await withTaskCancellationHandler { try await operation.value } onCancel: { operation.cancel() }
    }
}

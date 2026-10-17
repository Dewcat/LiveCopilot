import Foundation

protocol HTTPTransport {
    func data(for request: URLRequest) async throws -> (Data, Int)
    func lines(for request: URLRequest) -> AsyncThrowingStream<String, Error>
}

struct URLSessionTransport: HTTPTransport {
    let session: URLSession
    init(session: URLSession = .shared) { self.session = session }
    func data(for request: URLRequest) async throws -> (Data, Int) {
        let (data, response) = try await session.data(for: request)
        return (data, (response as? HTTPURLResponse)?.statusCode ?? 0)
    }
    func lines(for request: URLRequest) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let (bytes, response) = try await session.bytes(for: request)
                    let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                    if !(200..<300).contains(status) {
                        var errorData = Data()
                        for try await byte in bytes {
                            errorData.append(byte)
                            if errorData.count >= 8192 { break }
                        }
                        try OpenAIHTTP.check(status, data: errorData)
                    }
                    var framer = StreamingLines()
                    for try await byte in bytes {
                        if let line = try framer.consume(byte) {
                            try Task.checkCancellation()
                            continuation.yield(line)
                        }
                    }
                    if let line = try framer.finish() { continuation.yield(line) }
                    continuation.finish()
                } catch { continuation.finish(throwing: error) }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

enum OpenAIHTTP {
    static func request(path: String, key: String, body: [String: Any]) throws -> URLRequest {
        guard !key.isEmpty else { throw CopilotError.message("Add an OpenAI API key in Settings, or launch with OPENAI_API_KEY.") }
        var request = URLRequest(url: URL(string: "https://api.openai.com/v1/\(path)")!)
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        return request
    }
    static func check(_ status: Int, data: Data? = nil) throws {
        guard (200..<300).contains(status) else { throw ServiceHTTPFailure(status: status, data: data) }
    }

}

struct OpenAIEmbeddingProvider: EmbeddingProvider {
    let key: String
    let model: String
    var transport: any HTTPTransport = URLSessionTransport()
    func embed(_ texts: [String]) async throws -> [[Float]] {
        guard !texts.isEmpty else { return [] }
        let request = try OpenAIHTTP.request(path: "embeddings", key: key,
                                             body: ["model": model, "input": texts, "encoding_format": "float"])
        let (data, status) = try await transport.data(for: request)
        try OpenAIHTTP.check(status, data: data)
        struct Response: Decodable {
            struct Item: Decodable { let index: Int; let embedding: [Float] }
            let data: [Item]
        }
        let decoded: Response
        do { decoded = try JSONDecoder().decode(Response.self, from: data) }
        catch { throw CopilotError.message("OpenAI returned malformed embeddings.") }
        let rows = decoded.data.sorted { $0.index < $1.index }
        guard rows.map(\.index) == Array(texts.indices), let dimension = rows.first?.embedding.count,
              dimension > 0, rows.allSatisfy({ $0.embedding.count == dimension && $0.embedding.allSatisfy(\.isFinite) }) else {
            throw CopilotError.message("OpenAI returned missing or incompatible embedding vectors.")
        }
        return rows.map(\.embedding)
    }
}

/// Foundation's AsyncBytes.lines omits empty lines, which destroys SSE event
/// boundaries. Frame the original UTF-8 bytes, preserving LF, CRLF and CR blanks.
struct StreamingLines {
    private var bytes: [UInt8] = []
    private var afterCR = false
    mutating func consume(_ byte: UInt8) throws -> String? {
        if afterCR {
            afterCR = false
            if byte == 10 { return nil }
        }
        if byte == 10 || byte == 13 {
            afterCR = byte == 13
            return try flush()
        }
        guard bytes.count < 1_048_576 else { throw CopilotError.message("Reasoning stream contained an oversized event. Retry this question.") }
        bytes.append(byte)
        return nil
    }
    mutating func finish() throws -> String? { bytes.isEmpty ? nil : try flush() }
    private mutating func flush() throws -> String {
        defer { bytes.removeAll(keepingCapacity: true) }
        guard let text = String(bytes: bytes, encoding: .utf8) else {
            throw CopilotError.message("Reasoning stream contained invalid text encoding. Retry this question.")
        }
        return text
    }
}

/// SSE data is dispatched on the blank lines preserved by StreamingLines.
struct ServerSentEvents {
    private var data: [String] = []
    mutating func consume(_ line: String) -> String? {
        if line.isEmpty {
            defer { data = [] }
            return data.isEmpty ? nil : data.joined(separator: "\n")
        }
        if line.hasPrefix("data:") {
            let payload = String(line.dropFirst(5))
            data.append(payload.hasPrefix(" ") ? String(payload.dropFirst()) : payload)
        }
        return nil
    }
    mutating func finish() -> String? { consume("") }
}

struct OpenAIReasoningProvider: ReasoningProvider {
    let key: String
    let model: String
    var effort = "low"
    var processing = AnalysisProcessing.standard
    var transport: any HTTPTransport = URLSessionTransport()
    func httpRequest(_ request: AnswerRequest) throws -> URLRequest {
        var body: [String: Any] = ["model": model, "instructions": request.instructions,
            "input": request.input, "stream": true, "store": false, "max_output_tokens": 2800]
        let mode = AnalysisModelCatalog.normalized(effort, model: model, service: .separateOpenAI)
        if mode != .modelDefault { body["reasoning"] = ["effort": mode.referenceKey] }
        // Explicit Standard when unchecked; an account-level Fast default must
        // not silently change the price shown by the application.
        body["service_tier"] = processing.wireValue
        return try OpenAIHTTP.request(path: "responses", key: key, body: body)
    }
    func stream(_ request: AnswerRequest) -> AsyncThrowingStream<String, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    let http = try httpRequest(request)
                    var parser = ServerSentEvents(), completed = false, hadText = false
                    var reportedService = false, reportedReasoning = false
                    func handle(_ payload: String) async throws {
                        if payload == "[DONE]" { return }
                        guard let data = payload.data(using: .utf8),
                              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                              let type = obj["type"] as? String else { throw CopilotError.message("Malformed reasoning stream. Retry this question.") }
                        if !reportedService {
                            reportedService = true
                            await request.onStreamProgress?(.firstServiceEvent, ProcessInfo.processInfo.systemUptime)
                        }
                        if !reportedReasoning, type == "response.output_item.added",
                           let item = obj["item"] as? [String: Any], item["type"] as? String == "reasoning" {
                            reportedReasoning = true
                            await request.onStreamProgress?(.reasoningStarted, ProcessInfo.processInfo.systemUptime)
                        }
                        switch type {
                        case "response.output_text.delta", "response.refusal.delta":
                            if let delta = obj["delta"] as? String { hadText = hadText || !delta.isEmpty; continuation.yield(delta) }
                        case "response.completed": completed = true
                        case "response.failed", "error":
                            let failure = (obj["response"] as? [String: Any])?["error"] as? [String: Any] ?? obj["error"] as? [String: Any] ?? obj
                            throw ServiceHTTPFailure(status: 0, data: try? JSONSerialization.data(withJSONObject: failure))
                        case "response.incomplete": throw CopilotError.message("The answer was cut short. Partial text is retained; retry or choose a lower reasoning effort.")
                        default: break
                        }
                    }
                    for try await line in transport.lines(for: http) {
                        try Task.checkCancellation()
                        if let event = parser.consume(line) { try await handle(event) }
                    }
                    if let event = parser.finish() { try await handle(event) }
                    guard completed && hadText else { throw CopilotError.message("Reasoning stream ended without a complete answer. Check the network and retry.") }
                    continuation.finish()
                } catch { continuation.finish(throwing: error) }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }
}

/// One short synthetic input verifies authentication, model access and a usable vector response.
enum EmbeddingConnectionProbe {
    static func run(provider: any EmbeddingProvider) async throws {
        let vectors = try await provider.embed(["Connection test"])
        try Task.checkCancellation()
        guard vectors.count == 1, let vector = vectors.first, !vector.isEmpty,
              vector.allSatisfy(\.isFinite) else {
            throw CopilotError.message("OpenAI returned missing or incompatible embedding vectors.")
        }
    }
}

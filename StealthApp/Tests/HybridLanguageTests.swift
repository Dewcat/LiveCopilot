import XCTest
import SwiftUI
@testable import LiveCopilot

private final class PolicyReasoner: ReasoningProvider, @unchecked Sendable {
    private let lock = NSLock()
    private var values: [AnswerRequest] = []
    var requests: [AnswerRequest] { lock.withLock { values } }
    func stream(_ request: AnswerRequest) -> AsyncThrowingStream<String, Error> {
        lock.withLock { values.append(request) }
        return AsyncThrowingStream { c in c.yield("## Suggested answer\nFixture answer."); c.finish() }
    }
}

final class HybridLanguageTests: XCTestCase {
    @MainActor private func app(_ reasoner: PolicyReasoner) -> AppCoordinator {
        let name = "LiveCopilot-Policy-Tests-" + UUID().uuidString
        let defaults = UserDefaults(suiteName: name)!
        addTeardownBlock { defaults.removePersistentDomain(forName: name) }
        return AppCoordinator(mock: true, layaPredictor: { _, _ in 0.96 }, mockReasoning: reasoner,
                              emitMockConversation: false, mockDefaults: defaults,
                              mockKnowledgeDirectory: FileManager.default.temporaryDirectory.appendingPathComponent(name))
    }
    @MainActor private func settled(_ app: AppCoordinator) async {
        for _ in 0..<100 {
            try? await Task.sleep(nanoseconds: 20_000_000)
            if !app.suggestion.isLoading { return }
        }
        XCTFail("Answer did not settle")
    }
    func testLegacyMigrationAndRoundTrip() throws {
        let old = try JSONDecoder().decode(AppSettings.self, from: Data("{\"language\":\"simplifiedChinese\"}".utf8))
        XCTAssertEqual(old.knowledgeMode, .hybrid); XCTAssertEqual(old.answerLanguage, .auto)
        for language in AnswerLanguage.allCases {
            var value = old; value.answerLanguage = language; value.knowledgeMode = .knowledgeBaseOnly
            let decoded = try JSONDecoder().decode(AppSettings.self, from: JSONEncoder().encode(value))
            XCTAssertEqual(decoded, value)
        }
    }
    func testIndependentQuestionDoesNotRetrievePreviousTopic() {
        let q = RetrievalQuery.formulate(question: "Explain quantum entanglement.", context: "中文简历：项目使用缓存。", previousQuestion: "缓存失效如何处理？")
        XCTAssertFalse(q.semantic.contains("缓存")); XCTAssertFalse(q.lexical.contains("缓存"))
        let follow = RetrievalQuery.formulate(question: "What are its limitations?", context: "Method B has 128 samples.", previousQuestion: "Why choose method B?")
        XCTAssertTrue(follow.semantic.contains("method B")); XCTAssertTrue(follow.lexical.contains("128"))
    }
    @MainActor func testPolicySettingsSurviveCoordinatorRecreation() async {
        let suite = "LiveCopilot-Policy-Restart-" + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(suite)
        let first = AppCoordinator(mock: true, emitMockConversation: false, mockDefaults: defaults, mockKnowledgeDirectory: directory)
        first.settings.answerLanguage = .english
        first.settings.knowledgeMode = .knowledgeBaseOnly
        await first.shutdown()
        let second = AppCoordinator(mock: true, emitMockConversation: false, mockDefaults: UserDefaults(suiteName: suite)!, mockKnowledgeDirectory: directory)
        XCTAssertEqual(second.settings.answerLanguage, .english)
        XCTAssertEqual(second.settings.knowledgeMode, .knowledgeBaseOnly)
        await second.shutdown()
    }
    @MainActor func testExplicitQuestionCannotBypassInvalidLayaResult() async {
        for score in [Double.nan, -0.1, Double.infinity] {
            let suite = "LiveCopilot-Invalid-Laya-" + UUID().uuidString
            let defaults = UserDefaults(suiteName: suite)!
            let reasoner = PolicyReasoner()
            let app = AppCoordinator(mock: true, layaPredictor: { _, _ in score }, mockReasoning: reasoner,
                                     emitMockConversation: false, mockDefaults: defaults,
                                     mockKnowledgeDirectory: FileManager.default.temporaryDirectory.appendingPathComponent(suite))
            app.settings.listeningService = .paraformer; app.settings.automaticSuggestions = true
            await app.start()
            app.receiveMockEvent(.transcript(.init(id: "invalid", speaker: .them, text: "请问什么是二分查找？", startMS: 0, endMS: 1000, receivedAt: Date())), speaker: .them)
            try? await Task.sleep(nanoseconds: 600_000_000)
            XCTAssertTrue(reasoner.requests.isEmpty)
            app.askText("请问什么是二分查找？"); await settled(app)
            XCTAssertEqual(reasoner.requests.count, 1, "Manual fallback must remain available")
            await app.shutdown(); defaults.removePersistentDomain(forName: suite)
        }
    }
    func testLanguagePriorityAndStrictPolicy() {
        var request = AnswerRequest(query: .formulate(question: "请用英文回答：什么是TCP？", context: ""), conversation: "之前用中文回答", scenario: .interview, sources: [])
        XCTAssertTrue(request.instructions.contains("main semantic clause"))
        XCTAssertTrue(request.instructions.contains("Document language and interface language"))
        request.answerLanguage = .english
        XCTAssertTrue(request.instructions.contains("Response language override: English"))
        request.knowledgeMode = .knowledgeBaseOnly
        XCTAssertTrue(request.instructions.contains("Do not fill evidence gaps with general knowledge"))
        XCTAssertFalse(request.instructions.contains("Knowledge mode: HYBRID"))
        XCTAssertTrue(request.instructions.contains("invent the user's experience"))
    }
    func testLocalNoEvidenceLanguageMatchesExplicitRequest() {
        XCTAssertFalse(AnswerLanguage.auto.localFallbackIsChinese(question: "请用英文回答什么是缓存？"))
        XCTAssertTrue(AnswerLanguage.auto.localFallbackIsChinese(question: "Please answer in Chinese: what is caching?"))
        XCTAssertTrue(AnswerLanguage.chinese.localFallbackIsChinese(question: "Please answer in English"))
    }
    @MainActor func testHybridNoHitCallsOneModelAndStrictNoHitCallsNone() async {
        let reasoner = PolicyReasoner()
        let actual = self.app(reasoner)
        actual.includeConversation = false
        actual.askText("What is quantum entanglement?"); await settled(actual)
        XCTAssertEqual(reasoner.requests.count, 1)
        XCTAssertTrue(reasoner.requests[0].sources.isEmpty)
        XCTAssertEqual(reasoner.requests[0].knowledgeMode, .hybrid)
        actual.settings.knowledgeMode = .knowledgeBaseOnly
        actual.settings.answerLanguage = .english
        actual.askText("什么是量子纠缠？"); await settled(actual)
        XCTAssertEqual(reasoner.requests.count, 1)
        XCTAssertTrue(actual.suggestion.text.contains("Knowledge Base Only"))
        XCTAssertNil(actual.suggestion.trace?.milliseconds(.modelRequest))
        await actual.shutdown()
    }
    @MainActor func testManualAndJevShareLanguageAndKnowledgeSnapshotsAcrossTurns() async {
        let reasoner = PolicyReasoner(), app = app(reasoner)
        app.settings.listeningService = .paraformer; app.settings.automaticSuggestions = true
        await app.start()
        for (index, text) in ["请解释什么是缓存？", "Could you explain TCP congestion control?", "Can you explain 缓存失效 in English?"].enumerated() {
            app.receiveMockEvent(.transcript(.init(id: "turn-\(index)", speaker: .them, text: text,
                startMS: index * 6000, endMS: index * 6000 + 1000, receivedAt: Date())), speaker: .them)
            try? await Task.sleep(nanoseconds: 850_000_000)
            await settled(app)
            XCTAssertEqual(reasoner.requests.last?.query.question, text)
            XCTAssertEqual(reasoner.requests.last?.answerLanguage, .auto)
        }
        XCTAssertEqual(reasoner.requests.count, 3, "High-confidence new questions must not wait seven seconds")
        app.settings.answerLanguage = .english
        app.receiveMockEvent(.partialTranscript("请解释一下数据库事务的隔离级别"), speaker: .them)
        app.requestSuggestion(); await settled(app)
        XCTAssertEqual(reasoner.requests.count, 4)
        XCTAssertTrue(reasoner.requests.last?.query.question.contains("隔离级别") == true)
        XCTAssertEqual(reasoner.requests.last?.answerLanguage, .english)
        XCTAssertEqual(reasoner.requests.last?.knowledgeMode, .hybrid)
        await app.shutdown()
    }
    @MainActor func testSettingsSnapshotAndCredentialFreeEmptyLibrary() async {
        let reasoner = PolicyReasoner(), app = app(reasoner)
        app.settings.answerLanguage = .chinese
        app.askText("Explain CPU scheduling.")
        app.settings.answerLanguage = .english
        await settled(app)
        XCTAssertEqual(reasoner.requests.first?.answerLanguage, .chinese)
        XCTAssertNotNil(app.suggestion.trace?.milliseconds(.ragComplete))
        XCTAssertNotNil(app.suggestion.trace?.milliseconds(.firstToken))
        XCTAssertNotNil(app.suggestion.trace?.milliseconds(.answerComplete))
        await app.shutdown()
    }
    @MainActor func testOnlyUsedSourcesAppearAndUnknownStreamedCitationsDisappear() {
        let store = SuggestionStore()
        store.begin()
        store.sources = (1...3).map { n in .init(chunk: .init(id: "\(n)", documentID: "doc", documentName: "Fixture", ordinal: n, page: nil, text: "Synthetic", vector: [], embeddingModel: "mock"), score: 1) }
        store.appendDelta("A fact [S"); XCTAssertFalse(store.text.contains("[S"))
        store.appendDelta("3]. Another [S999"); XCTAssertEqual(store.citedSources.map(\.index), [3])
        store.appendDelta("] and [S0].")
        XCTAssertFalse(store.text.contains("S999")); XCTAssertFalse(store.text.contains("S0"))
        XCTAssertEqual(store.citedSources.first?.source.id, "3")
    }
    func testLowAbsoluteSimilarityDoesNotBecomeEvidenceThroughRRF() async throws {
        let index = try KnowledgeIndex(directory: FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString))
        let doc = KnowledgeDocument(id: "d", name: "Recipe", importedAt: Date(), localPath: "", status: "Ready", chunkCount: 1, embeddingModel: "model")
        try await index.replaceChunks([.init(id: "c", documentID: "d", documentName: "Recipe", ordinal: 0, page: nil, text: "Bake sourdough bread in the oven.", vector: [0.2, 0.98], embeddingModel: "model")], document: doc)
        let sources = try await index.retrieve(query: .formulate(question: "Explain quantum entanglement", context: ""), vector: [1, 0], model: "model", limit: 6)
        XCTAssertTrue(sources.isEmpty)
    }
    func testPCMEndpointUsesAudioClockAndToleratesShortPause() {
        func pcm(_ value: Int16, _ count: Int) -> Data { [Int16](repeating: value, count: count).withUnsafeBytes { Data($0) } }
        var detector = PCMEndpoint()
        XCTAssertTrue(detector.consume(pcm(0, 16000)).isEmpty)
        XCTAssertEqual(detector.consume(pcm(1500, 1600)), [.started])
        XCTAssertTrue(detector.consume(pcm(0, 6400)).isEmpty, "400ms intra-question pause must not commit")
        XCTAssertTrue(detector.consume(pcm(1500, 3200)).isEmpty)
        let events = detector.consume(pcm(0, 12800))
        XCTAssertEqual(events.count, 1); XCTAssertFalse(detector.speaking)
        XCTAssertTrue(detector.consume(pcm(0, 16000)).isEmpty, "Silence must not repeatedly commit")
    }
    func testPlainModelHeadingsKeepTheGeneratedLanguage() {
        let sections = SuggestionParser.sections("Suggested answer:\nAn English answer.\n\nEvidence & notes\nA claim [S1].")
        XCTAssertEqual(sections.map(\.title), ["Suggested answer", "Evidence & notes"])
        XCTAssertEqual(SuggestionParser.sections("建议回答：\n这是中文回答。").first?.title, "建议回答")
        XCTAssertEqual(SuggestionParser.sections("A plain streamed sentence.").first?.title, "")
    }
    func testNewTurnBoundaryAfterAnsweredAndUnansweredCaptions() {
        var conversation = ConversationState()
        let now = Date()
        func append(_ id: String, _ text: String, _ start: Int) {
            _ = conversation.append(.init(id: id, speaker: .them, text: " " + text, startMS: start, endMS: start + 1000, receivedAt: now))
        }
        append("first", "日本的首都是哪里", 0)
        conversation.begin("日本的首都是哪里", speaker: .them, now: now)
        conversation.finish(success: true, question: "日本的首都是哪里")
        append("repeat", "日本的首都是哪里", 3000)
        append("next", "告诉我你的经历", 4300)
        XCTAssertEqual(conversation.candidate(speaker: .them, now: now, cooldown: 0, semanticDetection: true), "告诉我你的经历")
        append("statement", "今天的会议到这里结束", 7500)
        append("indirect", "我不知道日本的首都是哪里", 11000)
        XCTAssertEqual(conversation.candidate(speaker: .them, now: now, cooldown: 0, semanticDetection: true), "我不知道日本的首都是哪里")
        XCTAssertEqual(conversation.fragments.count, 5, "Raw transcript must be preserved")
    }
    func testRollingContextSeparatesHandledHistoryAndCurrentASRRevision() throws {
        var conversation = ConversationState()
        let now = Date()
        func append(_ id: String, _ speaker: Speaker, _ text: String, _ start: Int, _ end: Int) {
            _ = conversation.append(.init(id: id, speaker: speaker, text: text,
                                          startMS: start, endMS: end, receivedAt: now))
        }
        append("question", .them, "介绍一下你的项目", 0, 1000)
        conversation.begin("介绍一下你的项目", speaker: .them, now: now)
        append("answer", .you, "我有三个项目：检索、语音和数据分析。", 1200, 4200)
        append("follow-up", .them, "第一个呢", 4500, 5000)
        let before = conversation.layaContext(speaker: .them, now: now)
        let data = try XCTUnwrap(before.data(using: .utf8))
        let context = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let turns = try XCTUnwrap(context["recentTurns"] as? [[String: Any]])
        XCTAssertEqual(context["currentSpeaker"] as? String, Speaker.them.rawValue)
        XCTAssertEqual(turns.compactMap { $0["text"] as? String }, ["介绍一下你的项目", "我有三个项目：检索、语音和数据分析。"])
        XCTAssertEqual(turns.compactMap { $0["handled"] as? Bool }, [true, false])
        XCTAssertFalse(before.contains("第一个呢"), "Current candidate must not also appear as history")
        append("follow-up", .them, "第一个项目仔细讲一下吧", 4500, 5200)
        XCTAssertEqual(conversation.layaContext(speaker: .them, now: now), before,
                       "Revising current ASR text must not mutate unrelated history")
        XCTAssertEqual(conversation.candidate(speaker: .them, now: now, cooldown: 0, semanticDetection: true), "第一个项目仔细讲一下吧")
        append("answer", .you, "我有三个项目：搜索、语音和数据分析。", 1200, 4300)
        XCTAssertNotEqual(conversation.layaContext(speaker: .them, now: now), before,
                          "A historical ASR revision must reach the semantic model")
    }
    func testRollingContextBoundsTransportButKeepsRawTranscript() throws {
        var conversation = ConversationState()
        let now = Date()
        for i in 0..<100 {
            _ = conversation.append(.init(id: "h\(i)", speaker: .you, text: "\(i):" + String(repeating: "较长的历史发言。", count: 100),
                                          startMS: i * 2000, endMS: i * 2000 + 1000, receivedAt: now))
        }
        _ = conversation.append(.init(id: "current", speaker: .them, text: "那第二个呢", startMS: 201000, endMS: 202000, receivedAt: now))
        let data = Data(conversation.layaContext(speaker: .them, now: now).utf8)
        XCTAssertLessThanOrEqual(data.count, 60_000)
        let value = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let turns = try XCTUnwrap(value["recentTurns"] as? [[String: Any]])
        XCTAssertLessThanOrEqual(turns.count, 80)
        XCTAssertTrue((turns.last?["text"] as? String)?.hasPrefix("99:") == true)
        XCTAssertEqual(conversation.fragments.count, 101, "Model budget must not erase transcript history")
    }
    @MainActor func testSemanticRequestsStillRequireFinalSilenceAndDeduplication() async throws {
        for text in ["日本的首都是哪里", "第一个项目仔细讲一下吧", "第一个呢", "那延迟呢"] {
            let score = 0.95
            var outputs: [String] = []
            let gate = LayaTriggerController(predict: { _, _ in score }, onTrigger: { outputs.append($0.text); return true },
                                             timing: .init(throttle: 0.01, quiet: 0.04))
            gate.configure(enabled: true, cooldown: 0)
            gate.submit(.init(text: text, context: "", speaker: .room, isFinal: false))
            try await Task.sleep(nanoseconds: 80_000_000)
            XCTAssertTrue(outputs.isEmpty)
            gate.setSpeaking(true, speaker: .room)
            gate.submit(.init(text: text, context: "", speaker: .room, isFinal: true))
            try await Task.sleep(nanoseconds: 80_000_000)
            XCTAssertTrue(outputs.isEmpty)
            gate.setSpeaking(false, speaker: .room)
            try await Task.sleep(nanoseconds: 200_000_000)
            XCTAssertEqual(outputs, [text])
            gate.submit(.init(text: text + "？", context: "", speaker: .room, isFinal: true))
            try await Task.sleep(nanoseconds: 80_000_000)
            XCTAssertEqual(outputs, [text])
            gate.reset()
        }
    }
    @MainActor func testContextRevisionRescoresEvenWhenCurrentWordsAreUnchanged() async throws {
        var calls = 0, triggers = 0
        let gate = LayaTriggerController(predict: { _, _ in calls += 1; return 0.97 }, onTrigger: { _ in triggers += 1; return true })
        gate.configure(enabled: true, cooldown: 0)
        gate.submit(.init(text: "Could you explain caching", context: "preview", speaker: .them, isFinal: false))
        try await Task.sleep(nanoseconds: 100_000_000)
        gate.submit(.init(text: "Could you explain caching?", context: "final context", speaker: .them, isFinal: true))
        try await Task.sleep(nanoseconds: 300_000_000)
        XCTAssertEqual(calls, 2); XCTAssertEqual(triggers, 1)
        gate.reset()
    }
    @MainActor func testRenderOverlayForVisualAcceptance() async throws {
        let output = ProcessInfo.processInfo.environment["LIVECOPILOT_UI_ACCEPTANCE"] ?? ""
        guard !output.isEmpty, !output.hasPrefix("$(") else { throw XCTSkip("Opt-in native panel rendering") }
        let root = URL(fileURLWithPath: output)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let app = app(PolicyReasoner())
        app.settings.language = .simplifiedChinese; app.settings.background = .white
        app.settings.answerLanguage = .english; app.settings.knowledgeMode = .hybrid
        app.onboarding.dismissTips()
        let recorded = root.deletingLastPathComponent().appendingPathComponent("real-analysis/analysis-results.json")
        let rows = (try? JSONSerialization.jsonObject(with: Data(contentsOf: recorded)) as? [[String: Any]]) ?? []
        let real = rows.first { $0["case"] as? String == "cn-document-en-answer" }
        app.suggestion.begin(question: real?["question"] as? String ?? "What latency and sample size were measured?")
        app.suggestion.sources = [.init(chunk: .init(id: "cn", documentID: "cn", documentName: "Synthetic-CN.txt", ordinal: 0, page: nil,
            text: "合成项目资料：实验记录命中延迟为42毫秒，样本量128。", vector: [], embeddingModel: "fixture"), score: 1)]
        app.suggestion.appendDelta(real?["answer"] as? String ?? "## Suggested answer\nThe measured latency was 42 ms across 128 samples.\n## Evidence & notes\nMeasured latency and sample size [S1].")
        app.suggestion.finish()
        for width in [400, 560] {
            let host = NSHostingView(rootView: OverlayView(coordinator: app))
            let window = NSWindow(contentRect: NSRect(x: 80, y: 80, width: width, height: 620), styleMask: [.borderless], backing: .buffered, defer: false)
            window.contentView = host; window.orderFrontRegardless()
            try await Task.sleep(nanoseconds: 300_000_000)
            host.layoutSubtreeIfNeeded(); window.display()
            let bounds = host.bounds
            let bitmap = try XCTUnwrap(host.bitmapImageRepForCachingDisplay(in: bounds))
            host.cacheDisplay(in: bounds, to: bitmap)
            let png = try XCTUnwrap(bitmap.representation(using: .png, properties: [:]))
            try png.write(to: root.appendingPathComponent("overlay-\(width).png"))
            XCTAssertEqual(Int(bounds.width), width)
            window.orderOut(nil)
        }
        await app.shutdown()
    }
}

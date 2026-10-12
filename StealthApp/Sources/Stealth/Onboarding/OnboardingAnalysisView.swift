import SwiftUI

struct OnboardingAnalysisView: View {
    @ObservedObject var coordinator: AppCoordinator
    @State private var testTask: Task<Void, Never>?
    @State private var testID = UUID()
    @State private var testing = false
    @State private var failure: OnboardingConnectionFailure?
    @State private var credentialsTop = CGFloat.zero
    @State private var usedScrollShortcut = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private func b(_ en: String, _ zh: String) -> String { ServiceGuide.text(en, zh, coordinator.settings.language) }
    private var locked: Bool { coordinator.isRunning || coordinator.isTransitioning }
    private var shared: Bool { coordinator.settings.reasoningService == .sharedOpenAI }
    private var connectionIdentity: String {
        [coordinator.settings.reasoningService.rawValue, coordinator.settings.analysisModel,
         (try? coordinator.settings.analysisCredentialReference().accountSuffix) ?? "invalid",
         coordinator.settings.reasoningEffort, coordinator.settings.analysisProcessing.rawValue, coordinator.settings.deepSeekEffort,
         coordinator.settings.presetConnection?.thinking.rawValue ?? ""].joined(separator: "|")
    }
    var body: some View {
        GeometryReader { geometry in
            ScrollViewReader { proxy in
                VStack(spacing: 6) {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 14) {
                            OnboardingAnswerConfiguration(coordinator: coordinator).disabled(locked)
                            credentials
                                .id("credentials")
                                .background(GeometryReader { position in
                                    Color.clear.preference(key: AnswerCredentialsPosition.self, value: position.frame(in: .named("answer-scroll")).minY)
                                })
                        }.padding(4)
                    }.coordinateSpace(name: "answer-scroll")
                        .onPreferenceChange(AnswerCredentialsPosition.self) { credentialsTop = $0 }
                    if !usedScrollShortcut && credentialsTop > geometry.size.height - 80 {
                        Button {
                            withAnimation(reduceMotion ? nil : .easeInOut(duration: 0.25)) {
                                usedScrollShortcut = true
                                proxy.scrollTo("credentials", anchor: .top)
                            }
                        } label: {
                            Label(b("Configure your API key", "向下配置 API Key"), systemImage: "arrow.down")
                                .font(.system(size: 11))
                        }.buttonStyle(.plain).foregroundStyle(Color.accentColor)
                            .accessibilityIdentifier("onboarding-view-performance-key")
                    }
                }
            }
        }
        .onChange(of: connectionIdentity) { _, _ in cancelTest() }
        .onChange(of: coordinator.answerCredentialRevision) { _, _ in cancelTest() }
        .onDisappear { cancelTest() }
    }
    private var credentials: some View {
        OnboardingServiceSection(number: 2, title: b("API Key & connection test", "API Key 与连接测试")) {
            if (try? coordinator.settings.analysisCredentialReference()) != nil {
                CredentialEditor(coordinator: coordinator, analysis: !shared, onboarding: true)
                    .id(coordinator.settings.reasoningService.rawValue + "|" + ((try? coordinator.settings.analysisCredentialReference().account) ?? "invalid"))
                    .disabled(locked || testing)
            } else {
                Label(b("Save a valid service address in Connection address first.", "请先在连接地址中保存有效的服务地址。"), systemImage: "info.circle")
                    .font(.callout).foregroundStyle(.secondary)
            }
            Divider()
            HStack(spacing: 10) {
                Button(b("Test connection", "测试连接")) { test() }
                    .disabled(testing || coordinator.isCheckingKey || coordinator.isCheckingAnalysisKey || !coordinator.hasAnswerCredential || coordinator.settings.analysisModel.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || (try? coordinator.settings.analysisCredentialReference()) == nil || locked)
                    .accessibilityIdentifier("onboarding-test-connection")
                if testing {
                    ProgressView().controlSize(.small)
                    Button(b("Cancel", "取消")) { cancelTest() }
                }
            }
            OnboardingConnectionFeedback(language: coordinator.settings.language, testing: testing,
                                         verified: coordinator.isAnalysisConnectionVerified,
                                         saved: coordinator.hasAnswerCredential, mock: coordinator.isMock, failure: failure)
            Text(b("Testing sends one short example question, without your conversation or documents, and may incur API charges.", "测试仅发送一条简短示例问题，不附带对话或资料，可能产生 API 费用。"))
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
        }
    }
    private func cancelTest() {
        testID = UUID(); testTask?.cancel(); testTask = nil
        testing = false; failure = nil
    }
    private func test() {
        cancelTest(); testing = true
        let id = testID
        testTask = Task {
            do {
                try await coordinator.testAnalysisConnection()
                guard !Task.isCancelled, testID == id else { return }
            } catch {
                guard !Task.isCancelled, testID == id else { return }
                failure = .classify(error)
            }
            if testID == id { testing = false; testTask = nil }
        }
    }
}

private struct AnswerCredentialsPosition: PreferenceKey {
    static var defaultValue = CGFloat.zero
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = nextValue() }
}

struct OnboardingConnectionFeedback: View {
    let language: AppLanguage
    let testing: Bool
    let verified: Bool
    let saved: Bool
    var mock = false
    var failure: OnboardingConnectionFailure?
    private func b(_ en: String, _ zh: String) -> String { ServiceGuide.text(en, zh, language) }
    private var success: Bool { verified && !testing && failure == nil }
    private var title: String {
        if testing { return b("Testing connection…", "正在测试连接…") }
        if let failure { return failure.title(language) }
        if verified { return mock ? b("Preview test passed · no API call", "预览测试通过 · 未调用 API") : b("Connection verified · ready to continue", "连接测试成功 · 可以继续") }
        return saved ? b("Key saved · connection not yet verified", "密钥已保存 · 连接待测试") : b("Not configured · you can set up later", "尚未配置 · 可以稍后设置")
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Label(title, systemImage: success ? "checkmark.circle.fill" : failure != nil ? "exclamationmark.circle" : "info.circle")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(success ? Color.green : failure != nil ? Color.orange : Color.secondary)
            if let failure { Text(failure.detail(language)).font(.caption).foregroundStyle(.secondary) }
        }.fixedSize(horizontal: false, vertical: true).accessibilityIdentifier("onboarding-connection-result")
    }
}

struct OnboardingServiceSection<Content: View>: View {
    let number: Int
    let title: String
    @ViewBuilder let content: () -> Content
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Text(String(number)).font(.system(size: 11, weight: .semibold)).foregroundStyle(Color.accentColor)
                    .frame(width: 21, height: 21).background(Color.accentColor.opacity(0.09), in: Circle())
                    .accessibilityHidden(true)
                Text(title).font(.system(size: 14, weight: .semibold))
            }
            content()
        }.padding(14).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .windowBackgroundColor).opacity(0.72), in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).strokeBorder(Color.primary.opacity(0.045)))
            .accessibilityElement(children: .contain)
    }
}

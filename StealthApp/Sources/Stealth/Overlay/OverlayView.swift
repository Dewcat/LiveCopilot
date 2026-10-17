import SwiftUI

struct OverlayView: View {
    @ObservedObject var coordinator: AppCoordinator
    @ObservedObject var transcript: TranscriptStore
    @ObservedObject var hotkeys: HotkeyStore
    @ObservedObject var onboarding: OnboardingStore
    @State private var query = ""
    @State private var followTranscript = true
    @State private var chromeHeight: CGFloat = 368
    @State private var answerContentHeight: CGFloat = 56
    var onContentHeight: (CGFloat) -> Void
    var onMinimumHeight: (CGFloat) -> Void
    init(coordinator: AppCoordinator, onContentHeight: @escaping (CGFloat) -> Void = { _ in }, onMinimumHeight: @escaping (CGFloat) -> Void = { _ in }) {
        self.coordinator = coordinator; transcript = coordinator.transcript; hotkeys = coordinator.hotkeys
        onboarding = coordinator.onboarding
        self.onContentHeight = onContentHeight; self.onMinimumHeight = onMinimumHeight
    }
    private func b(_ en: String, _ zh: String) -> String { ServiceGuide.text(en, zh, coordinator.settings.language) }
    private func t(_ text: String) -> String { L10n.text(text, language: coordinator.settings.language) }
    private var transcriptSize: CGFloat { OverlayTypography.clamped(coordinator.settings.transcriptFontSize, fallback: 12) }
    private var answerSize: CGFloat { OverlayTypography.clamped(coordinator.settings.answerFontSize, fallback: 14) }
    private var speakerWidth: CGFloat { max(35, transcriptSize * 2.8) }
    private func reportSize() {
        // Only the answer viewport grows. The voice area and composer keep
        // their position relative to the window's stable top edge.
        let fixedHeight = chromeHeight + 10 + 28 // inter-pane spacing and outer padding
        onMinimumHeight(fixedHeight + 56)
        onContentHeight(fixedHeight + max(56, answerContentHeight))
    }
    var body: some View {
        GeometryReader { geometry in
            VStack(alignment: .leading, spacing: 10) {
                VStack(alignment: .leading, spacing: 10) {
                    top.frame(height: 120, alignment: .top)
                    if let step = onboarding.visibleTip {
                        OverlayFirstUseTip(step: step, coordinator: coordinator)
                    }
                    transcriptView.frame(height: 90)
                    Divider()
                    actions.frame(height: 28)
                    bottom.frame(height: 78, alignment: .top)
                    Divider()
                }
                .fixedSize(horizontal: false, vertical: true)
                .background(GeometryReader { measured in
                    Color.clear.preference(key: OverlayChromeHeightKey.self, value: measured.size.height)
                })
                ConversationFlowView(coordinator: coordinator, fontSize: answerSize, onContentHeight: { height in
                    guard height.isFinite, height > 0, abs(height - answerContentHeight) > 0.5 else { return }
                    answerContentHeight = height
                    reportSize()
                })
                .frame(maxHeight: .infinity)
            }
            .padding(14)
            .frame(width: geometry.size.width, height: geometry.size.height, alignment: .topLeading)
        }
        .background { WindowBackgroundView(style: coordinator.settings.background, isOverlay: true) }
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .preferredColorScheme(coordinator.settings.background.usesLightAppearance ? .light : nil)
        .environment(\.locale, coordinator.settings.language.locale)
        .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(.primary.opacity(0.12)))
        .overlay(alignment: .bottomTrailing) { resizeHandle }
        .onChange(of: coordinator.conversationGeneration) { _, _ in
            query = ""; followTranscript = true
            reportSize()
        }
        .onPreferenceChange(OverlayChromeHeightKey.self) { height in
            guard height > 0, abs(height - chromeHeight) > 0.5 else { return }
            chromeHeight = height
            reportSize()
        }
        .onAppear { reportSize() }
    }
    private var top: some View {
        VStack(alignment: .leading, spacing: 10) {
            header.padding(.trailing, 16)
            Text(t(coordinator.statusMessage)).font(.caption).foregroundStyle(.secondary).lineLimit(2).textSelection(.enabled)
            if coordinator.isRunning {
                HStack {
                    Text(t(coordinator.questionState)).font(.caption2).foregroundStyle(.secondary)
                    Spacer()
                    Toggle(t("Auto"), isOn: $coordinator.settings.automaticSuggestions)
                        .toggleStyle(OverlaySwitchStyle()).accessibilityIdentifier("automatic-suggestions")
                }
                if coordinator.settings.automaticSuggestions,
                   coordinator.settings.listeningService.isLocal {
                    Text(coordinator.layaLastScore.map {
                        String(format: "Laya %@ %.2f / %@ %.2f", t("Latest score"), $0,
                               t("Threshold"), coordinator.settings.layaThreshold)
                    } ?? String(format: "Laya %@ · %@ %.2f", t("Waiting for a decision"),
                                       t("Threshold"), coordinator.settings.layaThreshold))
                        .font(.caption2.monospacedDigit()).foregroundStyle(.secondary)
                        .lineLimit(1).frame(height: 16, alignment: .leading)
                }
                if coordinator.settings.listeningService == .apple {
                    Text(t("Apple ASR uses one language. For mixed Chinese/English, select another speech recognition engine in Services."))
                        .font(.caption2).foregroundStyle(.secondary).lineLimit(1)
                        .help(t("Apple ASR uses one language. For mixed Chinese/English, select another speech recognition engine in Services."))
                }
            }
        }
    }
    private var actions: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                ForEach(coordinator.settings.enabledSuggestionModes) { mode in
                    Button { coordinator.requestSuggestion(mode: mode) } label: { Label(t(mode.label), systemImage: mode.systemImage).font(.caption) }
                        .help(hotkeys.combo(for: mode).display).accessibilityIdentifier("action-" + mode.rawValue)
                        .onboardingHighlight(onboarding.visibleTip == .answer && mode == .reply)
                }
                Spacer(minLength: 4)
                Menu {
                    Picker(t("Answer language"), selection: $coordinator.settings.answerLanguage) {
                        ForEach(AnswerLanguage.allCases) { language in Text(language.label).tag(language) }
                    }.pickerStyle(.inline)
                } label: {
                    Label(coordinator.settings.answerLanguage.label, systemImage: "globe")
                        .font(.caption)
                }.fixedSize().help(t("Answer language"))
                    .accessibilityIdentifier("answer-language")
            }
        }
    }
    private var bottom: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .center) {
                TextField(t("Ask anything — listening can be off"), text: $query, axis: .vertical)
                    .textFieldStyle(.roundedBorder).lineLimit(1).frame(height: 28)
                    .onSubmit { submit() }.accessibilityIdentifier("manual-query")
                    .onboardingHighlight(onboarding.visibleTip == .start && onboarding.state.prefersTyping)
                Button(t("Ask")) { submit() }.disabled(query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            HStack {
                Toggle(t("Use recent conversation"), isOn: $coordinator.includeConversation).font(.caption2).toggleStyle(OverlaySwitchStyle())
                Spacer(minLength: 4)
                Menu {
                    Picker(t("Knowledge mode"), selection: $coordinator.settings.knowledgeMode) {
                        ForEach(KnowledgeMode.allCases) { mode in Text(t(mode.label)).tag(mode) }
                    }.pickerStyle(.inline)
                } label: {
                    Text(t(coordinator.settings.knowledgeMode == .hybrid ? "Hybrid" : "KB Only")).font(.caption2)
                }.fixedSize().help(t(coordinator.settings.knowledgeMode.label))
                    .accessibilityIdentifier("knowledge-mode")
                if coordinator.answerIsRunning { Button(t("Cancel")) { coordinator.cancelAnswer() }.font(.caption) }
            }
            footer.padding(.trailing, 20)
        }
    }
    private func submit() { let value = query; query = ""; coordinator.askText(value) }
    private var header: some View {
        HStack {
            HStack {
                AppBrandTitle(iconSize: 22)
                if coordinator.isMock { Text(t("MOCK")).font(.caption2.bold()).foregroundStyle(.orange) }
                Spacer(minLength: 0)
            }.overlay { OverlayDragRegion() }
                .help(b("Turn off automatic docking to drag this header anywhere.", "关闭自动贴边后，可拖动这里自由移动窗口。"))
            Button { Task { await coordinator.toggle() } } label: {
                Image(systemName: coordinator.isRunning ? "stop.circle.fill" : "play.circle.fill")
                    .foregroundStyle(coordinator.isRunning ? Color.red : .green)
            }.disabled(coordinator.isTransitioning).help(t(coordinator.isRunning ? "Stop listening" : "Start listening"))
                .accessibilityIdentifier("overlay-toggle-listening")
                .onboardingHighlight(onboarding.visibleTip == .start && !onboarding.state.prefersTyping)
            Button { Task { await coordinator.resetConversation() } } label: { Image(systemName: "arrow.clockwise") }
                .disabled(coordinator.isTransitioning)
                .help(t("Clear conversation and answers; keep listening if active"))
                .accessibilityLabel(t("Start fresh")).accessibilityIdentifier("reset-conversation")
            Button { coordinator.toggleMic() } label: { Image(systemName: coordinator.micEnabled ? "mic.fill" : "mic.slash") }
                .disabled(coordinator.isTransitioning).help(t("Toggle your microphone in Remote Meeting mode"))
            Button { coordinator.onOpenSettings?() } label: { Image(systemName: "gearshape") }.help(t("Settings and knowledge base"))
                .onboardingHighlight(onboarding.visibleTip == .captureExclusion)
            Button { coordinator.settings.overlayEdgeHide.toggle() } label: {
                Image(systemName: coordinator.settings.overlayEdgeHide ? "pin" : "pin.fill")
                    .foregroundStyle(coordinator.settings.overlayEdgeHide ? Color.secondary : .blue)
            }.help(coordinator.settings.overlayEdgeHide
                   ? b("Turn off automatic docking · drag freely", "关闭自动贴边 · 自由拖动")
                   : b("Turn on automatic docking", "开启自动贴边"))
                .accessibilityIdentifier("overlay-pin")
                .onboardingHighlight(onboarding.visibleTip == .visibility)
            Button { (NSApp.windows.first(where: { $0 is OverlayWindow }) as? OverlayWindow)?.tuckAway() } label: { Image(systemName: "minus") }
                .help(t("Hide ({shortcut})").replacingOccurrences(of: "{shortcut}", with: hotkeys.toggleOverlay.display))
        }.buttonStyle(.borderless)
    }
    private var transcriptView: some View {
        ScrollViewReader { proxy in
            VStack(spacing: 2) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 6) {
                        if !transcript.hasContent { Text(t("Conversation appears here when listening.")).font(.caption).foregroundStyle(.secondary) }
                        ForEach(transcript.lines) { line in
                            HStack(alignment: .top, spacing: 6) {
                                Text(t(line.speaker.rawValue)).font(.system(size: max(11, transcriptSize - 1), weight: .bold)).foregroundStyle(line.speaker == .you ? Color.blue : .green).frame(width: speakerWidth, alignment: .leading)
                                Text(line.content).font(.system(size: transcriptSize)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                        if !transcript.partialThem.isEmpty {
                            partialRow(transcript.partialThem, speaker: coordinator.settings.mode == .inPerson ? .room : .them)
                        }
                        if !transcript.partialYou.isEmpty { partialRow(transcript.partialYou, speaker: .you) }
                        Color.clear.frame(height: 1).id("latest")
                    }
                }.onChange(of: transcript.lines) { _, _ in if followTranscript { proxy.scrollTo("latest", anchor: .bottom) } }
                    .onChange(of: transcript.partialThem) { _, _ in if followTranscript { proxy.scrollTo("latest", anchor: .bottom) } }
                    .onChange(of: transcript.partialYou) { _, _ in if followTranscript { proxy.scrollTo("latest", anchor: .bottom) } }
                Toggle(t("Follow transcript"), isOn: $followTranscript).font(.caption2).toggleStyle(OverlaySwitchStyle()).frame(maxWidth: .infinity, alignment: .trailing)
            }
        }
    }
    private func partialRow(_ text: String, speaker: Speaker) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Text(t(speaker.rawValue)).font(.system(size: max(11, transcriptSize - 1), weight: .bold)).foregroundStyle(speaker == .you ? Color.blue : .green).frame(width: speakerWidth, alignment: .leading)
            Text(text).font(.system(size: transcriptSize)).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
        }.accessibilityLabel(t("Recognizing") + " · " + t(speaker.rawValue) + " · " + text)
    }
    private var footer: some View {
        HStack {
            Text(t(coordinator.settings.scenario.rawValue)).font(.caption2).foregroundStyle(.secondary)
            Spacer()
            Text(hotkeys.toggleOverlay.display).font(.caption2).foregroundStyle(.tertiary)
                .onboardingHighlight(onboarding.visibleTip == .visibility)
        }
    }
    private var resizeHandle: some View {
        Image(systemName: "arrow.up.left.and.arrow.down.right")
            .font(.system(size: 11, weight: .medium)).foregroundStyle(.secondary)
            .frame(width: 28, height: 28)
            .help(t("Drag any edge or corner to resize"))
            .allowsHitTesting(false) // The native border owns all eight resize directions.
    }
}

/// Native switches lose their on-state color when this nonactivating panel is in the background.
/// Draw the state explicitly while retaining Toggle's accessibility and Button's keyboard behavior.
private struct OverlaySwitchStyle: ToggleStyle {
    @Environment(\.isEnabled) private var isEnabled
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func makeBody(configuration: Configuration) -> some View {
        Button { configuration.isOn.toggle() } label: {
            HStack(spacing: 8) {
                configuration.label
                Capsule()
                    .fill(configuration.isOn ? Color.blue : Color.primary.opacity(0.18))
                    .overlay(alignment: configuration.isOn ? .trailing : .leading) {
                        Circle().fill(.white)
                            .shadow(color: .black.opacity(0.18), radius: 1, y: 1)
                            .frame(width: 14, height: 14).padding(2)
                    }
                    .frame(width: 32, height: 18)
            }
            .padding(.vertical, 4)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .opacity(isEnabled ? 1 : 0.45)
        .animation(reduceMotion ? nil : .easeInOut(duration: 0.12), value: configuration.isOn)
        .accessibilityRepresentation {
            Toggle(isOn: configuration.$isOn) { configuration.label }.toggleStyle(.switch)
        }
    }
}

private struct OverlayChromeHeightKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) { value = max(value, nextValue()) }
}

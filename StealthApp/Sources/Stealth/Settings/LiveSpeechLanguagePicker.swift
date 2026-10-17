import SwiftUI

/// Shared by setup and settings so language guidance stays identical in both places.
struct LiveSpeechLanguagePicker: View {
    @Binding var language: LiveSpeechLanguage
    let interfaceLanguage: AppLanguage
    var compact = false
    private func b(_ en: String, _ zh: String) -> String { ServiceGuide.text(en, zh, interfaceLanguage) }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Picker(compact ? b("Language", "识别语言") : b("Recognition language preference", "识别语言偏好"), selection: $language) {
                Text(b("Chinese + English", "中英混合")).tag(LiveSpeechLanguage.mixed)
                Text(b("Mandarin Chinese", "普通话")).tag(LiveSpeechLanguage.chinese)
                Text(b("English", "英语")).tag(LiveSpeechLanguage.english)
                Text(b("Any language", "不限语言")).tag(LiveSpeechLanguage.unrestricted)
            }.accessibilityIdentifier("live-speech-language")
            if !compact { Text(b("The first three options guide GPT-Live-1 without locking its language. Any language sends no language hint. Changes apply when you next start listening.", "前三项提供语言偏好，不会锁定语言。“不限语言”不发送语言提示，由模型根据音频判断，下次开始监听时生效。"))
                .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
        }
    }
}

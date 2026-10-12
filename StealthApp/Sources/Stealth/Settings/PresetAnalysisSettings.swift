import SwiftUI

/// Presets use the same live configuration and source data as onboarding.
struct PresetAnalysisSettings: View {
    @ObservedObject var coordinator: AppCoordinator
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            OnboardingAnswerConfiguration(coordinator: coordinator)
            CredentialEditor(coordinator: coordinator, analysis: true)
                .id(try? coordinator.settings.analysisCredentialReference().account)
        }
    }
}

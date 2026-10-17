import Foundation

/// Opt-in real-worker replay. Synthetic speech-end/final events; never captures audio or calls an answer API.
@main struct JevLatencyAudit {
    @MainActor static func main() async throws {
        guard CommandLine.arguments.count == 4 else {
            throw CopilotError.message("Usage: JevLatencyAudit <installation> <LayaRuntime resources> <output.json>")
        }
        let installation = URL(fileURLWithPath: CommandLine.arguments[1])
        let resources = URL(fileURLWithPath: CommandLine.arguments[2])
        let worker = LayaWorker(installation: installation, resources: resources)
        defer { worker.stop() }
        let cold = ProcessInfo.processInfo.systemUptime
        try await worker.prepare()
        let readyMS = (ProcessInfo.processInfo.systemUptime - cold) * 1000
        let samples = [
            ("mixed", "请解释 React 的 useEffect 和 Vue watch 有什么区别？"),
            ("short", "为什么？"),
            ("long", String(repeating: "我们需要考虑数据库扩展、缓存失效与故障恢复。", count: 35) + "请说明你会如何设计这个系统？"),
            ("followup", "那你会如何验证这个优化没有引入新的问题？"),
            ("unfinished", "I would like to ask you about"),
            ("statement", "The meeting starts tomorrow at nine.")
        ]
        var rows: [[String: Any]] = []
        for _ in 0..<3 {
            for (id, text) in samples {
                let start = ProcessInfo.processInfo.systemUptime
                var score: Double?
                var inferenceMS: Double?
                var triggeredMS: Double?
                var failed = false
                var completed = false
                let gate = LayaTriggerController(predict: { text, context in
                    let begin = ProcessInfo.processInfo.systemUptime
                    let highest = try await worker.predict(text: text, context: context)
                    inferenceMS = (ProcessInfo.processInfo.systemUptime - begin) * 1000
                    return highest
                }, onTrigger: { _ in
                    triggeredMS = (ProcessInfo.processInfo.systemUptime - start) * 1000
                    completed = true
                    return true
                })
                gate.onDecision = { score = $0 }
                gate.onError = { _ in failed = true; completed = true }
                gate.configure(enabled: true, threshold: 0.8, cooldown: 7)
                gate.setSpeaking(true, speaker: .them)
                gate.setSpeaking(false, speaker: .them)
                // Fixed synthetic ASR-final delay, held identical across runtime versions.
                try await Task.sleep(nanoseconds: 150_000_000)
                gate.submit(.init(text: text, context: "Earlier synthetic conversation.", speaker: .them, isFinal: true))
                var scoreAt: Double?
                while !completed && ProcessInfo.processInfo.systemUptime - start < 20 {
                    if score != nil && scoreAt == nil { scoreAt = ProcessInfo.processInfo.systemUptime }
                    if let scoreAt, ProcessInfo.processInfo.systemUptime - scoreAt > 0.7 { break }
                    try await Task.sleep(nanoseconds: 5_000_000)
                }
                failed = failed || score == nil
                rows.append(["id": id, "score": score as Any? ?? NSNull(), "decision_ms": inferenceMS as Any? ?? NSNull(),
                             "speech_end_to_trigger_ms": triggeredMS as Any? ?? NSNull(), "failed": failed,
                             "triggered": triggeredMS != nil])
                gate.reset()
            }
        }
        let output: [String: Any] = ["cold_process_to_ready_ms": readyMS, "synthetic_asr_final_delay_ms": 150, "rows": rows]
        let data = try JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: URL(fileURLWithPath: CommandLine.arguments[3]))
        print("Audit complete: \(rows.count) synthetic replays")
    }
}

import SwiftUI

/// Fixed decimal-aligned cells. Updating during a crossfade starts from the
/// current composite, so rapid model changes cannot flash an obsolete value.
struct NumericBlurTransition {
    static let duration = 0.25
    static let stagger = 0.03
    static let radius = 2.4
    struct Glyph {
        let character: Character
        let opacity: Double
        let blur: Double
    }
    struct Cell {
        var target: Character?
        var outgoing: [Glyph] = []
        var start: TimeInterval = -.infinity

        func glyphs(at time: TimeInterval) -> [Glyph] {
            let progress = NumericBlurTransition.easeOut((time - start) / NumericBlurTransition.duration)
            var result = outgoing.compactMap { glyph -> Glyph? in
                let opacity = glyph.opacity * (1 - progress)
                guard opacity > 0.001 else { return nil }
                return Glyph(character: glyph.character, opacity: opacity,
                             blur: glyph.blur + (NumericBlurTransition.radius - glyph.blur) * progress)
            }
            if let target, progress > 0 {
                result.append(Glyph(character: target, opacity: progress, blur: NumericBlurTransition.radius * (1 - progress)))
            }
            return result
        }
    }
    private(set) var cells: [Cell]
    init(_ slots: [Character?]) { cells = slots.map { Cell(target: $0) } }

    mutating func update(_ slots: [Character?], at time: TimeInterval, reduceMotion: Bool) {
        guard cells.count == slots.count, !reduceMotion else {
            cells = slots.map { Cell(target: $0) }; return
        }
        var changed = 0
        for index in slots.indices where cells[index].target != slots[index] {
            let visible = cells[index].glyphs(at: time)
            cells[index] = Cell(target: slots[index], outgoing: visible,
                                start: time + Double(changed) * Self.stagger)
            changed += 1
        }
    }
    func isActive(at time: TimeInterval) -> Bool { cells.contains { time < $0.start + Self.duration } }

    // CSS/SwiftUI ease-out: cubic Bézier (0, 0, 0.58, 1).
    static func easeOut(_ fraction: Double) -> Double {
        if fraction <= 0 { return 0 }
        if fraction >= 1 { return 1 }
        var low = 0.0, high = 1.0
        for _ in 0..<18 {
            let t = (low + high) / 2
            let x = 3 * (1 - t) * t * t * 0.58 + t * t * t
            if x < fraction { low = t } else { high = t }
        }
        let t = (low + high) / 2
        return 3 * (1 - t) * t * t + t * t * t
    }

    static func slots(_ number: String, integerPlaces: Int) -> [Character?] {
        let parts = number.split(separator: ".", omittingEmptySubsequences: false)
        let whole = Array(parts.first.map(String.init) ?? "")
        let fraction = parts.count > 1 ? Array(parts[1]) : []
        return Array(repeating: nil, count: max(0, integerPlaces - whole.count)) + whole.map(Optional.some) +
            (parts.count > 1 ? [Character(".")] + fraction.map(Optional.some) : [])
    }
}

struct StaggeredBlurNumber: View {
    let number: String
    let prefix: String
    let suffix: String
    let size: CGFloat
    let integerPlaces: Int
    let leadingAligned: Bool
    let compactWidth: Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var transition: NumericBlurTransition
    @State private var animating = false
    @State private var revision = 0

    init(_ number: String, prefix: String = "", suffix: String = "", size: CGFloat, integerPlaces: Int = 3, leadingAligned: Bool = false, compactWidth: Bool = false) {
        self.number = number; self.prefix = prefix; self.suffix = suffix
        self.compactWidth = compactWidth
        self.size = size; self.integerPlaces = integerPlaces; self.leadingAligned = leadingAligned
        _transition = State(initialValue: NumericBlurTransition(NumericBlurTransition.slots(number, integerPlaces: integerPlaces)))
    }
    var body: some View {
        TimelineView(.animation(paused: !animating || reduceMotion)) { clock in
            // Reserve the same outer width, but keep the visible value and its
            // currency tight against the left edge instead of leading blank digits.
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text(prefix + reservedNumber + suffix).hidden()
            }.overlay(alignment: .leading) {
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text(prefix)
                ForEach(visibleIndices, id: \.self) { index in
                    // Hidden Text supplies an invariant width, height and baseline.
                    Text(transition.cells[index].target == "." ? "." : "0").hidden()
                        .overlay {
                            let glyphs = transition.cells[index].glyphs(at: clock.date.timeIntervalSinceReferenceDate)
                            ZStack {
                                ForEach(glyphs.indices, id: \.self) { glyph in
                                    Text(String(glyphs[glyph].character))
                                        .blur(radius: glyphs[glyph].blur)
                                        .opacity(glyphs[glyph].opacity)
                                }
                            }
                        }
                }
                Text(suffix)
            }.fixedSize()
            }
        }
        .font(.system(size: size, weight: .semibold)).monospacedDigit()
        .fixedSize()
        .transaction { $0.animation = nil }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(prefix + number + suffix)
        .onChange(of: number) { _, _ in change() }
        .onChange(of: reduceMotion) { _, _ in change() }
        .task(id: revision) {
            guard animating else { return }
            let end = transition.cells.map { $0.start + NumericBlurTransition.duration }.max() ?? 0
            let remaining = max(0, end - Date.timeIntervalSinceReferenceDate)
            do { try await Task.sleep(for: .seconds(remaining)) } catch { return }
            guard !Task.isCancelled else { return }
            transition = NumericBlurTransition(NumericBlurTransition.slots(number, integerPlaces: integerPlaces))
            animating = false
        }
    }
    private var reservedNumber: String {
        let parts = number.split(separator: ".", omittingEmptySubsequences: false)
        return String(repeating: "0", count: compactWidth ? (parts.first?.count ?? 0) : max(integerPlaces, parts.first?.count ?? 0)) +
            (parts.count > 1 ? "." + String(repeating: "0", count: parts[1].count) : "")
    }
    private var visibleIndices: Range<Int> {
        let first = leadingAligned ? (transition.cells.firstIndex { $0.target != nil } ?? 0) : 0
        return first..<transition.cells.count
    }
    private func change() {
        let time = Date.timeIntervalSinceReferenceDate
        transition.update(NumericBlurTransition.slots(number, integerPlaces: integerPlaces), at: time, reduceMotion: reduceMotion)
        animating = transition.isActive(at: time)
        revision += 1
    }
}

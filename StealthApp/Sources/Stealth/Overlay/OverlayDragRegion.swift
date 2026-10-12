import AppKit
import SwiftUI

/// A dedicated title drag region avoids SwiftUI controls swallowing background drags.
/// It excludes the header buttons and leaves content selection and resize handles intact.
struct OverlayDragRegion: NSViewRepresentable {
    func makeNSView(context: Context) -> OverlayHeaderDragView { OverlayHeaderDragView() }
    func updateNSView(_ nsView: OverlayHeaderDragView, context: Context) {}
}

final class OverlayHeaderDragView: NSView {
    override var mouseDownCanMoveWindow: Bool { false }
    override func mouseDown(with event: NSEvent) {
        guard let overlay = window as? OverlayWindow, !overlay.edgeHide else { return }
        overlay.performDrag(with: event)
    }
}

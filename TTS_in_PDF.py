#!/usr/bin/env python3
"""
Zen Reader Pro — Immersive PDF Reader with TTS
================================================
A distraction-free, high-performance PDF reader built with PyQt6.
Features: glassmorphic UI, smooth animations, TTS (offline + edge),
highlighting, sketching, floating notes, search, thumbnails, focus mode.

Dependencies:
    pip install PyQt6 PyMuPDF edge-tts pygame sounddevice sherpa-onnx keyboard
"""

import sys
import os
import time
import tempfile
import asyncio
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass

# ── Third-party ──
import fitz  # PyMuPDF
import edge_tts
import pygame
import sounddevice as sd

try:
    import sherpa_onnx
    HAS_SHERPA = True
except ImportError:
    HAS_SHERPA = False

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# ── PyQt6 ──
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QScrollArea, QFileDialog, QColorDialog,
    QTextEdit, QFrame, QComboBox, QGraphicsDropShadowEffect, QSizePolicy,
    QSpacerItem, QGraphicsOpacityEffect, QStackedWidget, QLineEdit,
    QProgressBar, QSplitter, QGridLayout, QToolButton, QDialog,
    QDialogButtonBox, QScrollBar, QAbstractItemView
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPoint, QPointF, QRect, QRectF, QPropertyAnimation,
    QEasingCurve, QObject, QTimer, QSize, QParallelAnimationGroup,
    QSequentialAnimationGroup, pyqtSlot
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QPen, QPainterPath, QKeySequence,
    QShortcut, QFont, QCursor, QLinearGradient, QPalette, QFontMetrics,
    QMouseEvent, QWheelEvent, QKeyEvent, QPaintEvent
)

# ═════════════════════════════════════════════════════════════
#  DESIGN SYSTEM
# ═════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class D:
    """Design tokens — deep, minimal, high-tech."""
    BG_DEEP: str        = "#060608"
    BG_SURFACE: str     = "#0E0E12"
    BG_ELEVATED: str    = "#15151A"
    BG_HOVER: str       = "#1C1C22"
    BG_ACTIVE: str      = "#24242C"
    BORDER_SUBTLE: str  = "#25252E"
    BORDER_FOCUS: str   = "#3E3E4C"
    TEXT_PRIMARY: str   = "#F0F0F5"
    TEXT_SECONDARY: str = "#A0A0B0"
    TEXT_MUTED: str     = "#606070"
    TEXT_DIM: str       = "#404050"
    ACCENT: str         = "#5EEAD4"
    ACCENT_DIM: str     = "#14B8A630"
    ACCENT_GLOW: str    = "#5EEAD420"
    WARNING: str        = "#FBBF24"
    ERROR: str          = "#F87171"
    HIGHLIGHT: str      = "#FDE68A"

    RADIUS_SM: int  = 6
    RADIUS_MD: int  = 10
    RADIUS_LG: int  = 14
    RADIUS_XL: int  = 18

    DUR_FAST: int   = 150
    DUR_NORMAL: int = 280
    DUR_SLOW: int   = 450

    FONT: str = "Inter, SF Pro Display, Segoe UI, system-ui, sans-serif"


EDGE_VOICES = {
    "Aria · US Female":   "en-US-AriaNeural",
    "Guy · US Male":      "en-US-GuyNeural",
    "Jenny · US Female":  "en-US-JennyNeural",
    "Sonia · UK Female":  "en-GB-SoniaNeural",
    "Neerja · IN Female": "en-IN-NeerjaExpressiveNeural",
    "Prabhat · IN Male":  "en-IN-PrabhatNeural",
}


def stylesheet() -> str:
    t = D()
    return f"""
    QMainWindow, QWidget {{
        background-color: {t.BG_DEEP};
        color: {t.TEXT_PRIMARY};
        font-family: '{t.FONT}';
        font-size: 13px;
        border: none; outline: none;
    }}
    QLabel {{ background: transparent; border: none; }}

    QPushButton {{
        background: transparent;
        color: {t.TEXT_SECONDARY};
        border: 1px solid transparent;
        border-radius: {t.RADIUS_SM}px;
        padding: 6px 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{ background: {t.BG_HOVER}; color: {t.TEXT_PRIMARY}; }}
    QPushButton:pressed {{ background: {t.BG_ACTIVE}; color: {t.TEXT_PRIMARY}; }}
    QPushButton:checked {{
        background: {t.ACCENT_DIM};
        color: {t.ACCENT};
        border: 1px solid {t.ACCENT_DIM};
    }}

    QToolButton {{
        background: transparent; color: {t.TEXT_SECONDARY};
        border: none; border-radius: {t.RADIUS_SM}px; padding: 4px;
    }}
    QToolButton:hover {{ background: {t.BG_HOVER}; color: {t.TEXT_PRIMARY}; }}

    QComboBox {{
        background: {t.BG_ELEVATED};
        color: {t.TEXT_PRIMARY};
        border: 1px solid {t.BORDER_SUBTLE};
        border-radius: {t.RADIUS_MD}px;
        padding: 5px 10px;
        min-width: 160px;
    }}
    QComboBox:hover {{ border-color: {t.BORDER_FOCUS}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {t.TEXT_MUTED};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {t.BG_ELEVATED};
        border: 1px solid {t.BORDER_SUBTLE};
        border-radius: {t.RADIUS_MD}px;
        padding: 4px;
        selection-background-color: {t.ACCENT_DIM};
        selection-color: {t.ACCENT};
        outline: none;
    }}

    QSlider::groove:horizontal {{
        height: 3px; background: {t.BORDER_SUBTLE}; border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {t.ACCENT}; border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {t.TEXT_PRIMARY}; width: 14px; height: 14px;
        margin: -6px 0; border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{ background: {t.ACCENT}; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{
        background: transparent; width: 6px; margin: 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.BORDER_SUBTLE}; border-radius: 3px; min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t.BORDER_FOCUS}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; border: none; }}
    QScrollBar:horizontal {{ height: 6px; background: transparent; }}
    QScrollBar::handle:horizontal {{
        background: {t.BORDER_SUBTLE}; border-radius: 3px; min-width: 40px;
    }}

    QTextEdit {{
        background: {t.BG_DEEP}; color: {t.TEXT_PRIMARY};
        border: 1px solid {t.BORDER_SUBTLE}; border-radius: {t.RADIUS_SM}px;
        padding: 8px; selection-background-color: {t.ACCENT_DIM};
    }}
    QLineEdit {{
        background: {t.BG_SURFACE}; color: {t.TEXT_PRIMARY};
        border: 1px solid {t.BORDER_SUBTLE}; border-radius: {t.RADIUS_SM}px;
        padding: 6px 10px;
    }}
    QLineEdit:focus {{ border-color: {t.BORDER_FOCUS}; }}
    """


# ═════════════════════════════════════════════════════════════
#  ANIMATION UTILITIES
# ═════════════════════════════════════════════════════════════

class Anim:
    """Fluent animation builder."""
    @staticmethod
    def fade(w, start: float, end: float, dur: int = D.DUR_NORMAL):
        eff = w.graphicsEffect()
        if not isinstance(eff, QGraphicsOpacityEffect):
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
        a = QPropertyAnimation(eff, b"opacity", w)
        a.setDuration(dur)
        a.setStartValue(start)
        a.setEndValue(end)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start()
        return a

    @staticmethod
    def slide_y(w, start: int, end: int, dur: int = D.DUR_NORMAL):
        a = QPropertyAnimation(w, b"pos", w)
        a.setDuration(dur)
        a.setStartValue(QPoint(w.x(), start))
        a.setEndValue(QPoint(w.x(), end))
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start()
        return a

    @staticmethod
    def grow(w, start: QSize, end: QSize, dur: int = D.DUR_FAST):
        a = QPropertyAnimation(w, b"size", w)
        a.setDuration(dur)
        a.setStartValue(start)
        a.setEndValue(end)
        a.setEasingCurve(QEasingCurve.Type.OutExpo)
        a.start()
        return a


# ═════════════════════════════════════════════════════════════
#  BASE CLASSES
# ═════════════════════════════════════════════════════════════

class IconBtn(QPushButton):
    """Minimal icon button for dense toolbars."""
    def __init__(self, icon: str, tip: str, checkable: bool = False, parent=None):
        super().__init__(icon, parent)
        self.setToolTip(tip)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {D.TEXT_SECONDARY};
                border: none; border-radius: {D.RADIUS_SM}px;
                font-size: 14px; padding: 0px;
            }}
            QPushButton:hover {{ background: {D.BG_HOVER}; color: {D.TEXT_PRIMARY}; }}
            QPushButton:pressed {{ background: {D.BG_ACTIVE}; }}
            QPushButton:checked {{
                background: {D.ACCENT_DIM}; color: {D.ACCENT}; border: none;
            }}
        """)


class GlassFrame(QFrame):
    """Semi-transparent elevated surface with subtle border."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            GlassFrame {{
                background: rgba(21,21,26,0.88);
                border: 1px solid {D.BORDER_SUBTLE};
                border-radius: {D.RADIUS_LG}px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)


# ═════════════════════════════════════════════════════════════
#  TOAST NOTIFICATION
# ═════════════════════════════════════════════════════════════

class Toast(QFrame):
    """Elegant, non-intrusive transient notification."""
    def __init__(self, text: str, parent=None, duration_ms: int = 2000):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background: {D.BG_ELEVATED};
                border: 1px solid {D.BORDER_FOCUS};
                border-radius: {D.RADIUS_MD}px;
            }}
            QLabel {{ color: {D.TEXT_PRIMARY}; font-size: 12px; padding: 10px 18px; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        self.adjustSize()

        if parent:
            r = parent.rect()
            self.move(r.center().x() - self.width()//2, r.bottom() - self.height() - 100)

        # Fade in
        self._op = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._op)
        self._op.setOpacity(0.0)

        a = QPropertyAnimation(self._op, b"opacity", self)
        a.setDuration(250)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start()

        QTimer.singleShot(duration_ms, self._fade_out)
        self._anim = a

    def _fade_out(self):
        a = QPropertyAnimation(self._op, b"opacity", self)
        a.setDuration(300)
        a.setStartValue(1.0)
        a.setEndValue(0.0)
        a.finished.connect(self.close)
        a.setEasingCurve(QEasingCurve.Type.InCubic)
        a.start()


# ═════════════════════════════════════════════════════════════
#  FLOATING NOTES
# ═════════════════════════════════════════════════════════════

class TextNote(QFrame):
    """Collapsible, draggable text note."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.offset = QPoint()
        self.collapsed = QSize(36, 36)
        self.expanded = QSize(260, 180)
        self.resize(self.collapsed)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(21,21,26,0.95);
                border: 1px solid {D.ACCENT_DIM};
                border-radius: {D.RADIUS_MD}px;
            }}
            QTextEdit {{
                background: {D.BG_DEEP}; color: {D.TEXT_PRIMARY};
                border: 1px solid {D.BORDER_SUBTLE}; border-radius: {D.RADIUS_SM}px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        self.icon = QLabel("✎")
        self.icon.setStyleSheet(f"color: {D.WARNING}; font-size: 13px;")
        self.title = QLabel("Note")
        self.title.setStyleSheet(f"color: {D.TEXT_PRIMARY}; font-weight: 600; font-size: 11px;")
        self.title.hide()
        hdr.addWidget(self.icon)
        hdr.addWidget(self.title)
        hdr.addStretch()
        lay.addLayout(hdr)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write your thought…")
        self.editor.hide()
        lay.addWidget(self.editor)

        self._anim = QPropertyAnimation(self, b"size", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        self._anim.setDuration(200)

    def enterEvent(self, e):
        self.title.show()
        self.editor.show()
        self._anim.stop()
        self._anim.setEndValue(self.expanded)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self.editor.hasFocus():
            self.title.hide()
            self.editor.hide()
            self._anim.stop()
            self._anim.setEndValue(self.collapsed)
            self._anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = e.pos()

    def mouseMoveEvent(self, e):
        if self.dragging:
            self.move(self.mapToParent(e.pos() - self.offset))

    def mouseReleaseEvent(self, e):
        self.dragging = False


class SketchNote(QFrame):
    """Collapsible, draggable sketch pad."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.drawing = False
        self.offset = QPoint()
        self.last_point = QPoint()
        self.collapsed = QSize(36, 36)
        self.expanded = QSize(260, 220)
        self.resize(self.collapsed)
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(21,21,26,0.95);
                border: 1px solid {D.ACCENT_DIM};
                border-radius: {D.RADIUS_MD}px;
            }}
            QPushButton {{
                background: {D.BG_HOVER}; color: {D.TEXT_PRIMARY};
                border-radius: 4px; padding: 2px 8px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {D.ACCENT_DIM}; color: {D.ACCENT}; }}
        """)

        self.canvas = QPixmap(240, 170)
        self.canvas.fill(QColor(D.BG_DEEP))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        self.icon = QLabel("✦")
        self.icon.setStyleSheet(f"color: {D.ACCENT}; font-size: 13px;")
        self.title = QLabel("Sketch")
        self.title.setStyleSheet(f"color: {D.TEXT_PRIMARY}; font-weight: 600; font-size: 11px;")
        self.title.hide()
        self.btn_clr = QPushButton("Clear")
        self.btn_clr.clicked.connect(self._clear)
        self.btn_clr.hide()
        hdr.addWidget(self.icon)
        hdr.addWidget(self.title)
        hdr.addStretch()
        hdr.addWidget(self.btn_clr)
        lay.addLayout(hdr)

        self.lbl = QLabel()
        self.lbl.setPixmap(self.canvas)
        self.lbl.hide()
        lay.addWidget(self.lbl)

        self._anim = QPropertyAnimation(self, b"size", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        self._anim.setDuration(200)

    def _clear(self):
        self.canvas.fill(QColor(D.BG_DEEP))
        self.lbl.setPixmap(self.canvas)

    def enterEvent(self, e):
        self.title.show()
        self.btn_clr.show()
        self.lbl.show()
        self._anim.stop()
        self._anim.setEndValue(self.expanded)
        self._anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.title.hide()
        self.btn_clr.hide()
        self.lbl.hide()
        self._anim.stop()
        self._anim.setEndValue(self.collapsed)
        self._anim.start()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if e.pos().y() < 30:
                self.dragging = True
                self.offset = e.pos()
            else:
                self.drawing = True
                self.last_point = self.lbl.mapFrom(self, e.pos())

    def mouseMoveEvent(self, e):
        if self.dragging:
            self.move(self.mapToParent(e.pos() - self.offset))
        elif self.drawing:
            cur = self.lbl.mapFrom(self, e.pos())
            p = QPainter(self.canvas)
            p.setPen(QPen(QColor(D.ACCENT), 2.2, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawLine(self.last_point, cur)
            p.end()
            self.last_point = cur
            self.lbl.setPixmap(self.canvas)

    def mouseReleaseEvent(self, e):
        self.dragging = False
        self.drawing = False


# ═════════════════════════════════════════════════════════════
#  INTERACTIVE PDF SURFACE
# ═════════════════════════════════════════════════════════════

class PDFSurface(QLabel):
    """Handles mouse interaction: zoom, highlight, pencil, erase."""
    eraseRequested = pyqtSignal(QPoint)

    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self.drawing = False
        self.highlighting = False
        self.current_path: Optional[QPainterPath] = None
        self.hl_start = QPoint()
        self.hl_end = QPoint()
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, e: QWheelEvent):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            pos = e.position().toPoint()
            delta = e.angleDelta().y() / 1200.0
            new_zoom = max(0.4, min(4.0, self.app.zoom + delta))
            if new_zoom != self.app.zoom:
                self.app.zoom_toward(pos, new_zoom)
            e.accept()
        else:
            e.ignore()

    def mousePressEvent(self, e: QMouseEvent):
        pos = e.pos()
        if e.button() == Qt.MouseButton.LeftButton:
            if self.app.pencil_mode:
                self.drawing = True
                fp = QPointF(float(pos.x()), float(pos.y()))
                self.current_path = QPainterPath(fp)
                self.app.pencil_add(fp, start=True)
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif self.app.highlight_mode:
                self.highlighting = True
                self.hl_start = pos
                self.hl_end = pos
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif e.button() == Qt.MouseButton.RightButton:
            self.eraseRequested.emit(pos)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QMouseEvent):
        pos = e.pos()
        if self.drawing and self.app.pencil_mode:
            fp = QPointF(float(pos.x()), float(pos.y()))
            self.current_path.lineTo(fp)
            self.app.pencil_add(fp, start=False)
        elif self.highlighting and self.app.highlight_mode:
            self.hl_end = pos
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self.drawing:
            self.drawing = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif self.highlighting:
            self.highlighting = False
            rect = QRect(self.hl_start, self.hl_end).normalized()
            if rect.width() > 4 and rect.height() > 4:
                self.app.highlight_add(rect)
            self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)
        if self.highlighting and self.app.highlight_mode:
            p = QPainter(self)
            p.setBrush(QColor(253, 230, 138, 70))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRect(self.hl_start, self.hl_end).normalized())


# ═════════════════════════════════════════════════════════════
#  RENDER WORKER
# ═════════════════════════════════════════════════════════════

class RenderJob:
    __slots__ = ("doc", "page_idx", "zoom", "highlights", "pencil", "sentence")
    def __init__(self, doc, page_idx, zoom, highlights, pencil, sentence):
        self.doc = doc
        self.page_idx = page_idx
        self.zoom = zoom
        self.highlights = highlights
        self.pencil = pencil
        self.sentence = sentence


class RenderWorker(QThread):
    pageReady = pyqtSignal(int, float, QPixmap)

    def __init__(self):
        super().__init__()
        self._running = True
        self._job: Optional[RenderJob] = None
        self._mutex = False

    def set_job(self, job: RenderJob):
        while self._mutex:
            time.sleep(0.001)
        self._job = job

    def run(self):
        while self._running:
            time.sleep(0.008)
            if self._job is None or self._mutex:
                continue
            self._mutex = True
            job = self._job
            self._job = None
            try:
                page = job.doc.load_page(job.page_idx)
                mat = fitz.Matrix(job.zoom, job.zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                             QImage.Format.Format_RGB888).copy()
                base = QPixmap.fromImage(img)

                painter = QPainter(base)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

                # User highlights
                if job.page_idx in job.highlights:
                    painter.setPen(Qt.PenStyle.NoPen)
                    for rect, color in job.highlights[job.page_idx]:
                        painter.setBrush(QColor(color))
                        zr = QRectF(
                            rect.x() * job.zoom, rect.y() * job.zoom,
                            rect.width() * job.zoom, rect.height() * job.zoom
                        )
                        painter.drawRoundedRect(zr, 3, 3)

                # Pencil strokes
                if job.page_idx in job.pencil:
                    for path in job.pencil[job.page_idx]:
                        painter.save()
                        painter.setPen(QPen(QColor(D.ACCENT), 2.4 * job.zoom,
                                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                            Qt.PenJoinStyle.RoundJoin))
                        t = painter.transform()
                        t.scale(job.zoom, job.zoom)
                        painter.setTransform(t)
                        painter.drawPath(path)
                        painter.restore()

                # TTS sentence highlight
                if job.sentence:
                    painter.setBrush(QColor(94, 234, 212, 60))
                    painter.setPen(Qt.PenStyle.NoPen)
                    s = job.sentence.strip()
                    rects = page.search_for(s)
                    if not rects and len(s) > 20:
                        rects = page.search_for(s[:20])
                    for r in rects:
                        painter.drawRect(QRectF(
                            r.x0 * job.zoom, r.y0 * job.zoom,
                            (r.x1 - r.x0) * job.zoom, (r.y1 - r.y0) * job.zoom
                        ))

                painter.end()
                self.pageReady.emit(job.page_idx, job.zoom, base)
            except Exception as e:
                print(f"Render error: {e}")
            self._mutex = False

    def stop(self):
        self._running = False
        self.wait(1000)


# ═════════════════════════════════════════════════════════════
#  TTS WORKER
# ═════════════════════════════════════════════════════════════

class TTSWorker(QThread):
    sentenceStarted = pyqtSignal(int, str)
    pageFinished = pyqtSignal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.sentences: List[str] = []
        self.idx = 0
        self.speed = 1.0
        self.voice = "Offline · Piper VITS (Amy)"
        self._stop = False

    def load(self, text: str, speed: float, voice: str):
        clean = re.sub(r'\s+', ' ', text).strip()
        self.sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
        self.idx = 0
        self.speed = speed
        self.voice = voice
        self._stop = False

    def run(self):
        while self.idx < len(self.sentences) and not self._stop:
            sent = self.sentences[self.idx].strip()
            if sent:
                self.sentenceStarted.emit(self.idx, sent)
                try:
                    if self.voice in EDGE_VOICES:
                        vid = EDGE_VOICES[self.voice]
                        rate_pct = int((self.speed - 1.0) * 100)
                        rate_str = f"{rate_pct:+d}%"
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                        asyncio.run(edge_tts.Communicate(sent, vid, rate=rate_str).save(tmp))
                        pygame.mixer.music.load(tmp)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and not self._stop:
                            time.sleep(0.03)
                        pygame.mixer.music.unload()
                        try:
                            os.remove(tmp)
                        except Exception:
                            pass
                    else:
                        if self.engine:
                            audio = self.engine.generate(sent, speed=self.speed)
                            sd.play(audio.samples, samplerate=audio.sample_rate)
                            sd.wait()
                except Exception as e:
                    print(f"TTS skip: {e}")
            if not self._stop:
                self.idx += 1
        if not self._stop:
            self.pageFinished.emit()

    def stop(self):
        self._stop = True
        try:
            sd.stop()
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass
        self.wait()


# ═════════════════════════════════════════════════════════════
#  THUMBNAIL SIDEBAR
# ═════════════════════════════════════════════════════════════

class ThumbnailItem(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, page_num: int, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.page_num = page_num
        self.setFixedSize(120, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            ThumbnailItem {{
                background: {D.BG_SURFACE};
                border: 1px solid {D.BORDER_SUBTLE};
                border-radius: {D.RADIUS_SM}px;
            }}
            ThumbnailItem:hover {{
                background: {D.BG_HOVER};
                border-color: {D.BORDER_FOCUS};
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        lbl = QLabel()
        lbl.setPixmap(pixmap.scaled(110, 140, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                    Qt.TransformationMode.SmoothTransformation))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)

        num = QLabel(f"{page_num + 1}")
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(f"color: {D.TEXT_MUTED}; font-size: 10px;")
        lay.addWidget(num)

    def mousePressEvent(self, e):
        self.clicked.emit(self.page_num)


class ThumbnailSidebar(QScrollArea):
    pageSelected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(140)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"""
            QScrollArea {{ background: {D.BG_SURFACE}; border: none; }}
        """)
        self.container = QWidget()
        self.lay = QVBoxLayout(self.container)
        self.lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.lay.setSpacing(8)
        self.lay.setContentsMargins(8, 12, 8, 12)
        self.setWidget(self.container)
        self.items: List[ThumbnailItem] = []

    def load_document(self, doc):
        for item in self.items:
            item.deleteLater()
        self.items.clear()

        if not doc:
            return

        for i in range(min(len(doc), 50)):
            try:
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
                img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                             QImage.Format.Format_RGB888).copy()
                pm = QPixmap.fromImage(img)
                item = ThumbnailItem(i, pm, self.container)
                item.clicked.connect(self.pageSelected.emit)
                self.lay.addWidget(item)
                self.items.append(item)
            except Exception:
                pass

    def set_active(self, idx: int):
        for item in self.items:
            if item.page_num == idx:
                item.setStyleSheet(f"""
                    ThumbnailItem {{
                        background: {D.BG_HOVER};
                        border: 1px solid {D.ACCENT};
                        border-radius: {D.RADIUS_SM}px;
                    }}
                """)
            else:
                item.setStyleSheet(f"""
                    ThumbnailItem {{
                        background: {D.BG_SURFACE};
                        border: 1px solid {D.BORDER_SUBTLE};
                        border-radius: {D.RADIUS_SM}px;
                    }}
                    ThumbnailItem:hover {{
                        background: {D.BG_HOVER};
                        border-color: {D.BORDER_FOCUS};
                    }}
                """)


# ═════════════════════════════════════════════════════════════
#  SEARCH OVERLAY
# ═════════════════════════════════════════════════════════════

class SearchOverlay(GlassFrame):
    searchRequested = pyqtSignal(str)
    nextRequested = pyqtSignal()
    prevRequested = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(360)
        self.setFixedHeight(56)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Search in document…")
        self.input.returnPressed.connect(self._search)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: {D.BG_DEEP}; color: {D.TEXT_PRIMARY};
                border: 1px solid {D.BORDER_SUBTLE}; border-radius: {D.RADIUS_SM}px;
                padding: 6px 10px;
            }}
        """)
        lay.addWidget(self.input, 1)

        self.btn_prev = IconBtn("◀", "Previous result")
        self.btn_prev.clicked.connect(self.prevRequested.emit)
        lay.addWidget(self.btn_prev)

        self.btn_next = IconBtn("▶", "Next result")
        self.btn_next.clicked.connect(self.nextRequested.emit)
        lay.addWidget(self.btn_next)

        self.btn_close = IconBtn("✕", "Close search")
        self.btn_close.clicked.connect(self._close)
        lay.addWidget(self.btn_close)

        self._anim = None

    def _search(self):
        text = self.input.text().strip()
        if text:
            self.searchRequested.emit(text)

    def showEvent(self, e):
        super().showEvent(e)
        self.input.setFocus()
        self.input.selectAll()
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(D.DUR_NORMAL)
        self._anim.setStartValue(QPoint(self.x(), -self.height()))
        self._anim.setEndValue(QPoint(self.x(), 80))
        self._anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        self._anim.start()

    def _close(self):
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(D.DUR_FAST)
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(self.x(), -self.height()))
        self._anim.finished.connect(self.hide)
        self._anim.finished.connect(self.closed.emit)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.start()


# ═════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═════════════════════════════════════════════════════════════

class ZenReaderPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zen Reader Pro")
        self.resize(1400, 900)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(stylesheet())

        # ── Audio init ──
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception as e:
            print(f"Audio init: {e}")

        # ── TTS engine ──
        self.tts_engine = None
        self._init_default_tts()

        self.tts_worker = TTSWorker(self.tts_engine)
        self.tts_worker.sentenceStarted.connect(self.on_sentence)
        self.tts_worker.pageFinished.connect(self.on_page_done)

        # ── Render worker ──
        self.renderer = RenderWorker()
        self.renderer.pageReady.connect(self.on_render_ready)
        self.renderer.start()

        # ── State ──
        self.doc = None
        self.page = 0
        self.zoom = 1.6
        self.active_color = QColor(253, 230, 138, 100)
        self.highlight_mode = False
        self.pencil_mode = False
        self.highlights: Dict[int, List[Tuple[QRectF, QColor]]] = {}
        self.pencil: Dict[int, List[QPainterPath]] = {}
        self.sentence_text = ""
        self._pending_job: Optional[RenderJob] = None
        self._last_pixmap: Optional[QPixmap] = None

        self._focus_mode = False
        self._toolbar_visible = True
        self._search_results: List[Tuple[int, QRectF]] = []
        self._search_idx = -1

        # ── UI ──
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_global_hotkey()

        # ── Entrance animation ──
        self.setWindowOpacity(0.0)
        a = QPropertyAnimation(self, b"windowOpacity", self)
        a.setDuration(500)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start()

        # ── Auto-hide timer ──
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._try_hide_toolbar)

    # ───────────────────────── UI SETUP ─────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Thumbnail sidebar ──
        self.sidebar = ThumbnailSidebar(self)
        self.sidebar.pageSelected.connect(self.goto_page)
        self.sidebar.hide()
        root.addWidget(self.sidebar)

        # ── Main content ──
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)
        root.addWidget(content, 1)

        # ── Floating Toolbar ──
        self.toolbar = GlassFrame(self)
        self.toolbar.setFixedHeight(52)

        tb = QHBoxLayout(self.toolbar)
        tb.setContentsMargins(14, 6, 14, 6)
        tb.setSpacing(6)

        self.btn_open = IconBtn("⌘", "Open PDF (Ctrl+O)")
        self.btn_open.clicked.connect(self.open_pdf)

        self.btn_play = IconBtn("▷", "Play / Pause (Space)")
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_stop = IconBtn("□", "Stop (S)")
        self.btn_stop.clicked.connect(self.stop_reading)

        self.combo_voice = QComboBox()
        self.combo_voice.addItems(["Offline · Piper VITS (Amy)"] + list(EDGE_VOICES.keys()))
        self.combo_voice.setToolTip("Voice")
        self.combo_voice.setFixedWidth(180)
        self.combo_voice.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.btn_load_voice = IconBtn("＋", "Load custom voice model")
        self.btn_load_voice.clicked.connect(self.load_custom_voice)

        self.btn_color = IconBtn("◐", "Highlight color")
        self.btn_color.clicked.connect(self.pick_color)

        self.btn_hl = IconBtn("▤", "Toggle highlighter (H)", checkable=True)
        self.btn_hl.clicked.connect(self.toggle_highlight)

        self.btn_pen = IconBtn("✎", "Toggle pencil (P)", checkable=True)
        self.btn_pen.clicked.connect(self.toggle_pencil)

        self.btn_note = IconBtn("✚", "Add note (N)")
        self.btn_note.clicked.connect(self.add_note)

        self.btn_sketch = IconBtn("✦", "Add sketch (K)")
        self.btn_sketch.clicked.connect(self.add_sketch)

        self.btn_search = IconBtn("🔍", "Search (Ctrl+F)")
        self.btn_search.clicked.connect(self.toggle_search)

        self.btn_sidebar = IconBtn("☰", "Toggle sidebar (Ctrl+B)")
        self.btn_sidebar.clicked.connect(self.toggle_sidebar)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(5, 25)
        self.slider_speed.setValue(10)
        self.slider_speed.setFixedWidth(100)
        self.slider_speed.setToolTip("Speed")
        self.lbl_speed = QLabel("1.0×")
        self.lbl_speed.setStyleSheet(f"color: {D.TEXT_MUTED}; font-size: 11px; min-width: 32px;")
        self.slider_speed.valueChanged.connect(lambda v: self.lbl_speed.setText(f"{v/10.0:.1f}×"))

        self.btn_focus = IconBtn("◑", "Focus mode (F)")
        self.btn_focus.clicked.connect(self.toggle_focus)

        # Add to toolbar
        tb.addWidget(self.btn_open)
        tb.addWidget(self.btn_play)
        tb.addWidget(self.btn_stop)
        tb.addSpacing(8)
        tb.addWidget(self.combo_voice)
        tb.addWidget(self.btn_load_voice)
        tb.addSpacing(8)
        tb.addWidget(self.btn_color)
        tb.addWidget(self.btn_hl)
        tb.addWidget(self.btn_pen)
        tb.addWidget(self.btn_note)
        tb.addWidget(self.btn_sketch)
        tb.addWidget(self.btn_search)
        tb.addWidget(self.btn_sidebar)
        tb.addSpacing(8)
        tb.addWidget(self.lbl_speed)
        tb.addWidget(self.slider_speed)
        tb.addStretch()
        tb.addWidget(self.btn_focus)

        self.toolbar.adjustSize()
        self.toolbar.raise_()

        # ── Search overlay ──
        self.search_overlay = SearchOverlay(self)
        self.search_overlay.hide()
        self.search_overlay.searchRequested.connect(self.do_search)
        self.search_overlay.nextRequested.connect(self.search_next)
        self.search_overlay.prevRequested.connect(self.search_prev)
        self.search_overlay.closed.connect(self.clear_search)

        # ── PDF Scroll Area ──
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.pdf = PDFSurface(self)
        self.pdf.setText("Open a PDF to begin.\n\n"
                        "Space · play/pause    ←/→ · pages    Ctrl+scroll · zoom\n"
                        "F · focus mode    F11 · fullscreen    Ctrl+F · search\n"
                        "Alt+S · read selected text anywhere")
        self.pdf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pdf.setStyleSheet(f"color: {D.TEXT_MUTED}; font-size: 14px; padding: 60px;")
        self.scroll.setWidget(self.pdf)
        content_lay.addWidget(self.scroll, 1)

        # ── Status Bar ──
        self.status = QFrame(self)
        self.status.setStyleSheet("background: transparent;")
        sb = QHBoxLayout(self.status)
        sb.setContentsMargins(24, 6, 24, 12)
        sb.setSpacing(16)

        self.lbl_info = QLabel("No document")
        self.lbl_info.setStyleSheet(f"color: {D.TEXT_MUTED}; font-size: 11px;")

        self.lbl_zoom = QLabel("")
        self.lbl_zoom.setStyleSheet(f"color: {D.TEXT_MUTED}; font-size: 11px;")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(2)
        self.progress.setFixedWidth(120)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {D.BORDER_SUBTLE}; border: none; border-radius: 1px; }}
            QProgressBar::chunk {{ background: {D.ACCENT}; border-radius: 1px; }}
        """)

        sb.addWidget(self.lbl_info)
        sb.addStretch()
        sb.addWidget(self.progress)
        sb.addWidget(self.lbl_zoom)
        self.status.adjustSize()
        self.status.raise_()

        self._reposition_floating()

    def _reposition_floating(self):
        tw = self.toolbar.width()
        self.toolbar.move((self.width() - tw) // 2, 18)
        if self.search_overlay.isVisible():
            sw = self.search_overlay.width()
            self.search_overlay.move((self.width() - sw) // 2, self.toolbar.y() + self.toolbar.height() + 10)
        sw = self.status.width()
        sh = self.status.height()
        self.status.move((self.width() - sw) // 2, self.height() - sh - 10)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reposition_floating()

    # ─────────────────── TOOLBAR AUTO-HIDE ───────────────────
    def _try_hide_toolbar(self):
        if self._focus_mode and not self.toolbar.underMouse():
            self._set_toolbar_visible(False)

    def _set_toolbar_visible(self, visible: bool):
        if visible == self._toolbar_visible:
            return
        self._toolbar_visible = visible
        end_y = 18 if visible else -(self.toolbar.height() + 30)
        Anim.slide_y(self.toolbar, self.toolbar.y(), end_y, D.DUR_NORMAL)
        if not visible:
            self.search_overlay.hide()

    def _show_toolbar(self):
        self._hide_timer.stop()
        if not self._toolbar_visible:
            self._set_toolbar_visible(True)
        if self._focus_mode:
            self._hide_timer.start(3000)

    def mouseMoveEvent(self, e):
        if e.position().y() < 90:
            self._show_toolbar()
        super().mouseMoveEvent(e)

    # ─────────────────── SHORTCUTS ───────────────────
    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Right"), self, self.next_page)
        QShortcut(QKeySequence("Left"), self, self.prev_page)
        QShortcut(QKeySequence("Space"), self, self.toggle_play)
        QShortcut(QKeySequence("S"), self, self.stop_reading)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_pdf)
        QShortcut(QKeySequence("H"), self, lambda: self.btn_hl.click())
        QShortcut(QKeySequence("P"), self, lambda: self.btn_pen.click())
        QShortcut(QKeySequence("N"), self, self.add_note)
        QShortcut(QKeySequence("K"), self, self.add_sketch)
        QShortcut(QKeySequence("F"), self, self.toggle_focus)
        QShortcut(QKeySequence("Ctrl++"), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)
        QShortcut(QKeySequence("Ctrl+F"), self, self.toggle_search)
        QShortcut(QKeySequence("Ctrl+B"), self, self.toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+G"), self, self.jump_page)
        QShortcut(QKeySequence("Escape"), self, self._esc_handler)

    def _esc_handler(self):
        if self.search_overlay.isVisible():
            self.search_overlay._close()
        elif self._focus_mode:
            self.toggle_focus()

    # ─────────────────── TTS INIT ───────────────────
    def _init_default_tts(self):
        if not HAS_SHERPA:
            return
        base = self._base_path()
        model = os.path.join(base, "vits-piper-en_US-amy-low", "en_US-amy-low.onnx")
        tokens = os.path.join(base, "vits-piper-en_US-amy-low", "tokens.txt")
        data = os.path.join(base, "vits-piper-en_US-amy-low", "espeak-ng-data")
        if os.path.exists(model) and os.path.exists(tokens):
            try:
                cfg = sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                            model=model, tokens=tokens, data_dir=data
                        )
                    )
                )
                self.tts_engine = sherpa_onnx.OfflineTts(cfg)
            except Exception as e:
                print(f"TTS init: {e}")

    def _base_path(self):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.abspath(os.path.dirname(__file__))

    # ─────────────────── PDF I/O ───────────────────
    def open_pdf(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if fn:
            try:
                self.doc = fitz.open(fn)
                self.page = 0
                self.highlights.clear()
                self.pencil.clear()
                self.sentence_text = ""
                self._last_pixmap = None
                self.sidebar.load_document(self.doc)
                self.sidebar.show()
                self.sidebar.set_active(0)
                self.render()
                self._toast(f"Loaded · {len(self.doc)} pages")
            except Exception as e:
                self._toast(f"Error: {e}")

    def goto_page(self, idx: int):
        if not self.doc:
            return
        idx = max(0, min(len(self.doc) - 1, idx))
        if idx == self.page:
            return
        self.stop_reading()
        self.page = idx
        self.sentence_text = ""
        self.sidebar.set_active(idx)
        self.render()

    def next_page(self):
        if self.doc and self.page < len(self.doc) - 1:
            self.goto_page(self.page + 1)

    def prev_page(self):
        if self.doc and self.page > 0:
            self.goto_page(self.page - 1)

    def jump_page(self):
        if not self.doc:
            return
        from PyQt6.QtWidgets import QInputDialog
        n, ok = QInputDialog.getInt(self, "Jump to page", "Page:", self.page + 1, 1, len(self.doc))
        if ok:
            self.goto_page(n - 1)

    # ─────────────────── RENDERING ───────────────────
    def render(self):
        if not self.doc:
            return
        self.lbl_info.setText(f"{self.page + 1} / {len(self.doc)}")
        self.lbl_zoom.setText(f"{int(self.zoom * 100)}%")
        self.progress.setValue(int((self.page + 1) / len(self.doc) * 100))

        job = RenderJob(self.doc, self.page, self.zoom,
                        self.highlights, self.pencil, self.sentence_text)
        self.renderer.set_job(job)

    def on_render_ready(self, idx: int, zoom: float, pixmap: QPixmap):
        if idx != self.page or abs(zoom - self.zoom) > 0.01:
            return
        self._last_pixmap = pixmap
        self.pdf.setFixedSize(pixmap.size())
        self.pdf.setPixmap(pixmap)

    # ─────────────────── ZOOM ───────────────────
    def zoom_in(self):
        self.zoom = min(4.0, self.zoom + 0.2)
        self.render()

    def zoom_out(self):
        self.zoom = max(0.4, self.zoom - 0.2)
        self.render()

    def zoom_reset(self):
        self.zoom = 1.6
        self.render()

    def zoom_toward(self, cursor_pos: QPoint, new_zoom: float):
        if not self.doc:
            return
        rel = self.pdf.mapFrom(self.scroll.viewport(), cursor_pos)
        rx = rel.x() / max(1, self.pdf.width())
        ry = rel.y() / max(1, self.pdf.height())

        self.zoom = new_zoom
        self.render()

        QTimer.singleShot(80, lambda: self._reanchor(rx, ry))

    def _reanchor(self, rx: float, ry: float):
        target_x = int(rx * self.pdf.width()) - self.scroll.viewport().width() // 2
        target_y = int(ry * self.pdf.height()) - self.scroll.viewport().height() // 2
        self.scroll.horizontalScrollBar().setValue(max(0, target_x))
        self.scroll.verticalScrollBar().setValue(max(0, target_y))

    # ─────────────────── TOOLS ───────────────────
    def pick_color(self):
        c = QColorDialog.getColor(self.active_color, self, "Highlight Color")
        if c.isValid():
            c.setAlpha(110)
            self.active_color = c

    def toggle_highlight(self, checked: bool):
        self.highlight_mode = checked
        if checked:
            self.btn_pen.setChecked(False)
            self.pencil_mode = False
            self._toast("Highlighter on")
        else:
            self.pdf.setCursor(Qt.CursorShape.ArrowCursor)

    def toggle_pencil(self, checked: bool):
        self.pencil_mode = checked
        if checked:
            self.btn_hl.setChecked(False)
            self.highlight_mode = False
            self._toast("Pencil on")
        else:
            self.pdf.setCursor(Qt.CursorShape.ArrowCursor)

    def highlight_add(self, rect: QRect):
        if self.page not in self.highlights:
            self.highlights[self.page] = []
        ur = QRectF(rect.x() / self.zoom, rect.y() / self.zoom,
                    rect.width() / self.zoom, rect.height() / self.zoom)
        self.highlights[self.page].append((ur, QColor(self.active_color)))
        self.render()

    def pencil_add(self, fpos: QPointF, start: bool = False):
        if self.page not in self.pencil:
            self.pencil[self.page] = []
        up = QPointF(fpos.x() / self.zoom, fpos.y() / self.zoom)
        if start:
            self.pencil[self.page].append(QPainterPath(up))
        elif self.pencil[self.page]:
            self.pencil[self.page][-1].lineTo(up)
        self.render()

    def erase_at(self, pos: QPoint):
        up = QPointF(pos.x() / self.zoom, pos.y() / self.zoom)
        changed = False
        if self.page in self.highlights:
            before = len(self.highlights[self.page])
            self.highlights[self.page] = [
                h for h in self.highlights[self.page] if not h[0].contains(up)
            ]
            if len(self.highlights[self.page]) < before:
                changed = True
        if self.page in self.pencil:
            before = len(self.pencil[self.page])
            self.pencil[self.page] = [
                p for p in self.pencil[self.page] if not p.boundingRect().adjusted(-2, -2, 2, 2).contains(up)
            ]
            if len(self.pencil[self.page]) < before:
                changed = True
        if changed:
            self.render()

    def add_note(self):
        note = TextNote(self.pdf)
        cx = self.scroll.horizontalScrollBar().value() + self.scroll.viewport().width() // 2 - 130
        cy = self.scroll.verticalScrollBar().value() + self.scroll.viewport().height() // 2 - 90
        note.move(max(20, cx), max(20, cy))
        note.show()
        note.raise_()

    def add_sketch(self):
        sk = SketchNote(self.pdf)
        cx = self.scroll.horizontalScrollBar().value() + self.scroll.viewport().width() // 2 - 130
        cy = self.scroll.verticalScrollBar().value() + self.scroll.viewport().height() // 2 - 110
        sk.move(max(20, cx + 40), max(20, cy + 40))
        sk.show()
        sk.raise_()

    # ─────────────────── SEARCH ───────────────────
    def toggle_search(self):
        if self.search_overlay.isVisible():
            self.search_overlay._close()
        else:
            self.search_overlay.show()
            self.search_overlay.raise_()
            self._reposition_floating()

    def do_search(self, text: str):
        if not self.doc or not text:
            return
        self._search_results.clear()
        self._search_idx = -1
        text_lower = text.lower()
        for i in range(len(self.doc)):
            page = self.doc.load_page(i)
            rects = page.search_for(text_lower)
            for r in rects:
                self._search_results.append((i, QRectF(r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0)))
        if self._search_results:
            self._toast(f"Found {len(self._search_results)} results")
            self.search_next()
        else:
            self._toast("No results found")

    def search_next(self):
        if not self._search_results:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_results)
        self._goto_search_result()

    def search_prev(self):
        if not self._search_results:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_results)
        self._goto_search_result()

    def _goto_search_result(self):
        if self._search_idx < 0 or self._search_idx >= len(self._search_results):
            return
        page_idx, rect = self._search_results[self._search_idx]
        if page_idx != self.page:
            self.goto_page(page_idx)
        QTimer.singleShot(100, lambda: self._scroll_to_rect(rect))

    def _scroll_to_rect(self, rect: QRectF):
        x = int(rect.x() * self.zoom) - self.scroll.viewport().width() // 2
        y = int(rect.y() * self.zoom) - self.scroll.viewport().height() // 2
        self.scroll.horizontalScrollBar().setValue(max(0, x))
        self.scroll.verticalScrollBar().setValue(max(0, y))

    def clear_search(self):
        self._search_results.clear()
        self._search_idx = -1
        self.render()

    # ─────────────────── SIDEBAR ───────────────────
    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()
            if self.doc:
                self.sidebar.set_active(self.page)

    # ─────────────────── TTS ───────────────────
    def toggle_play(self):
        if self.tts_worker.isRunning():
            self.stop_reading()
        else:
            self.start_reading()

    def start_reading(self):
        if not self.doc:
            self._toast("Open a PDF first")
            return
        text = self.doc.load_page(self.page).get_text("text")
        speed = self.slider_speed.value() / 10.0
        voice = self.combo_voice.currentText()
        self.tts_worker.load(text, speed, voice)
        self.tts_worker.start()
        self.btn_play.setText("⏸")

    def stop_reading(self):
        self.tts_worker.stop()
        self.sentence_text = ""
        self.btn_play.setText("▷")
        self.render()

    def on_sentence(self, idx: int, text: str):
        self.sentence_text = text
        self.render()

    def on_page_done(self):
        if self.doc and self.page < len(self.doc) - 1:
            self.page += 1
            self.sidebar.set_active(self.page)
            self.render()
            QTimer.singleShot(400, self.start_reading)
        else:
            self.stop_reading()
            self._toast("Document complete")

    # ─────────────────── VOICE ───────────────────
    def load_custom_voice(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Model Folder")
        if not folder:
            return
        self.stop_reading()
        files = os.listdir(folder)
        onnx = [f for f in files if f.endswith('.onnx')]
        if not onnx:
            self._toast("No .onnx found"); return
        onnx_path = os.path.join(folder, onnx[0])
        tokens_path = os.path.join(folder, "tokens.txt")
        if not os.path.exists(tokens_path):
            self._toast("Missing tokens.txt"); return
        if not HAS_SHERPA:
            self._toast("sherpa-onnx not installed"); return
        is_kokoro = any("kokoro" in f.lower() for f in files)
        try:
            if is_kokoro:
                voices = os.path.join(folder, "voices.bin")
                cfg = sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                            model=onnx_path, tokens=tokens_path, voices=voices)))
            else:
                d = os.path.join(folder, "espeak-ng-data")
                if not os.path.exists(d): d = ""
                cfg = sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                            model=onnx_path, tokens=tokens_path, data_dir=d)))
            self.tts_engine = sherpa_onnx.OfflineTts(cfg)
            self.tts_worker.engine = self.tts_engine
            name = f"Offline · {os.path.basename(onnx_path)}"
            self.combo_voice.addItem(name)
            self.combo_voice.setCurrentText(name)
            self._toast("Voice loaded")
        except Exception as e:
            self._toast("Failed to load voice")
            print(e)

    # ─────────────────── FOCUS MODE ───────────────────
    def toggle_focus(self):
        self._focus_mode = not self._focus_mode
        if self._focus_mode:
            self._set_toolbar_visible(False)
            self.status.setVisible(False)
            self.sidebar.hide()
            self.search_overlay.hide()
            self._toast("Focus mode · move mouse to top edge")
        else:
            self._set_toolbar_visible(True)
            self.status.setVisible(True)
            if self.doc:
                self.sidebar.show()

    # ─────────────────── GLOBAL HOTKEY ───────────────────
    def _setup_global_hotkey(self):
        if not HAS_KEYBOARD:
            return
        class Bridge(QObject):
            triggered = pyqtSignal()
        self.bridge = Bridge()
        self.bridge.triggered.connect(self._read_selection)
        try:
            keyboard.add_hotkey('alt+s', lambda: self.bridge.triggered.emit())
        except Exception:
            pass

    def _read_selection(self):
        self.stop_reading()
        QApplication.clipboard().clear()
        if HAS_KEYBOARD:
            keyboard.send('ctrl+c')
        QTimer.singleShot(200, self._read_clipboard)

    def _read_clipboard(self):
        txt = QApplication.clipboard().text()
        if txt:
            speed = self.slider_speed.value() / 10.0
            voice = self.combo_voice.currentText()
            self.sentence_text = ""
            self.tts_worker.load(txt, speed, voice)
            self.tts_worker.start()
            self.btn_play.setText("⏸")

    # ─────────────────── KEYS ───────────────────
    def keyPressEvent(self, e: QKeyEvent):
        if e.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(e)

    # ─────────────────── TOAST ───────────────────
    def _toast(self, text: str):
        Toast(text, self)

    # ─────────────────── CLEANUP ───────────────────
    def closeEvent(self, e):
        try:
            self.renderer.stop()
        except Exception:
            pass
        try:
            if HAS_KEYBOARD:
                keyboard.unhook_all()
        except Exception:
            pass
        super().closeEvent(e)


# ═════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(D.BG_DEEP))
    pal.setColor(QPalette.ColorRole.Base, QColor(D.BG_SURFACE))
    pal.setColor(QPalette.ColorRole.Text, QColor(D.TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(D.TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.Button, QColor(D.BG_ELEVATED))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(D.TEXT_SECONDARY))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(D.ACCENT_DIM))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(D.ACCENT))
    app.setPalette(pal)

    win = ZenReaderPro()
    win.show()
    sys.exit(app.exec())

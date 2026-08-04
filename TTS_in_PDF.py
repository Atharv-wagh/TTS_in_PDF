# TTS_in_PDF.py
import sys
print("\n[SYSTEM] 1. Booting application core...", flush=True)

import time
import os
import tempfile
import asyncio
print("[SYSTEM] 2. Loading AI and Audio libraries...", flush=True)

import keyboard
import sounddevice as sd
import sherpa_onnx
import fitz  # PyMuPDF
import edge_tts
import pygame
import re
import urllib.request
import tarfile

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QColorDialog,
    QTextEdit, QFrame, QComboBox, QGraphicsDropShadowEffect, QInputDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsPathItem
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPoint, QPointF, QRectF, QPropertyAnimation,
    QEasingCurve, QObject, QTimer, QSize
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QPen, QPainterPath, QKeySequence,
    QShortcut, QPalette, QTransform
)

print("[SYSTEM] 3. All libraries successfully imported!", flush=True)

# ─────────────────────────────────────────────────────────────
# Design System
# ─────────────────────────────────────────────────────────────
class Theme:
    BG_DEEP        = "#0A0A0C"
    BG_SURFACE     = "#141418"
    BG_ELEVATED    = "#1C1C22"
    BG_HOVER       = "#26262E"
    BORDER_SUBTLE  = "#2A2A32"
    BORDER_FOCUS   = "#3A3A45"
    TEXT_PRIMARY   = "#E8E8EC"
    TEXT_SECONDARY = "#8A8A95"
    TEXT_MUTED     = "#5A5A65"
    ACCENT         = "#7DD3A0"
    ACCENT_DIM     = "#3A5A48"
    WARNING        = "#E8B86D"

FONT_FAMILY = "SF Pro Display, Segoe UI, Inter, sans-serif"
BASE_RENDER_ZOOM = 8.0  # High-res 8K internal render for crispness

EDGE_VOICE_MAP = {
    "Aria · US Female":      "en-US-AriaNeural",
    "Guy · US Male":         "en-US-GuyNeural",
    "Jenny · US Female":     "en-US-JennyNeural",
    "Sonia · UK Female":     "en-GB-SoniaNeural",
    "Neerja · IN Female":    "en-IN-NeerjaExpressiveNeural",
    "Prabhat · IN Male":     "en-IN-PrabhatNeural",
}

def get_base_path():
    # PyInstaller puts bundled files in _MEIPASS, but that location is not a
    # suitable place for user-downloaded voice models.  Keep them next to the
    # executable so they are available on the next launch.
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

BASE_DIR = get_base_path()

def create_tts_config(folder_path):
    try:
        files = os.listdir(folder_path)
        onnx_files = [f for f in files if f.endswith('.onnx')]
        if not onnx_files: return None
        onnx_file = os.path.join(folder_path, onnx_files[0])
        tokens = os.path.join(folder_path, "tokens.txt")
        if not os.path.exists(tokens): return None
        
        is_kokoro = any("kokoro" in f.lower() for f in files)
        if is_kokoro:
            voices = os.path.join(folder_path, "voices.bin")
            return sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(model=onnx_file, tokens=tokens, voices=voices)))
        else:
            d = os.path.join(folder_path, "espeak-ng-data")
            lexicon = os.path.join(folder_path, "lexicon.txt")
            if os.path.exists(d):
                return sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=onnx_file, tokens=tokens, data_dir=d)))
            elif os.path.exists(lexicon):
                return sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=onnx_file, tokens=tokens, lexicon=lexicon)))
            else:
                return sherpa_onnx.OfflineTtsConfig(model=sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=onnx_file, tokens=tokens)))
    except Exception as e:
        print(f"Error creating config: {e}")
        return None

APP_QSS = f"""
QMainWindow, QWidget {{ background-color: {Theme.BG_DEEP}; color: {Theme.TEXT_PRIMARY}; font-family: '{FONT_FAMILY}'; font-size: 13px; }}
QLabel {{ background: transparent; color: {Theme.TEXT_SECONDARY}; }}
QPushButton {{ background: transparent; color: {Theme.TEXT_SECONDARY}; border: 1px solid transparent; border-radius: 8px; padding: 7px 12px; font-weight: 500; }}
QPushButton:hover {{ background: {Theme.BG_HOVER}; color: {Theme.TEXT_PRIMARY}; }}
QPushButton:pressed {{ background: {Theme.BG_ELEVATED}; }}
QPushButton:checked {{ background: {Theme.ACCENT_DIM}; color: {Theme.ACCENT}; border: 1px solid {Theme.ACCENT_DIM}; }}
QComboBox {{ background: transparent; color: {Theme.TEXT_PRIMARY}; border: 1px solid {Theme.BORDER_SUBTLE}; border-radius: 8px; padding: 5px 10px; min-width: 140px; }}
QComboBox:hover {{ border-color: {Theme.BORDER_FOCUS}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {Theme.TEXT_SECONDARY}; margin-right: 6px; }}
QComboBox QAbstractItemView {{ background: {Theme.BG_ELEVATED}; border: 1px solid {Theme.BORDER_SUBTLE}; border-radius: 8px; padding: 4px; selection-background-color: {Theme.ACCENT_DIM}; selection-color: {Theme.ACCENT}; outline: none; }}
QSlider::groove:horizontal {{ height: 3px; background: {Theme.BORDER_SUBTLE}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {Theme.ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {Theme.TEXT_PRIMARY}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
QSlider::handle:horizontal:hover {{ background: {Theme.ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: {Theme.BORDER_SUBTLE}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {Theme.BORDER_FOCUS}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QTextEdit {{ background: {Theme.BG_DEEP}; color: {Theme.TEXT_PRIMARY}; border: 1px solid {Theme.BORDER_SUBTLE}; border-radius: 6px; padding: 6px; }}
"""

# ─────────────────────────────────────────────────────────────
# Threads & Bridges
# ─────────────────────────────────────────────────────────────
class HotkeySignalBridge(QObject):
    trigger = pyqtSignal()

class TTSWorker(QThread):
    sentence_started = pyqtSignal(int, str)
    page_finished    = pyqtSignal()

    def __init__(self, tts_engine):
        super().__init__()
        
        # MOVED PYGAME INIT HERE TO PREVENT DEADLOCKS
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        except Exception as e:
            print(f"Audio init warning: {e}", flush=True)
            
        self.tts_engine    = tts_engine
        self.sentences     = []
        self.current_idx   = 0
        self.speed         = 1.0
        self.engine_choice = ""
        self.stop_requested = False
        self.is_paused     = False

    def load_text(self, text, speed, engine_choice):
        clean = re.sub(r'\s+', ' ', text).strip()
        self.sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean) if s.strip()]
        self.current_idx = 0
        self.speed = speed
        self.engine_choice = engine_choice
        self.is_paused = False

    def pause(self):
        self.is_paused = True
        try:
            if pygame.mixer.get_init(): pygame.mixer.music.pause()
        except Exception: pass

    def resume(self):
        self.is_paused = False
        try:
            if pygame.mixer.get_init(): pygame.mixer.music.unpause()
        except Exception: pass

    def run(self):
        self.stop_requested = False
        self.is_paused = False
        
        while self.current_idx < len(self.sentences) and not self.stop_requested:
            while self.is_paused and not self.stop_requested:
                time.sleep(0.05)
            if self.stop_requested: break

            sentence = self.sentences[self.current_idx].strip()
            if sentence and re.search(r'[a-zA-Z0-9]', sentence):
                self.sentence_started.emit(self.current_idx, sentence)
                try:
                    if self.engine_choice in EDGE_VOICE_MAP:
                        voice_id = EDGE_VOICE_MAP[self.engine_choice]
                        rate_pct = int((self.speed - 1.0) * 100)
                        rate_str = f"{rate_pct:+d}%"
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                        asyncio.run(edge_tts.Communicate(sentence, voice_id, rate=rate_str).save(tmp))
                        
                        pygame.mixer.music.load(tmp)
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy() and not self.stop_requested:
                            if self.is_paused:
                                pygame.mixer.music.pause()
                                while self.is_paused and not self.stop_requested:
                                    time.sleep(0.05)
                                if not self.stop_requested:
                                    pygame.mixer.music.unpause()
                            time.sleep(0.03)
                            
                        pygame.mixer.music.unload()
                        try: os.remove(tmp)
                        except Exception: pass
                    else:
                        if self.tts_engine is None:
                            print("Offline TTS missing! Please select an Edge TTS voice from the dropdown.")
                            self.stop_requested = True
                            break
                            
                        audio = self.tts_engine.generate(sentence, speed=self.speed)
                        sd.play(audio.samples, samplerate=audio.sample_rate)
                        while sd.get_stream() and sd.get_stream().active:
                            if self.stop_requested: break
                            if self.is_paused:
                                sd.stop()
                                while self.is_paused and not self.stop_requested:
                                    time.sleep(0.05)
                                if not self.stop_requested:
                                    sd.play(audio.samples, samplerate=audio.sample_rate)
                            time.sleep(0.03)
                        sd.wait()
                except Exception as e:
                    print(f"Skipping audio block: {e}")
            
            if not self.stop_requested and not self.is_paused:
                self.current_idx += 1

        if not self.stop_requested and not self.is_paused:
            self.page_finished.emit()

    def stop(self):
        self.stop_requested = True
        self.is_paused = False
        try:
            sd.stop()
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception: pass
        self.wait()

class RenderWorker(QThread):
    page_ready = pyqtSignal(int, QPixmap)

    def __init__(self):
        super().__init__()
        self.doc          = None
        self.page_idx     = 0
        self._running     = True
        self._job_pending = False

    def set_job(self, doc, page_idx):
        self.doc = doc
        self.page_idx = page_idx
        self._job_pending = True

    def run(self):
        while self._running:
            time.sleep(0.01)
            if not self._job_pending or self.doc is None:
                continue
            
            doc, page_idx = self.doc, self.page_idx
            self._job_pending = False
            
            try:
                page = doc.load_page(page_idx)
                matrix = fitz.Matrix(BASE_RENDER_ZOOM, BASE_RENDER_ZOOM)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                pixmap = QPixmap.fromImage(img)
                self.page_ready.emit(page_idx, pixmap)
            except Exception as e:
                print(f"Render error: {e}")

# ─────────────────────────────────────────────────────────────
# Floating Notes
# ─────────────────────────────────────────────────────────────
class AnimatedTextNote(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False; self.offset = QPoint()
        self.collapsed = QSize(40, 40); self.expanded = QSize(260, 180)
        self.resize(self.collapsed)
        self.setStyleSheet(f"""
            QFrame {{ background: rgba(28,28,34,0.92); border: 1px solid {Theme.ACCENT_DIM}; border-radius: 12px; }}
            QTextEdit {{ background: {Theme.BG_DEEP}; color: {Theme.TEXT_PRIMARY}; border: 1px solid {Theme.BORDER_SUBTLE}; border-radius: 6px; }}
        """)
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 6, 8, 8); lay.setSpacing(4)
        hdr = QHBoxLayout(); hdr.setSpacing(6)
        self.lbl_icon = QLabel("✎"); self.lbl_icon.setStyleSheet("color: #E8B86D; font-size: 14px;")
        self.lbl_title = QLabel("Note"); self.lbl_title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-weight: 600; font-size: 11px;")
        self.lbl_title.hide()
        hdr.addWidget(self.lbl_icon); hdr.addWidget(self.lbl_title); hdr.addStretch()
        lay.addLayout(hdr)
        self.editor = QTextEdit(); self.editor.setPlaceholderText("Write…"); self.editor.hide()
        lay.addWidget(self.editor)
        self._anim = QPropertyAnimation(self, b"size"); self._anim.setEasingCurve(QEasingCurve.Type.OutCubic); self._anim.setDuration(180)

    def enterEvent(self, e):
        self.lbl_title.show(); self.editor.show()
        self._anim.stop(); self._anim.setEndValue(self.expanded); self._anim.start()
        super().enterEvent(e)
    def leaveEvent(self, e):
        if not self.editor.hasFocus():
            self.lbl_title.hide(); self.editor.hide()
            self._anim.stop(); self._anim.setEndValue(self.collapsed); self._anim.start()
        super().leaveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.dragging = True; self.offset = e.pos()
    def mouseMoveEvent(self, e):
        if self.dragging: self.move(self.mapToParent(e.pos() - self.offset))
    def mouseReleaseEvent(self, e): self.dragging = False

class DrawingCanvasNote(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False; self.drawing = False
        self.offset = QPoint(); self.last_point = QPoint()
        self.collapsed = QSize(40, 40); self.expanded = QSize(260, 220)
        self.resize(self.collapsed)
        self.setStyleSheet(f"""
            QFrame {{ background: rgba(28,28,34,0.92); border: 1px solid {Theme.ACCENT_DIM}; border-radius: 12px; }}
            QPushButton {{ background: {Theme.BG_HOVER}; color: {Theme.TEXT_PRIMARY}; border-radius: 4px; padding: 2px 8px; font-size: 11px; }}
            QPushButton:hover {{ background: {Theme.ACCENT_DIM}; color: {Theme.ACCENT}; }}
        """)
        self.pixmap = QPixmap(240, 170); self.pixmap.fill(QColor(Theme.BG_DEEP))
        lay = QVBoxLayout(self); lay.setContentsMargins(8, 6, 8, 8); lay.setSpacing(4)
        hdr = QHBoxLayout(); hdr.setSpacing(6)
        self.lbl_icon = QLabel("✦"); self.lbl_icon.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 14px;")
        self.lbl_title = QLabel("Sketch"); self.lbl_title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-weight: 600; font-size: 11px;")
        self.lbl_title.hide()
        self.btn_clr = QPushButton("Clear"); self.btn_clr.clicked.connect(self.clear_canvas); self.btn_clr.hide()
        hdr.addWidget(self.lbl_icon); hdr.addWidget(self.lbl_title); hdr.addStretch(); hdr.addWidget(self.btn_clr)
        lay.addLayout(hdr)
        self.canvas_lbl = QLabel(); self.canvas_lbl.setPixmap(self.pixmap); self.canvas_lbl.hide()
        lay.addWidget(self.canvas_lbl)
        self._anim = QPropertyAnimation(self, b"size"); self._anim.setEasingCurve(QEasingCurve.Type.OutCubic); self._anim.setDuration(180)

    def clear_canvas(self): self.pixmap.fill(QColor(Theme.BG_DEEP)); self.canvas_lbl.setPixmap(self.pixmap)
    def enterEvent(self, e):
        self.lbl_title.show(); self.btn_clr.show(); self.canvas_lbl.show()
        self._anim.stop(); self._anim.setEndValue(self.expanded); self._anim.start()
        super().enterEvent(e)
    def leaveEvent(self, e):
        self.lbl_title.hide(); self.btn_clr.hide(); self.canvas_lbl.hide()
        self._anim.stop(); self._anim.setEndValue(self.collapsed); self._anim.start()
        super().leaveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if e.pos().y() < 30: self.dragging = True; self.offset = e.pos()
            else: self.drawing = True; self.last_point = self.canvas_lbl.mapFrom(self, e.pos())
    def mouseMoveEvent(self, e):
        if self.dragging: self.move(self.mapToParent(e.pos() - self.offset))
        elif self.drawing:
            cur = self.canvas_lbl.mapFrom(self, e.pos())
            p = QPainter(self.pixmap)
            p.setPen(QPen(QColor(Theme.ACCENT), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(self.last_point, cur); p.end()
            self.last_point = cur; self.canvas_lbl.setPixmap(self.pixmap)
    def mouseReleaseEvent(self, e): self.dragging = False; self.drawing = False

# ─────────────────────────────────────────────────────────────
# Graphics View
# ─────────────────────────────────────────────────────────────
class PDFGraphicsView(QGraphicsView):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(Theme.BG_DEEP))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.page_item = None
        self.tts_items = []
        self.current_pencil_item = None
        self.current_hl_item = None
        self.hl_start = QPointF()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
            self.app.zoom_scale *= factor
            self.app.zoom_scale = max(0.3, min(6.0, self.app.zoom_scale))
            self.scale(factor, factor)
            self.app.update_zoom_label()
            e.accept()
        else:
            super().wheelEvent(e)

    def mousePressEvent(self, e):
        scene_pos = self.mapToScene(e.pos())
        if not self.page_item or not self.page_item.contains(self.page_item.mapFromScene(scene_pos)):
            super().mousePressEvent(e)
            return

        raw_pdf_pos = scene_pos

        if e.button() == Qt.MouseButton.LeftButton:
            if self.app.pencil_mode:
                path = QPainterPath(raw_pdf_pos)
                self.current_pencil_item = QGraphicsPathItem()
                self.current_pencil_item.setPath(path)
                
                solid_color = QColor(self.app.active_color)
                solid_color.setAlpha(255)
                self.current_pencil_item.setPen(QPen(solid_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                self.scene.addItem(self.current_pencil_item)
                
                if self.app.current_page not in self.app.pencil_strokes:
                    self.app.pencil_strokes[self.app.current_page] = []
                self.app.pencil_strokes[self.app.current_page].append([path, solid_color])
                
            elif self.app.highlight_mode:
                self.hl_start = raw_pdf_pos
                self.current_hl_item = QGraphicsRectItem(QRectF(self.hl_start, self.hl_start))
                self.current_hl_item.setBrush(self.app.active_color)
                self.current_hl_item.setPen(QPen(Qt.PenStyle.NoPen))
                self.scene.addItem(self.current_hl_item)
        elif e.button() == Qt.MouseButton.RightButton:
            self.app.erase_at(raw_pdf_pos)
            
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        scene_pos = self.mapToScene(e.pos())
        if self.page_item:
            raw_pdf_pos = scene_pos
            if self.current_pencil_item:
                path = self.current_pencil_item.path()
                path.lineTo(raw_pdf_pos)
                self.current_pencil_item.setPath(path)
                self.app.pencil_strokes[self.app.current_page][-1][0] = path
            elif self.current_hl_item:
                self.current_hl_item.setRect(QRectF(self.hl_start, raw_pdf_pos).normalized())
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.current_pencil_item:
            self.current_pencil_item = None
        elif self.current_hl_item:
            rect = self.current_hl_item.rect()
            if rect.width() > 0.01 and rect.height() > 0.01:
                if self.app.current_page not in self.app.user_highlights:
                    self.app.user_highlights[self.app.current_page] = []
                self.app.user_highlights[self.app.current_page].append((rect, QColor(self.app.active_color)))
            else:
                self.scene.removeItem(self.current_hl_item)
            self.current_hl_item = None
        super().mouseReleaseEvent(e)

# ─────────────────────────────────────────────────────────────
# Toast Notification
# ─────────────────────────────────────────────────────────────
class Toast(QFrame):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setStyleSheet(f"""
            QFrame {{ background: rgba(28,28,34,0.96); border: 1px solid {Theme.BORDER_FOCUS}; border-radius: 10px; }}
            QLabel {{ color: {Theme.TEXT_PRIMARY}; font-size: 12px; padding: 10px 18px; }}
        """)
        lay = QVBoxLayout(self); lay.setContentsMargins(0,0,0,0)
        lbl = QLabel(text); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl); self.adjustSize()
        if parent:
            r = parent.rect()
            self.move(r.center().x() - self.width()//2, r.bottom() - self.height() - 80)
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self._eff = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self._eff)
        self._anim = QPropertyAnimation(self._eff, b"opacity"); self._anim.setDuration(220)
        self._eff.setOpacity(0.0); self._anim.setStartValue(0.0); self._anim.setEndValue(1.0); self._anim.start()
        QTimer.singleShot(1800, self._fade_out)

    def _fade_out(self):
        self._anim.stop(); self._anim.setStartValue(1.0); self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.close); self._anim.start()

# ─────────────────────────────────────────────────────────────
# Neural Engine Store
# ─────────────────────────────────────────────────────────────
class ModelDownloadWorker(QThread):
    finished = pyqtSignal(str, bool)

    def __init__(self, folder_name, url):
        super().__init__()
        self.folder_name = folder_name
        self.url = url

    def run(self):
        try:
            dl_path = os.path.join(BASE_DIR, "temp_model.tar.bz2")
            urllib.request.urlretrieve(self.url, dl_path)
            with tarfile.open(dl_path, "r:bz2") as tar:
                if hasattr(tarfile, 'data_filter'): tar.extractall(path=BASE_DIR, filter='data')
                else: tar.extractall(path=BASE_DIR)
            os.remove(dl_path)
            self.finished.emit(self.folder_name, True)
        except Exception as e:
            print(f"Download failed: {e}")
            self.finished.emit(self.folder_name, False)

from PyQt6.QtWidgets import QDialog, QScrollArea
class VoiceStoreDialog(QDialog):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.app = parent_app
        self.setWindowTitle("Neural Voice Engine Store")
        self.setMinimumWidth(520)
        self.setMinimumHeight(600)
        self.setStyleSheet(f"""
            QDialog {{ background: {Theme.BG_DEEP}; }}
            QLabel {{ color: {Theme.TEXT_PRIMARY}; font-family: '{FONT_FAMILY}'; }}
            QPushButton {{ background: {Theme.BG_HOVER}; border-radius: 6px; padding: 8px; font-weight: bold; }}
            QPushButton:hover {{ background: {Theme.BORDER_FOCUS}; }}
        """)
        lay = QVBoxLayout(self)
        
        btn_local = QPushButton("📂 Import Local Model Folder")
        btn_local.setStyleSheet(f"background: {Theme.ACCENT_DIM}; color: {Theme.ACCENT}; border: 1px solid {Theme.ACCENT}; margin-bottom: 10px;")
        btn_local.clicked.connect(self.import_local_folder)
        lay.addWidget(btn_local)

        title = QLabel("Available Cloud Engines")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Theme.TEXT_PRIMARY}; margin-bottom: 5px;")
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        slay = QVBoxLayout(scroll_content)

        self.models = {
            "Piper (Amy) · US Female · Ultra Light": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-amy-low.tar.bz2", "folder": "vits-piper-en_US-amy-low", "specs": "Speed: Blazing | RAM: <100MB\nPerfect for low-end hardware.", "type": "vits"},
            "Piper (Ryan) · US Male · Ultra Light": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_US-ryan-low.tar.bz2", "folder": "vits-piper-en_US-ryan-low", "specs": "Speed: Blazing | RAM: <100MB\nDeep, resonant American male voice.", "type": "vits"},
            "Piper (Alba) · GB Female · Ultra Light": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-en_GB-alba-medium.tar.bz2", "folder": "vits-piper-en_GB-alba-medium", "specs": "Speed: Blazing | RAM: <100MB\nClear British female accent.", "type": "vits"},
            "VITS (LJSpeech) · Balanced": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-ljs.tar.bz2", "folder": "vits-ljs", "specs": "Speed: Fast | RAM: ~150MB\nGreat natural cadence.", "type": "vits"},
            "VITS (VCTK) · Multi-Speaker": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-vctk.tar.bz2", "folder": "vits-vctk", "specs": "Speed: Fast | RAM: ~200MB\nContains over 100 different English voices.", "type": "vits"},
            "Kokoro (English) · Studio Quality": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-en-v0_19.tar.bz2", "folder": "kokoro-en-v0_19", "specs": "Speed: Moderate | RAM: ~400MB\nGod-tier heavy model. Sounds human.", "type": "kokoro"},
            "Kokoro (Multi-Lang) · Studio Quality": {"url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2", "folder": "kokoro-multi-lang-v1_0", "specs": "Speed: Moderate | RAM: ~450MB\nMassive multi-language studio model.", "type": "kokoro"}
        }

        for name, data in self.models.items():
            frame = QFrame()
            frame.setStyleSheet(f"QFrame {{ background: {Theme.BG_SURFACE}; border: 1px solid {Theme.BORDER_SUBTLE}; border-radius: 8px; margin-bottom: 5px; }}")
            flay = QVBoxLayout(frame)
            
            lbl_name = QLabel(f"<b>{name}</b>")
            lbl_specs = QLabel(data['specs'])
            lbl_specs.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 11px;")
            
            btn = QPushButton()
            folder_path = os.path.join(BASE_DIR, data['folder'])
            
            if os.path.exists(folder_path):
                btn.setText("✓ Set as Active Engine")
                btn.setStyleSheet(f"background: {Theme.ACCENT_DIM}; color: {Theme.ACCENT}; border: 1px solid {Theme.ACCENT};")
                btn.clicked.connect(lambda ch, n=name, d=data: self.use_model(n, d))
            else:
                btn.setText("Download & Install")
                btn.clicked.connect(lambda ch, b=btn, n=name, d=data: self.download_model(b, n, d))
                
            flay.addWidget(lbl_name)
            flay.addWidget(lbl_specs)
            flay.addWidget(btn)
            slay.addWidget(frame)
            
        slay.addStretch()
        scroll.setWidget(scroll_content)
        lay.addWidget(scroll)

    def import_local_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Unzipped Model Folder")
        if not folder: return
        self.app.stop_reading()
        display_name = f"Offline · {os.path.basename(folder)}"
        if display_name not in self.app.available_offline_models:
            self.app.available_offline_models[display_name] = folder
            self.app.tts_selector.insertItem(0, display_name)
        self.app.tts_selector.setCurrentText(display_name)
        self.app._toast("Custom Voice loaded!")
        self.accept()

    def download_model(self, btn, name, data):
        btn.setText("Downloading Engine... (This may take a minute)")
        btn.setEnabled(False)
        self.worker = ModelDownloadWorker(data['folder'], data['url'])
        self.worker.finished.connect(lambda folder, success: self.on_download_done(btn, name, data, success))
        self.worker.start()

    def on_download_done(self, btn, name, data, success):
        if success:
            btn.setText("✓ Set as Active Engine")
            btn.setStyleSheet(f"background: {Theme.ACCENT_DIM}; color: {Theme.ACCENT}; border: 1px solid {Theme.ACCENT};")
            btn.setEnabled(True)
            btn.clicked.disconnect()
            btn.clicked.connect(lambda ch, n=name, d=data: self.use_model(n, d))
            
            display_name = f"Offline · {data['folder']}"
            if display_name not in self.app.available_offline_models:
                self.app.available_offline_models[display_name] = os.path.join(BASE_DIR, data['folder'])
                self.app.tts_selector.insertItem(0, display_name)
        else:
            btn.setText("Download Failed - Retry")
            btn.setEnabled(True)

    def use_model(self, name, data):
        display_name = f"Offline · {data['folder']}"
        if display_name not in self.app.available_offline_models:
            self.app.available_offline_models[display_name] = os.path.join(BASE_DIR, data['folder'])
            self.app.tts_selector.insertItem(0, display_name)
        
        self.app.tts_selector.setCurrentText(display_name)
        self.app._toast(f"Engine Hot-Swapped: {display_name}")
        self.accept()

# ─────────────────────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────────────────────
class TTS_in_PDFApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TTS in PDF")
        self.resize(1280, 860)
        self.setMinimumSize(800, 600)
        self.setStyleSheet(APP_QSS)
        self.setWindowOpacity(0.0)
        
        print("[SYSTEM] Scanning for default models...", flush=True)
        
        amy_path = os.path.join(BASE_DIR, "vits-piper-en_US-amy-low")
        if not os.path.exists(amy_path):
            # Never block application startup with a large download.  The UI
            # starts with the online Edge voices; offline voices can be
            # downloaded from the +Voice dialog after the window is visible.
            print("[SYSTEM] No offline voice installed. Use +Voice to download one.", flush=True)
                
        print("[SYSTEM] Setting up Offline Model scanner...", flush=True)
        self.available_offline_models = {}
        for item in os.listdir(BASE_DIR):
            folder = os.path.join(BASE_DIR, item)
            if os.path.isdir(folder):
                files = os.listdir(folder)
                if any(f.endswith('.onnx') for f in files) and "tokens.txt" in files:
                    display_name = f"Offline · {item}"
                    self.available_offline_models[display_name] = folder
                    
        self.tts = None
        if self.available_offline_models:
            first_model = list(self.available_offline_models.keys())[0]
            cfg = create_tts_config(self.available_offline_models[first_model])
            if cfg: 
                try:
                    self.tts = sherpa_onnx.OfflineTts(cfg)
                except Exception as e:
                    print(f"[SYSTEM] Skipping corrupted default model: {e}", flush=True)

        self.tts_worker = TTSWorker(self.tts)
        self.tts_worker.sentence_started.connect(self.on_sentence_started)
        self.tts_worker.page_finished.connect(self.on_page_finished)

        self.renderer = RenderWorker()
        self.renderer.page_ready.connect(self.on_page_ready)
        self.renderer.start()

        self.doc                = None
        self.current_page       = 0
        self.current_sentence_text = ""
        self.zoom_scale         = 1.0
        self.active_color       = QColor(255, 220, 130, 90)
        
        self.highlight_mode     = False
        self.pencil_mode        = False
        self.user_highlights    = {}
        self.pencil_strokes     = {}
        self.page_notes         = {}

        self._toolbar_visible   = True
        self._focus_mode        = False
        self._autohide_timer    = QTimer(self)
        self._autohide_timer.setSingleShot(True)
        self._autohide_timer.timeout.connect(self._maybe_hide_toolbar)

        self.init_ui()
        self.setup_global_hotkey()
        self._setup_shortcuts()

        self._launch_anim = QPropertyAnimation(self, b"windowOpacity")
        self._launch_anim.setDuration(420); self._launch_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._launch_anim.setStartValue(0.0); self._launch_anim.setEndValue(1.0); self._launch_anim.start()
        print("[SYSTEM] Window Initialized!", flush=True)

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        self.toolbar = QFrame(self); self.toolbar.setObjectName("Toolbar")
        self.toolbar.setStyleSheet(f"QFrame#Toolbar {{ background: rgba(20,20,24,0.78); border: 1px solid {Theme.BORDER_SUBTLE}; border-radius: 14px; }}")
        shadow = QGraphicsDropShadowEffect(self.toolbar); shadow.setBlurRadius(30); shadow.setColor(QColor(0,0,0,160)); shadow.setOffset(0, 6)
        self.toolbar.setGraphicsEffect(shadow)
        t = QHBoxLayout(self.toolbar); t.setContentsMargins(12, 8, 12, 8); t.setSpacing(4)

        def mk_btn(text, tip, check=False):
            b = QPushButton(text); b.setToolTip(tip); b.setCursor(Qt.CursorShape.PointingHandCursor)
            if check: b.setCheckable(True)
            return b

        self.btn_open   = mk_btn("⌘ Open", "Open PDF (Ctrl+O)"); self.btn_open.clicked.connect(self.open_pdf)
        self.btn_play   = mk_btn("▷", "Play/Pause (Space)"); self.btn_play.clicked.connect(self.toggle_play)
        self.btn_stop   = mk_btn("□", "Stop (S)"); self.btn_stop.clicked.connect(self.stop_reading)

        self.tts_selector = QComboBox()
        self.tts_selector.addItems(list(self.available_offline_models.keys()))
        self.tts_selector.addItems(["Aria · US Female", "Guy · US Male", "Jenny · US Female", "Sonia · UK Female", "Neerja · IN Female", "Prabhat · IN Male"])
        self.tts_selector.currentTextChanged.connect(self.on_voice_changed)
        
        self.btn_load_model = mk_btn("＋Voice", "Load custom voice"); self.btn_load_model.clicked.connect(self.load_custom_local_voice)

        sep1 = self._vsep(); sep2 = self._vsep()
        self.btn_color     = mk_btn("◐", "Color"); self.btn_color.clicked.connect(self.open_color_wheel)
        self.btn_highlight = mk_btn("Highlight", "Highlight (H)", check=True); self.btn_highlight.clicked.connect(self.toggle_highlight)
        self.btn_pencil    = mk_btn("Pencil", "Pencil (P)", check=True); self.btn_pencil.clicked.connect(self.toggle_pencil)
        self.btn_text_note = mk_btn("＋Note", "Text Note (N)"); self.btn_text_note.clicked.connect(self.add_text_note)
        self.btn_draw_note = mk_btn("＋Sketch", "Sketch (K)"); self.btn_draw_note.clicked.connect(self.add_canvas_note)

        self.lbl_page_info = QLabel("No document"); self.lbl_page_info.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; margin-left: 10px; margin-right: 10px;")
        self.lbl_zoom_info = QLabel("100%"); self.lbl_zoom_info.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")

        self.speed_slider = QSlider(Qt.Orientation.Horizontal); self.speed_slider.setRange(5, 25); self.speed_slider.setValue(10); self.speed_slider.setFixedWidth(90)
        self.lbl_speed = QLabel("1.0×"); self.lbl_speed.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; min-width: 28px;")
        self.speed_slider.valueChanged.connect(lambda v: self.lbl_speed.setText(f"{v/10.0:.1f}×"))

        t.addWidget(self.btn_open); t.addWidget(self.btn_play); t.addWidget(self.btn_stop)
        t.addWidget(self.tts_selector); t.addWidget(self.btn_load_model); t.addWidget(sep1)
        t.addWidget(self.btn_color); t.addWidget(self.btn_highlight); t.addWidget(self.btn_pencil)
        t.addWidget(self.btn_text_note); t.addWidget(self.btn_draw_note); t.addWidget(sep2)
        t.addWidget(self.lbl_page_info); t.addWidget(self.lbl_zoom_info)
        t.addWidget(self.lbl_speed); t.addWidget(self.speed_slider); t.addStretch()

        self.btn_focus = mk_btn("◑", "Focus Mode (F)"); self.btn_focus.clicked.connect(self.toggle_focus_mode)
        t.addWidget(self.btn_focus)
        self.toolbar.adjustSize(); self.toolbar.raise_()

        self.pdf_view = PDFGraphicsView(self)
        self.pdf_view.setStyleSheet("background: transparent; border: none;")
        root.addWidget(self.pdf_view, stretch=1)
        self._reposition_overlays()

    def on_voice_changed(self, text):
        if hasattr(self, 'available_offline_models') and text in self.available_offline_models:
            cfg = create_tts_config(self.available_offline_models[text])
            if cfg:
                try:
                    self.tts = sherpa_onnx.OfflineTts(cfg)
                    self.tts_worker.tts_engine = self.tts
                except Exception as e:
                    self._toast("Error: Model corrupted. Please delete and re-download.")
                    print(f"Model Load Error: {e}", flush=True)

    def _vsep(self):
        f = QFrame(); f.setFixedWidth(1); f.setFixedHeight(20)
        f.setStyleSheet(f"background: {Theme.BORDER_SUBTLE}; border: none;"); return f

    def resizeEvent(self, e):
        super().resizeEvent(e); self._reposition_overlays()

    def _reposition_overlays(self):
        tw = self.toolbar.sizeHint().width()
        self.toolbar.move((self.width() - tw)//2, 16)

    def _maybe_hide_toolbar(self):
        if self._focus_mode or self.isFullScreen():
            if not self.toolbar.underMouse(): self._animate_toolbar(False)

    def _animate_toolbar(self, show):
        if show == self._toolbar_visible: return
        self._toolbar_visible = show
        start_y = self.toolbar.y(); end_y = 16 if show else -(self.toolbar.height() + 20)
        anim = QPropertyAnimation(self.toolbar, b"pos", self.toolbar)
        anim.setDuration(260); anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(QPoint(self.toolbar.x(), start_y))
        anim.setEndValue(QPoint((self.width()-self.toolbar.sizeHint().width())//2, end_y))
        anim.start(); self.toolbar._pos_anim = anim

    def show_toolbar(self):
        self._autohide_timer.stop()
        if not self._toolbar_visible: self._animate_toolbar(True)
        if self._focus_mode or self.isFullScreen(): self._autohide_timer.start(2400)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.toggle_play)
        QShortcut(QKeySequence(Qt.Key.Key_S), self, self.stop_reading)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_pdf)
        QShortcut(QKeySequence(Qt.Key.Key_H), self, lambda: self.btn_highlight.click())
        QShortcut(QKeySequence(Qt.Key.Key_P), self, lambda: self.btn_pencil.click())
        QShortcut(QKeySequence(Qt.Key.Key_N), self, self.add_text_note)
        QShortcut(QKeySequence(Qt.Key.Key_K), self, self.add_canvas_note)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, self.toggle_focus_mode)
        QShortcut(QKeySequence("Ctrl+="), self, self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.zoom_reset)
        QShortcut(QKeySequence("Ctrl+L"), self, lambda: self.jump_to_page_prompt())

    def mouseMoveEvent(self, e):
        if e.position().y() < 80: self.show_toolbar()
        super().mouseMoveEvent(e)

    def open_pdf(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if fn:
            self.stop_reading()
            self.doc = fitz.open(fn)
            self.current_page = 0
            self.user_highlights.clear(); self.pencil_strokes.clear()
            self.request_render(); self._toast(f"Loaded · {len(self.doc)} pages")

    def load_custom_local_voice(self):
        self.stop_reading()
        store = VoiceStoreDialog(self)
        store.exec()

    def jump_to_page_prompt(self):
        if not self.doc: return
        n, ok = QInputDialog.getInt(self, "Jump to page", "Page:", self.current_page+1, 1, len(self.doc))
        if ok: self.goto_page(n-1)

    def goto_page(self, idx):
        if not self.doc: return
        idx = max(0, min(len(self.doc)-1, idx))
        self.stop_reading(); self.current_page = idx; self.request_render()

    def request_render(self):
        if not self.doc: return
        self.lbl_page_info.setText(f"{self.current_page + 1} / {len(self.doc)}")
        self.renderer.set_job(self.doc, self.current_page)

    def on_page_ready(self, idx, pixmap):
        if idx != self.current_page: return
        self.pdf_view.scene.clear()
        
        self.pdf_view.page_item = QGraphicsPixmapItem(pixmap)
        self.pdf_view.page_item.setScale(1.0 / BASE_RENDER_ZOOM)
        self.pdf_view.scene.addItem(self.pdf_view.page_item)
        
        self.pdf_view.resetTransform()
        self.pdf_view.scale(self.zoom_scale, self.zoom_scale)

        if self.current_page in self.user_highlights:
            for rect, color in self.user_highlights[self.current_page]:
                item = QGraphicsRectItem(rect)
                item.setBrush(color)
                item.setPen(QPen(Qt.PenStyle.NoPen))
                self.pdf_view.scene.addItem(item)

        if self.current_page in self.pencil_strokes:
            for stroke in self.pencil_strokes[self.current_page]:
                path = stroke[0] if isinstance(stroke, list) else stroke
                color = stroke[1] if isinstance(stroke, list) else QColor(Theme.ACCENT)
                
                item = QGraphicsPathItem(path)
                item.setPen(QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                self.pdf_view.scene.addItem(item)
                
        if not hasattr(self, 'page_notes'): self.page_notes = {}
        for page_idx, notes in self.page_notes.items():
            for n in notes: n.hide()
        if self.current_page in self.page_notes:
            for n in self.page_notes[self.current_page]: n.show()

        self.update_tts_highlight()

    def update_zoom_label(self):
        self.lbl_zoom_info.setText(f"{int(self.zoom_scale * 100)}%")

    def zoom_in(self):
        self.zoom_scale = min(6.0, self.zoom_scale + 0.2)
        scale_factor = self.zoom_scale / BASE_RENDER_ZOOM
        self.pdf_view.setTransform(QTransform.fromScale(scale_factor, scale_factor))
        self.update_zoom_label()

    def zoom_out(self):
        self.zoom_scale = max(0.3, self.zoom_scale - 0.2)
        scale_factor = self.zoom_scale / BASE_RENDER_ZOOM
        self.pdf_view.setTransform(QTransform.fromScale(scale_factor, scale_factor))
        self.update_zoom_label()

    def zoom_reset(self):
        self.zoom_scale = 1.0
        scale_factor = self.zoom_scale / BASE_RENDER_ZOOM
        self.pdf_view.resetTransform()
        self.pdf_view.scale(scale_factor, scale_factor)
        self.update_zoom_label()

    def open_color_wheel(self):
        c = QColorDialog.getColor(self.active_color, self, "Highlight Color")
        if c.isValid(): c.setAlpha(120); self.active_color = c

    def toggle_pencil(self, checked):
        self.pencil_mode = checked
        if checked: self.btn_highlight.setChecked(False); self.highlight_mode = False; self._toast("Pencil on")
        
    def toggle_highlight(self, checked):
        self.highlight_mode = checked
        if checked: self.btn_pencil.setChecked(False); self.pencil_mode = False; self._toast("Highlight on")

    def erase_at(self, raw_pdf_pos):
        changed = False
        if self.current_page in self.user_highlights:
            before = len(self.user_highlights[self.current_page])
            self.user_highlights[self.current_page] = [h for h in self.user_highlights[self.current_page] if not h[0].contains(raw_pdf_pos)]
            if len(self.user_highlights[self.current_page]) < before: changed = True
        if self.current_page in self.pencil_strokes:
            before = len(self.pencil_strokes[self.current_page])
            self.pencil_strokes[self.current_page] = [p for p in self.pencil_strokes[self.current_page] if not (p[0] if isinstance(p, list) else p).boundingRect().contains(raw_pdf_pos)]
            if len(self.pencil_strokes[self.current_page]) < before: changed = True
        if changed: self.on_page_ready(self.current_page, self.pdf_view.page_item.pixmap())

    def add_text_note(self):
        note = AnimatedTextNote(self.pdf_view)
        cx = self.pdf_view.width()//2 - 130; cy = self.pdf_view.height()//2 - 90
        note.move(max(20, cx), max(20, cy)); note.show()
        if not hasattr(self, 'page_notes'): self.page_notes = {}
        if self.current_page not in self.page_notes: self.page_notes[self.current_page] = []
        self.page_notes[self.current_page].append(note)

    def add_canvas_note(self):
        cn = DrawingCanvasNote(self.pdf_view)
        cx = self.pdf_view.width()//2 - 130; cy = self.pdf_view.height()//2 - 110
        cn.move(max(20, cx+40), max(20, cy+40)); cn.show()
        if not hasattr(self, 'page_notes'): self.page_notes = {}
        if self.current_page not in self.page_notes: self.page_notes[self.current_page] = []
        self.page_notes[self.current_page].append(cn) 

    # ──────────── TTS Logic with Pause/Resume ────────────
    def toggle_play(self):
        if self.tts_worker.isRunning():
            if self.tts_worker.is_paused:
                self.tts_worker.resume()
                self.btn_play.setText("⏸")
            else:
                self.tts_worker.pause()
                self.btn_play.setText("▷")
        else:
            self.start_reading_current_page()

    def start_reading_current_page(self):
        if not self.doc: self._toast("Open a PDF first"); return
        text = self.doc.load_page(self.current_page).get_text("text")
        speed = self.speed_slider.value()/10.0
        engine = self.tts_selector.currentText()
        self.current_sentence_text = ""
        self.tts_worker.load_text(text, speed, engine) 
        self.tts_worker.start()
        self.btn_play.setText("⏸")

    def stop_reading(self):
        self.tts_worker.stop()
        self.current_sentence_text = ""
        self.btn_play.setText("▷")
        self.update_tts_highlight()

    def on_sentence_started(self, idx, text):
        self.current_sentence_text = text
        self.update_tts_highlight()

    def on_page_finished(self):
        if self.doc and self.current_page < len(self.doc)-1:
            self.current_page += 1
            self.request_render()
            QTimer.singleShot(350, self.start_reading_current_page)
        else:
            self.stop_reading(); self._toast("Finished document")

    def update_tts_highlight(self):
        for item in self.pdf_view.tts_items:
            try:
                if item.scene(): self.pdf_view.scene.removeItem(item)
            except RuntimeError: pass
        self.pdf_view.tts_items.clear()

        if self.doc and self.current_sentence_text:
            page = self.doc.load_page(self.current_page)
            s = self.current_sentence_text.strip()
            rects = page.search_for(s)
            if not rects and len(s) > 20: rects = page.search_for(s[:20])
            for r in rects:
                qrect = QRectF(r.x0, r.y0, r.x1-r.x0, r.y1-r.y0)
                item = QGraphicsRectItem(qrect)
                
                tts_color = QColor(self.active_color)
                tts_color.setAlpha(70) 
                item.setBrush(tts_color)
                
                item.setPen(QPen(Qt.PenStyle.NoPen))
                self.pdf_view.scene.addItem(item)
                self.pdf_view.tts_items.append(item)

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.stop_reading(); self.current_page -= 1; self.request_render()
            
    def next_page(self):
        if self.doc and self.current_page < len(self.doc)-1:
            self.stop_reading(); self.current_page += 1; self.request_render()

    def toggle_focus_mode(self):
        self._focus_mode = not self._focus_mode
        if self._focus_mode:
            self._animate_toolbar(False)
            self._toast("Focus mode · move mouse to top for tools")
        else:
            self._animate_toolbar(True)

    def _toast(self, text): Toast(text, self)

    def setup_global_hotkey(self):
        self.hotkey_bridge = HotkeySignalBridge()
        self.hotkey_bridge.trigger.connect(self.trigger_alt_s)
        try: keyboard.add_hotkey('alt+s', lambda: self.hotkey_bridge.trigger.emit())
        except Exception: pass

    def trigger_alt_s(self):
        self.stop_reading()
        QApplication.clipboard().clear()
        keyboard.send('ctrl+c')
        QTimer.singleShot(180, self.read_clipboard_text)

    def read_clipboard_text(self):
        txt = QApplication.clipboard().text()
        if txt:
            speed = self.speed_slider.value()/10.0
            engine = self.tts_selector.currentText()
            self.current_sentence_text = ""
            self.tts_worker.load_text(txt, speed, engine)
            self.tts_worker.start()
            self.btn_play.setText("⏸")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_F11:
            if self.isFullScreen(): self.showNormal()
            else: self.showFullScreen()
        elif e.key() == Qt.Key.Key_Escape:
            if self._focus_mode: self.toggle_focus_mode()
        else: super().keyPressEvent(e)

    def closeEvent(self, e):
        try:
            self.renderer._running = False; self.renderer.quit(); self.renderer.wait(1000)
        except Exception: pass
        try: keyboard.unhook_all()
        except Exception: pass
        super().closeEvent(e)
if __name__ == "__main__":
    # --- WINDOWS ZOMBIE ARMOR ---
    import multiprocessing
    multiprocessing.freeze_support()
    # ----------------------------

    print("[SYSTEM] 4. Launching User Interface...", flush=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # ... (Keep the rest of your palette and launch code exactly the same) ...
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(Theme.BG_DEEP))
    pal.setColor(QPalette.ColorRole.Base,   QColor(Theme.BG_SURFACE))
    pal.setColor(QPalette.ColorRole.Text,   QColor(Theme.TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(Theme.TEXT_PRIMARY))
    pal.setColor(QPalette.ColorRole.Button, QColor(Theme.BG_ELEVATED))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(Theme.TEXT_SECONDARY))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(Theme.ACCENT_DIM))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(Theme.ACCENT))
    app.setPalette(pal)

    win = TTS_in_PDFApp()
    win.show()
    print("[SYSTEM] 5. Application successfully loaded!", flush=True)
    sys.exit(app.exec())

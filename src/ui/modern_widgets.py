"""Modern UI components for DeepGuard AI - Professional Dashboard Architecture."""
from __future__ import annotations
import math
from typing import Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QLinearGradient, QFontMetrics

from src.config import THEME_DARK


class CardWidget(QFrame):
    """Modern card container with glassmorphism effect."""
    
    def __init__(self, parent=None, title: str = ""):
        super().__init__(parent)
        self.title = title
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(16)
        
        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setStyleSheet(f"""
                color: {THEME_DARK['text_secondary']};
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            """)
            self.main_layout.addWidget(self.title_label)
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: {THEME_DARK['bg_card']};
                border: 1px solid {THEME_DARK['border']};
                border-radius: 16px;
            }}
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
    
    def add_widget(self, widget: QWidget):
        """Add widget to card content area."""
        self.main_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Add layout to card content area."""
        self.main_layout.addLayout(layout)
    
    def content_layout(self) -> QVBoxLayout:
        """Get the content layout for direct manipulation."""
        return self.main_layout


class MetricCard(QWidget):
    """Compact metric display card with value, label, and icon."""
    
    def __init__(self, label: str, value: str = "–", icon: str = "", color: str = None, parent=None):
        super().__init__(parent)
        self._label_text = label
        self._value_text = value
        self._icon = icon
        self._color = color or THEME_DARK['accent']
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # Icon circle
        self.icon_label = QLabel(self._icon)
        self.icon_label.setFixedSize(40, 40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet(f"""
            background-color: {self._color}22;
            border-radius: 20px;
            color: {self._color};
            font-size: 16px;
        """)
        layout.addWidget(self.icon_label)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        self.value_label = QLabel(self._value_text)
        self.value_label.setStyleSheet(f"""
            color: {THEME_DARK['text_primary']};
            font-size: 20px;
            font-weight: 700;
        """)
        text_layout.addWidget(self.value_label)
        
        self.label_widget = QLabel(self._label_text)
        self.label_widget.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 11px;
        """)
        text_layout.addWidget(self.label_widget)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Background styling
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {THEME_DARK['bg_elevated']};
                border-radius: 12px;
                border: 1px solid {THEME_DARK['border']};
            }}
        """)
    
    def set_value(self, value: str):
        """Update the metric value."""
        self._value_text = str(value)
        self.value_label.setText(self._value_text)
    
    def set_color(self, color: str):
        """Update the accent color."""
        self._color = color
        self.icon_label.setStyleSheet(f"""
            background-color: {color}22;
            border-radius: 20px;
            color: {color};
            font-size: 16px;
        """)


class MediaDropZone(QFrame):
    """Modern drag-and-drop media upload zone."""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, accepted_formats: list, placeholder: str = "Drop media here", parent=None):
        super().__init__(parent)
        self.accepted_formats = accepted_formats
        self.placeholder = placeholder
        self._current_file = None
        self._setup_ui()
        self._apply_style()
        self.setAcceptDrops(True)
    
    def _setup_ui(self):
        self.setMinimumHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 32, 32, 32)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Upload icon
        self.icon_label = QLabel("📁")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 48px;")
        self.layout.addWidget(self.icon_label)
        
        # Main text
        self.text_label = QLabel(self.placeholder)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(f"""
            color: {THEME_DARK['text_secondary']};
            font-size: 16px;
            font-weight: 500;
        """)
        self.layout.addWidget(self.text_label)
        
        # Subtext
        formats_str = ", ".join(self.accepted_formats[:5])
        self.sub_label = QLabel(f"Supports: {formats_str}")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 12px;
            margin-top: 8px;
        """)
        self.layout.addWidget(self.sub_label)
        
        # Browse button
        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setFixedWidth(140)
        self.browse_btn.setFixedHeight(40)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME_DARK['bg_elevated']};
                color: {THEME_DARK['text_primary']};
                border: 2px dashed {THEME_DARK['border_bright']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {THEME_DARK['border']};
                border-color: {THEME_DARK['accent']};
                color: {THEME_DARK['accent']};
            }}
        """)
        self.browse_btn.clicked.connect(self._on_browse)
        self.layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Preview widget (hidden initially)
        self.preview_widget = QLabel()
        self.preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_widget.setStyleSheet(f"""
            background-color: {THEME_DARK['bg_primary']};
            border-radius: 8px;
        """)
        self.preview_widget.hide()
        self.layout.addWidget(self.preview_widget)
    
    def _apply_style(self):
        self.setStyleSheet(f"""
            MediaDropZone {{
                background-color: {THEME_DARK['bg_secondary']};
                border: 2px dashed {THEME_DARK['border_bright']};
                border-radius: 16px;
            }}
            MediaDropZone[dragOver="true"] {{
                background-color: {THEME_DARK['accent']}11;
                border-color: {THEME_DARK['accent']};
            }}
        """)
    
    def _on_browse(self):
        from PyQt6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Media", "",
            f"Media Files ({' '.join('*.' + f for f in self.accepted_formats)})"
        )
        if files:
            self.files_dropped.emit(files)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragOver", "true")
            self.style().unpolish(self)
            self.style().polish(self)
    
    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", "false")
        self.style().unpolish(self)
        self.style().polish(self)
    
    def dropEvent(self, event):
        self.setProperty("dragOver", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.files_dropped.emit(files)
    
    def set_file(self, filepath: str):
        """Show file preview."""
        self._current_file = filepath
        self.icon_label.hide()
        self.text_label.hide()
        self.sub_label.hide()
        self.browse_btn.hide()
        
        self.preview_widget.show()
        self.preview_widget.setText(f"📄 {filepath.split('/')[-1]}")
    
    def clear(self):
        """Reset to initial state."""
        self._current_file = None
        self.icon_label.show()
        self.text_label.show()
        self.sub_label.show()
        self.browse_btn.show()
        self.preview_widget.hide()


class ConfidenceGauge(QWidget):
    """Animated circular confidence gauge with percentage."""
    
    def __init__(self, size: int = 200, parent=None):
        super().__init__(parent)
        self.size = size
        self._value = 0
        self._target_value = 0
        self._verdict = "–"
        self._color = THEME_DARK['text_muted']
        self.setFixedSize(size, size + 40)
        
        # Manual animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._anim_step = 0
        self._anim_total = 20  # 20 steps for 1 second at 50ms
    
    def _animate_step(self):
        """Animation step using timer."""
        self._anim_step += 1
        progress = self._anim_step / self._anim_total
        # Easing: OutCubic
        eased = 1 - pow(1 - progress, 3)
        
        start_val = getattr(self, '_anim_start_val', 0)
        self._value = start_val + (self._target_value - start_val) * eased
        self.update()
        
        if self._anim_step >= self._anim_total:
            self._anim_timer.stop()
            self._value = self._target_value
            self.update()
    
    def set_result(self, confidence: float, verdict: str, color: str):
        """Set the gauge with animation."""
        self._anim_start_val = self._value
        self._target_value = confidence * 100
        self._verdict = verdict
        self._color = color
        
        self._anim_step = 0
        self._anim_timer.start(50)  # 50ms = 20fps
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.size // 2
        center_y = self.size // 2
        radius = (self.size - 20) // 2
        
        # Background arc
        pen_bg = QPen(QColor(THEME_DARK['border']))
        pen_bg.setWidth(12)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(center_x - radius, center_y - radius, 
                       radius * 2, radius * 2, 225 * 16, -270 * 16)
        
        # Value arc
        if self._value > 0:
            pen_value = QPen(QColor(self._color))
            pen_value.setWidth(12)
            pen_value.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_value)
            
            span = int(-270 * 16 * (self._value / 100))
            painter.drawArc(center_x - radius, center_y - radius,
                           radius * 2, radius * 2, 225 * 16, span)
        
        # Center text
        painter.setPen(QColor(THEME_DARK['text_primary']))
        font = QFont("Segoe UI", 32, QFont.Weight.Bold)
        painter.setFont(font)
        
        value_text = f"{int(self._value)}%"
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(value_text)
        painter.drawText(center_x - text_width // 2, center_y + 10, value_text)
        
        # Verdict text below
        painter.setPen(QColor(self._color))
        font_verdict = QFont("Segoe UI", 14, QFont.Weight.Bold)
        painter.setFont(font_verdict)
        metrics_v = QFontMetrics(font_verdict)
        v_width = metrics_v.horizontalAdvance(self._verdict)
        painter.drawText(center_x - v_width // 2, self.size - 5, self._verdict)


class ModernButton(QPushButton):
    """Modern styled button with hover animation."""
    
    def __init__(self, text: str, variant: str = "primary", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self._apply_style()
    
    def _apply_style(self):
        if self.variant == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {THEME_DARK['accent']}, stop:1 {THEME_DARK['accent_dim']});
                    color: #0A0F1A;
                    border: none;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 700;
                    padding: 0 28px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {THEME_DARK['accent_dim']}, stop:1 {THEME_DARK['accent']});
                }}
                QPushButton:pressed {{
                    background: {THEME_DARK['accent_dim']};
                }}
                QPushButton:disabled {{
                    background: {THEME_DARK['border']};
                    color: {THEME_DARK['text_muted']};
                }}
            """)
        elif self.variant == "secondary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME_DARK['bg_elevated']};
                    color: {THEME_DARK['text_primary']};
                    border: 1px solid {THEME_DARK['border_bright']};
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0 24px;
                }}
                QPushButton:hover {{
                    background-color: {THEME_DARK['border']};
                    border-color: {THEME_DARK['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {THEME_DARK['bg_card']};
                }}
            """)
        elif self.variant == "danger":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME_DARK['danger']}22;
                    color: {THEME_DARK['danger']};
                    border: 1px solid {THEME_DARK['danger']}44;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0 24px;
                }}
                QPushButton:hover {{
                    background-color: {THEME_DARK['danger']}44;
                }}
            """)


class LoadingSkeleton(QWidget):
    """Animated loading placeholder."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 0.4
        self._growing = True
        self.setMinimumHeight(60)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)
    
    def _animate(self):
        if self._growing:
            self._opacity += 0.02
            if self._opacity >= 1.0:
                self._growing = False
        else:
            self._opacity -= 0.02
            if self._opacity <= 0.4:
                self._growing = True
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(THEME_DARK['border'])
        color.setAlphaF(self._opacity)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)


class AnalysisPanel(CardWidget):
    """Panel containing analysis results with metrics and explanations."""
    
    def __init__(self, parent=None):
        super().__init__(parent, "Analysis Details")
        self._setup_content()
    
    def _setup_content(self):
        # Metrics grid
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)
        
        self.metric_confidence = MetricCard("Confidence", "–", "🎯", THEME_DARK['accent'])
        self.metric_frames = MetricCard("Frames", "–", "🎞", THEME_DARK['warning'])
        self.metric_time = MetricCard("Time", "–", "⏱", THEME_DARK['text_secondary'])
        
        metrics_layout.addWidget(self.metric_confidence)
        metrics_layout.addWidget(self.metric_frames)
        metrics_layout.addWidget(self.metric_time)
        
        self.add_layout(metrics_layout)
        
        # AI Explanation section
        self.explanation_card = CardWidget(title="AI Explanation")
        self.explanation_card.setMinimumHeight(120)
        self.explanation_text = QLabel("Analysis results will appear here...")
        self.explanation_text.setWordWrap(True)
        self.explanation_text.setStyleSheet(f"""
            color: {THEME_DARK['text_secondary']};
            font-size: 13px;
            line-height: 1.6;
        """)
        self.explanation_card.add_widget(self.explanation_text)
        self.add_widget(self.explanation_card)
        
        # Indicators section
        self.indicators_card = CardWidget(title="Detected Indicators")
        self.indicators_card.setMinimumHeight(100)
        self.indicators_text = QLabel("No indicators detected yet.")
        self.indicators_text.setWordWrap(True)
        self.indicators_text.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 12px;
        """)
        self.indicators_card.add_widget(self.indicators_text)
        self.add_widget(self.indicators_card)
    
    def update_results(self, confidence: float, frames: int, time_sec: float, 
                     explanation: str, indicators: list):
        """Update panel with analysis results."""
        self.metric_confidence.set_value(f"{confidence:.1%}")
        self.metric_frames.set_value(str(frames))
        self.metric_time.set_value(f"{time_sec:.1f}s")
        
        self.explanation_text.setText(explanation or "No explanation available.")
        self.explanation_text.setStyleSheet(f"""
            color: {THEME_DARK['text_primary']};
            font-size: 13px;
            line-height: 1.6;
        """)
        
        if indicators:
            indicators_html = "<br>".join([f"• {ind}" for ind in indicators])
            self.indicators_text.setText(indicators_html)
            self.indicators_text.setStyleSheet(f"""
                color: {THEME_DARK['warning']};
                font-size: 12px;
            """)
        else:
            self.indicators_text.setText("No suspicious indicators detected.")

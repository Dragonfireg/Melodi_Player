"""
Melodi - pemutar musik desktop bergaya Spotify, dibuat dengan PySide6.

Fitur & Pembaruan Terbaru:
  - Antrean (Queue), Playlist Custom, dan Lagu Favorit.
  - Sidebar (Beranda, Cari, Favorit, Playlist, Pengaturan) + panel utama gradien membulat.
  - TWS & Tombol Media (Play/Pause, Next, Prev) GLOBAL: tombol pause di TWS tetap bekerja
    walau Melodi disembunyikan di tray / aplikasi lain sedang aktif (Windows).
  - Hapus playlist: klik kanan di sidebar, tombol "Hapus playlist" di halaman playlist, atau tombol Delete.
  - Klik cover / judul lagu yang sedang diputar -> langsung buka daftar lagu selanjutnya (antrean).
  - Tema "Musik Latar": aurora bergerak, bokeh, piringan hitam berputar, equalizer, warna mengikuti lagu & waktu.
  - System Tray (Minimize ke background, klik dua kali untuk buka).
  - Auto-Resume lagu dan posisi durasi terakhir saat aplikasi dibuka.
  - Memutar file lokal, membaca metadata otomatis.
  - Musik Online: Audius, Jamendo, dan YouTube Music.
  - Fitur Pengaturan: Bahasa, Zona Waktu, Tema, Ukuran Teks, Resolusi, dan Startup.
"""

import json
import math
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import ytmusicapi
    import yt_dlp
except ImportError:
    pass

try:
    from PySide6.QtCore import (
        QAbstractNativeEventFilter, QCoreApplication, QEvent,
        QObject, QPoint, QPointF, QRectF, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, QUrl, Signal,
    )
    from PySide6.QtGui import (
        QColor,
        QCursor,
        QDesktopServices,
        QFont,
        QIcon,
        QImage,
        QKeySequence,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPalette,
        QPen,
        QPixmap,
        QPolygonF,
        QRadialGradient,
        QShortcut,
    )
    from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaMetaData, QMediaPlayer
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QApplication,
        QButtonGroup,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QStackedWidget,
        QStyle,
        QStyledItemDelegate,
        QSystemTrayIcon,
        QTableWidget,
        QTableWidgetItem,
        QToolTip,
        QVBoxLayout,
        QWidget,
    )
except ImportError as _e:  
    _msg = f"PySide6 belum terpasang atau versinya tidak cocok:\n{_e}\n\nJalankan:  pip install -U PySide6"
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, _msg, "Melodi", 0x10)
    else:
        print(_msg)
        try:
            input("Tekan Enter untuk keluar...")
        except Exception:
            pass
    sys.exit(1)

GREEN = "#1ed760"
BG = "#000000"
PANEL = "#121212"
ELEVATED = "#1f1f1f"
HOVER = "#2a2a2a"
TEXT = "#ffffff"
SUBTEXT = "#b3b3b3"
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma"}
AUDIO_FILTER = "Audio (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.wma);;Semua file (*)"

PREFIX_AU = "au:"
PREFIX_JM = "jm:"
PREFIX_YT = "yt:"

YT_CACHE_LIMIT = 800 * 1024 * 1024          
YT_AUDIO_EXTS = (".m4a", ".webm", ".opus", ".mp4", ".mp3", ".ogg", ".aac")
STALL_SECONDS = 12                           

APP_QSS = f"""
QMainWindow, QWidget#root {{ background: {BG}; }}
QToolTip {{ background: #282828; color: #fff; border: 1px solid #3e3e3e; padding: 4px 8px; }}
QFrame#panel {{ background: {PANEL}; border: 1px solid rgba(255,255,255,0.04); border-radius: 12px; }}
QScrollArea {{ background: transparent; border: none; }}
QWidget#inner {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #4d4d4d; border-radius: 4px; min-height: 40px; margin: 0 2px; }}
QScrollBar::handle:vertical:hover {{ background: #7a7a7a; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QMenu {{ background: #282828; color: #fff; border: none; padding: 4px; }}
QMenu::item {{ padding: 8px 24px; border-radius: 4px; }}
QMenu::item:selected {{ background: #3e3e3e; }}
QSlider::groove:horizontal {{ height: 4px; background: #4d4d4d; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: #ffffff; border-radius: 2px; }}
QSlider::add-page:horizontal {{ background: #4d4d4d; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: transparent; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }}
QSlider[hot="true"]::sub-page:horizontal {{ background: {GREEN}; }}
QSlider[hot="true"]::handle:horizontal {{ background: #ffffff; }}
QComboBox {{ background: #242424; border: 1px solid transparent; border-radius: 16px; color: #fff; padding: 4px 16px; font-size: 14px; font-weight: 600; height: 32px; }}
QComboBox:hover {{ background: #2a2a2a; border-color: #3e3e3e; }}
QComboBox::drop-down {{ border: none; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{ background: #282828; color: #fff; border: none; selection-background-color: #3e3e3e; outline: 0; }}
QCheckBox {{ color: {TEXT}; font-size: 14px; spacing: 8px; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 4px; border: 2px solid #555; background: transparent; }}
QCheckBox::indicator:checked {{ background: {GREEN}; border-color: {GREEN}; }}
"""

PILL_GREEN = f"""
QPushButton {{ background: {GREEN}; color: #000; border: none; border-radius: 20px;
              padding: 10px 28px; font-weight: 700; font-size: 14px; }}
QPushButton:hover {{ background: #3be477; }}
"""
PILL_WHITE = """
QPushButton { background: #ffffff; color: #000; border: none; border-radius: 16px;
              padding: 7px 18px; font-weight: 700; font-size: 13px; }
QPushButton:hover { background: #f0f0f0; }
"""
PILL_OUTLINE = """
QPushButton { background: transparent; color: #fff; border: 1px solid #727272; border-radius: 20px;
              padding: 10px 28px; font-weight: 700; font-size: 14px; }
QPushButton:hover { border-color: #fff; }
"""

def is_remote_path(p) -> bool:
    return str(p).startswith((PREFIX_AU, PREFIX_JM, PREFIX_YT))

def data_dir() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home()) / "Melodi"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path(tempfile.gettempdir()) / "Melodi"
        base.mkdir(parents=True, exist_ok=True)
    return base

def as_list(v) -> list:
    if v is None or v == "": return []
    if isinstance(v, str): return [v]
    return list(v)

def fmt(ms: int) -> str:
    s = max(0, int(ms // 1000))
    return f"{s // 60}:{s % 60:02d}"

def greeting() -> str:
    h = datetime.now().hour
    if h < 11: return "Selamat pagi"
    if h < 15: return "Selamat siang"
    if h < 18: return "Selamat sore"
    return "Selamat malam"

@dataclass
class Track:
    path: str
    title: str
    artist: str = "Artis tidak diketahui"
    album: str = "Single"
    duration: int = 0
    cover: Optional[QImage] = None
    cover_url: str = ""
    stream_url: str = ""
    stream_time: float = 0.0

    @property
    def is_remote(self) -> bool:
        return self.path.startswith(PREFIX_AU) or self.path.startswith(PREFIX_JM) or self.path.startswith(PREFIX_YT)

    def to_dict(self) -> dict:
        return {"path": self.path, "title": self.title, "artist": self.artist, "album": self.album,
                "duration": self.duration, "cover_url": self.cover_url,
                "stream_url": "" if self.path.startswith(PREFIX_YT) else self.stream_url}

    @staticmethod
    def from_dict(d: dict) -> "Track":
        return Track(path=str(d["path"]), title=str(d.get("title") or "Tanpa judul"),
                     artist=str(d.get("artist") or "Artis tidak diketahui"), album=str(d.get("album") or "Online"),
                     duration=int(d.get("duration") or 0), cover_url=str(d.get("cover_url") or ""),
                     stream_url=str(d.get("stream_url") or ""))

    @property
    def color(self) -> QColor:
        return QColor.fromHsv(zlib.crc32(self.title.encode("utf-8")) % 360, 150, 190)

    @staticmethod
    def from_path(path: str) -> "Track":
        stem = Path(path).stem.replace("_", " ").strip()
        if " - " in stem:
            artist, title = stem.split(" - ", 1)
            return Track(path, title.strip(), artist.strip())
        return Track(path, stem)

def make_icon(name: str, color: str = SUBTEXT, size: int = 20, dot: bool = False) -> QIcon:
    ratio = 2
    pm = QPixmap(int(size * ratio), int(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    s = float(size)
    stroke = QPen(c, max(1.6, s * 0.09), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    def poly(pts):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c)
        p.drawPolygon(QPolygonF([QPointF(x * s, y * s) for x, y in pts]))

    def rect(x, y, w, h, r=1.5):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c)
        p.drawRoundedRect(QRectF(x * s, y * s, w * s, h * s), r, r)

    def line(x1, y1, x2, y2):
        p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(x1 * s, y1 * s), QPointF(x2 * s, y2 * s))

    def path_stroke(build):
        path = QPainterPath(); build(path)
        p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def speaker():
        poly([(.12, .4), (.28, .4), (.48, .2), (.48, .8), (.28, .6), (.12, .6)])

    if name == "play": poly([(.3, .16), (.3, .84), (.82, .5)])
    elif name == "pause":
        rect(.24, .16, .18, .68); rect(.58, .16, .18, .68)
    elif name == "next":
        poly([(.2, .2), (.2, .8), (.68, .5)]); rect(.72, .2, .1, .6)
    elif name == "prev":
        poly([(.8, .2), (.8, .8), (.32, .5)]); rect(.18, .2, .1, .6)
    elif name == "shuffle":
        def a(pa):
            pa.moveTo(.1 * s, .3 * s); pa.lineTo(.3 * s, .3 * s)
            pa.cubicTo(.55 * s, .3 * s, .5 * s, .7 * s, .75 * s, .7 * s); pa.lineTo(.82 * s, .7 * s)
        def b(pa):
            pa.moveTo(.1 * s, .7 * s); pa.lineTo(.3 * s, .7 * s)
            pa.cubicTo(.55 * s, .7 * s, .5 * s, .3 * s, .75 * s, .3 * s); pa.lineTo(.82 * s, .3 * s)
        path_stroke(a); path_stroke(b)
        poly([(.8, .2), (.8, .4), (.95, .3)]); poly([(.8, .6), (.8, .8), (.95, .7)])
    elif name.startswith("repeat"):
        def top(pa):
            pa.moveTo(.22 * s, .52 * s); pa.cubicTo(.22 * s, .38 * s, .3 * s, .3 * s, .42 * s, .3 * s); pa.lineTo(.7 * s, .3 * s)
        def bottom(pa):
            pa.moveTo(.78 * s, .48 * s); pa.cubicTo(.78 * s, .62 * s, .7 * s, .7 * s, .58 * s, .7 * s); pa.lineTo(.3 * s, .7 * s)
        path_stroke(top); path_stroke(bottom)
        poly([(.68, .16), (.68, .44), (.86, .3)]); poly([(.32, .56), (.32, .84), (.14, .7)])
        if name == "repeat1":
            f = QFont(); f.setBold(True); f.setPixelSize(max(6, int(s * 0.3)))
            p.setFont(f); p.setPen(c)
            p.drawText(QRectF(.3 * s, .34 * s, .4 * s, .32 * s), Qt.AlignmentFlag.AlignCenter, "1")
    elif name == "home":
        poly([(.5, .12), (.9, .46), (.8, .46), (.8, .86), (.6, .86), (.6, .6),
              (.4, .6), (.4, .86), (.2, .86), (.2, .46), (.1, .46)])
    elif name == "search":
        p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(.44 * s, .44 * s), .26 * s, .26 * s)
        line(.64, .64, .86, .86)
    elif name == "plus":
        line(.5, .2, .5, .8); line(.2, .5, .8, .5)
    elif name == "library":
        rect(.16, .2, .12, .6); rect(.36, .2, .12, .6)
        poly([(.58, .24), (.68, .2), (.86, .76), (.76, .8)])
    elif name == "headphones":
        p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(.18 * s, .14 * s, .64 * s, .7 * s), 0, 180 * 16)
        rect(.12, .5, .16, .32, 2.5); rect(.72, .5, .16, .32, 2.5)
    elif name == "volume":
        speaker(); p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(.28 * s, .3 * s, .4 * s, .4 * s), -50 * 16, 100 * 16)
        p.drawArc(QRectF(.12 * s, .14 * s, .72 * s, .72 * s), -50 * 16, 100 * 16)
    elif name == "mute":
        speaker(); line(.62, .38, .88, .62); line(.88, .38, .62, .62)
    elif name == "heart":
        def heart_out(pa):
            pa.moveTo(.5 * s, .3 * s)
            pa.cubicTo(.1 * s, -.1 * s, -.1 * s, .5 * s, .5 * s, .9 * s)
            pa.moveTo(.5 * s, .3 * s)
            pa.cubicTo(.9 * s, -.1 * s, 1.1 * s, .5 * s, .5 * s, .9 * s)
        path_stroke(heart_out)
    elif name == "heart_fill":
        def heart_f(pa):
            pa.moveTo(.5 * s, .3 * s)
            pa.cubicTo(.1 * s, -.1 * s, -.1 * s, .5 * s, .5 * s, .9 * s)
            pa.cubicTo(1.1 * s, .5 * s, .9 * s, -.1 * s, .5 * s, .3 * s)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c)
        path = QPainterPath(); heart_f(path); p.drawPath(path)
    elif name == "cloud":
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c)
        p.drawEllipse(QPointF(.34 * s, .60 * s), .16 * s, .16 * s)
        p.drawEllipse(QPointF(.52 * s, .46 * s), .20 * s, .20 * s)
        p.drawEllipse(QPointF(.70 * s, .60 * s), .16 * s, .16 * s)
        p.drawRect(QRectF(.34 * s, .56 * s, .36 * s, .20 * s))
    elif name == "queue":
        line(.2, .3, .8, .3); line(.2, .5, .8, .5); line(.2, .7, .5, .7)
        poly([(.6, .6), (.6, .8), (.8, .7)])
    elif name == "playlist":
        line(.2, .3, .8, .3); line(.2, .5, .8, .5); line(.2, .7, .5, .7)
        p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(.7 * s, .7 * s), .1 * s, .1 * s)
        line(.8, .7, .8, .5)
    elif name == "settings":
        p.setPen(stroke); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(.5 * s, .5 * s), .16 * s, .16 * s)
        p.translate(.5 * s, .5 * s)
        for _ in range(8):
            p.drawLine(QPointF(0, -.16 * s), QPointF(0, -.26 * s))
            p.rotate(45)
        p.translate(-.5 * s, -.5 * s)

    if dot:
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(c)
        p.drawEllipse(QPointF(.5 * s, .94 * s), 1.6, 1.6)
    p.end()
    return QIcon(pm)

def make_cover(track: Optional[Track], size: int, radius: int = 6) -> QPixmap:
    ratio = 2
    px = int(size * ratio)
    pm = QPixmap(px, px)
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.setClipPath(clip)

    if track and track.cover is not None and not track.cover.isNull():
        img = track.cover.scaled(px, px, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                 Qt.TransformationMode.SmoothTransformation)
        x, y = (img.width() - px) // 2, (img.height() - px) // 2
        p.drawImage(QRectF(0, 0, size, size), img, QRectF(x, y, px, px))
    else:
        base = track.color if track else QColor("#3a3a3a")
        g = QLinearGradient(0, 0, size, size)
        g.setColorAt(0, base.lighter(115))
        g.setColorAt(1, base.darker(190))
        p.fillRect(QRectF(0, 0, size, size), g)
        s = float(size)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 255, 255, 215))
        p.drawEllipse(QPointF(.40 * s, .68 * s), .12 * s, .09 * s)
        p.drawRect(QRectF(.49 * s, .28 * s, .05 * s, .40 * s))
        p.drawPolygon(QPolygonF([QPointF(.54 * s, .28 * s), QPointF(.54 * s, .40 * s),
                                 QPointF(.70 * s, .50 * s), QPointF(.70 * s, .38 * s)]))
    p.end()
    return pm

def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size); pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing); s = float(size)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(GREEN)); p.drawEllipse(QRectF(0, 0, s, s))
        p.setBrush(QColor("#000000"))
        p.drawEllipse(QPointF(.40 * s, .66 * s), .13 * s, .10 * s)
        p.drawRect(QRectF(.51 * s, .28 * s, .06 * s, .38 * s))
        p.drawPolygon(QPolygonF([QPointF(.57 * s, .28 * s), QPointF(.57 * s, .42 * s),
                                 QPointF(.74 * s, .52 * s), QPointF(.74 * s, .38 * s)]))
        p.end(); icon.addPixmap(pm)
    return icon

def green_play_pixmap(size: int = 40) -> QPixmap:
    ratio = 2
    pm = QPixmap(size * ratio, size * ratio); pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(GREEN)); p.drawEllipse(0, 0, size, size)
    icon_px = make_icon("play", "#000000", 20).pixmap(20, 20)
    p.drawPixmap(10, 10, icon_px); p.end()
    return pm

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Melodi/1.0"
APP_NAME = "MelodiPlayer"
DEFAULT_JAMENDO_ID = "56d30c95"

class OnlineError(Exception):
    pass

def _http(url: str, headers: Optional[dict] = None, timeout: int = 15, max_bytes: int = 4_000_000) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(max_bytes)
    except urllib.error.HTTPError as e:
        raise OnlineError(f"HTTP {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise OnlineError(f"Gagal koneksi internet ({getattr(e, 'reason', e)})") from None

class OnlineClient:
    def __init__(self):
        self.jamendo_id = DEFAULT_JAMENDO_ID
        self.audius_host = None
        self._lock = threading.Lock()
        self._dl_locks: dict = {}
        self.cache_dir = self._make_cache_dir()

    @staticmethod
    def _make_cache_dir() -> Path:
        base = Path(os.environ.get("APPDATA") or Path.home()) / "Melodi" / "cache"
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError:
            base = Path(tempfile.gettempdir()) / "MelodiCache"
            base.mkdir(parents=True, exist_ok=True)
        return base

    def _yt_lock(self, vid: str) -> threading.Lock:
        with self._lock:
            return self._dl_locks.setdefault(vid, threading.Lock())

    def cached_yt_file(self, vid: str) -> str:
        try:
            for f in self.cache_dir.glob(f"{vid}.*"):
                if f.suffix.lower() in YT_AUDIO_EXTS and f.is_file() and f.stat().st_size > 0:
                    return str(f)
        except OSError:
            pass
        return ""

    def delete_cached(self, vid: str):
        try:
            for f in self.cache_dir.glob(f"{vid}.*"):
                try: f.unlink()
                except OSError: pass
        except OSError:
            pass

    def prune_cache(self, keep_ids: set, limit: int = YT_CACHE_LIMIT):
        try:
            files = [f for f in self.cache_dir.iterdir() if f.is_file()]
            total = sum(f.stat().st_size for f in files)
            if total <= limit: return
            now = time.time()
            old = [f for f in files if f.name.split(".")[0] not in keep_ids and now - f.stat().st_mtime > 600]
            for f in sorted(old, key=lambda x: x.stat().st_mtime):
                if total <= limit: break
                try:
                    sz = f.stat().st_size; f.unlink(); total -= sz
                except OSError:
                    pass
        except OSError:
            pass

    def fetch_yt_meta(self, video_id: str) -> dict:
        try:
            from ytmusicapi import YTMusic
            vd = (YTMusic().get_song(video_id) or {}).get("videoDetails") or {}
        except Exception as e:
            raise OnlineError(f"Metadata YT gagal: {e}") from None
        thumbs = (vd.get("thumbnail") or {}).get("thumbnails") or []
        return {"title": vd.get("title") or "", "artist": vd.get("author") or "",
                "duration": int(vd.get("lengthSeconds") or 0) * 1000,
                "cover_url": thumbs[-1].get("url", "") if thumbs else ""}

    def prepare_yt_audio(self, video_id: str) -> dict:
        with self._yt_lock(video_id):
            cached = self.cached_yt_file(video_id)
            if cached:
                return {"file": cached, "url": ""}
            try:
                import yt_dlp
            except ImportError:
                raise OnlineError("Pustaka yt-dlp belum terpasang. Jalankan: pip install yt-dlp")
            opts = {
                "quiet": True, "no_warnings": True, "noplaylist": True, "noprogress": True,
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": str(self.cache_dir / "%(id)s.%(ext)s"),
                "http_chunk_size": 10 * 1024 * 1024,
                "retries": 5, "fragment_retries": 5, "socket_timeout": 15,
                "continuedl": True,
            }
            url = f"https://music.youtube.com/watch?v={video_id}"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                f = self.cached_yt_file(video_id)
                if f: return {"file": f, "url": ""}
                if info and info.get("url"): return {"file": "", "url": info["url"]}
            except Exception:
                pass
            try:
                return {"file": "", "url": self.resolve_yt_stream(video_id)}
            except OnlineError as e:
                raise OnlineError(f"{e} (coba perbarui: pip install -U yt-dlp)") from None

    def configure(self, jamendo_id: str):
        with self._lock:
            self.jamendo_id = jamendo_id.strip() or DEFAULT_JAMENDO_ID

    def get_audius_host(self) -> str:
        with self._lock:
            if self.audius_host: return self.audius_host
        try:
            raw = _http("https://api.audius.co")
            data = json.loads(raw)
            host = random.choice(data["data"])
            with self._lock: self.audius_host = host
            return host
        except Exception:
            fallback = "https://discoveryprovider.audius.co"
            with self._lock: self.audius_host = fallback
            return fallback

    def search(self, query: str, provider: str, limit: int = 20) -> list:
        prov = provider.lower()
        if prov == "audius": return self._search_audius(query, limit)
        elif prov == "youtube music": return self._search_yt(query, limit)
        return self._search_jamendo(query, limit)

    def _search_audius(self, query: str, limit: int) -> list:
        host = self.get_audius_host()
        url = f"{host}/v1/tracks/search?query={urllib.parse.quote(query)}&app_name={APP_NAME}"
        try:
            raw = _http(url)
            data = json.loads(raw)
        except Exception as e:
            raise OnlineError(f"Kesalahan API Audius: {e}")
            
        out = []
        for t in data.get("data", [])[:limit]:
            if not t.get("is_streamable"): continue
            tid = str(t.get("id"))
            title = t.get("title") or "Tanpa judul"
            artist = (t.get("user") or {}).get("name") or "Artis tidak diketahui"
            dur = int(t.get("duration", 0)) * 1000
            cover = (t.get("artwork") or {}).get("480x480") or (t.get("artwork") or {}).get("150x150") or ""
            stream_url = f"{host}/v1/tracks/{tid}/stream?app_name={APP_NAME}"
            out.append({"id": PREFIX_AU + tid, "title": title, "artist": artist, "album": "Audius",
                        "duration": dur, "cover_url": cover, "stream_url": stream_url})
        return out

    def _search_jamendo(self, query: str, limit: int) -> list:
        url = f"https://api.jamendo.com/v3.0/tracks/?client_id={self.jamendo_id}&format=json&search={urllib.parse.quote(query)}&limit={limit}"
        try:
            raw = _http(url)
            data = json.loads(raw)
        except Exception as e:
            raise OnlineError(f"Kesalahan API Jamendo: {e}")
            
        out = []
        for t in data.get("results", [])[:limit]:
            tid = str(t.get("id"))
            title = t.get("name") or "Tanpa judul"
            artist = t.get("artist_name") or "Artis tidak diketahui"
            dur = int(t.get("duration", 0)) * 1000
            cover = t.get("image") or ""
            stream_url = t.get("audio") or ""
            if stream_url:
                out.append({"id": PREFIX_JM + tid, "title": title, "artist": artist, "album": "Jamendo",
                            "duration": dur, "cover_url": cover, "stream_url": stream_url})
        return out

    def _search_yt(self, query: str, limit: int) -> list:
        try:
            from ytmusicapi import YTMusic
        except ImportError:
            raise OnlineError("Pustaka ytmusicapi belum terpasang. Jalankan di Terminal: pip install ytmusicapi yt-dlp")
            
        try:
            yt = YTMusic()
            res = yt.search(query, filter="songs", limit=limit)
        except Exception as e:
            raise OnlineError(f"Kesalahan API YouTube: {e}")
            
        out = []
        for r in res:
            vid = r.get("videoId")
            if not vid: continue
            
            title = r.get("title") or "Tanpa judul"
            artists_list = r.get("artists") or []
            artist = ", ".join([a.get("name", "") for a in artists_list]) if artists_list else "Artis tidak diketahui"
            album = (r.get("album") or {}).get("name") or "YouTube Music"
            
            dur = int(r.get("duration_seconds") or 0) * 1000
            
            thumbs = r.get("thumbnails") or []
            cover = thumbs[-1].get("url") if thumbs else ""
            
            out.append({"id": PREFIX_YT + vid, "title": title, "artist": artist, "album": album,
                        "duration": dur, "cover_url": cover, "stream_url": ""})
        return out

    def resolve_yt_stream(self, video_id: str) -> str:
        try:
            import yt_dlp
        except ImportError:
            raise OnlineError("Pustaka yt-dlp belum terpasang. Jalankan di Terminal: pip install yt-dlp")
            
        opts = {
            "quiet": True, "no_warnings": True, "skip_download": True, 
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "noplaylist": True, "socket_timeout": 15
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"https://music.youtube.com/watch?v={video_id}", download=False)
                return info["url"]
        except Exception as e:
            raise OnlineError(f"Gagal memproses link stream: {str(e)[:100]}")

    def fetch_bytes(self, url: str) -> bytes:
        return _http(url, timeout=10, max_bytes=2_000_000)

class _WorkerSignals(QObject):
    done = Signal(object, object)     
    failed = Signal(object, str)      

class Worker(QRunnable):
    def __init__(self, fn, ctx, *args):
        super().__init__()
        self.fn, self.ctx, self.args = fn, ctx, args
        self.signals = _WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args)
        except Exception as e:
            self.signals.failed.emit(self.ctx, str(e) or e.__class__.__name__)
        else:
            self.signals.done.emit(self.ctx, result)


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full = text
        self.setMinimumWidth(10)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._apply()
    def setText(self, text: str):
        self._full = text; self.setToolTip(text); self._apply()
    def resizeEvent(self, e):
        self._apply(); super().resizeEvent(e)
    def _apply(self):
        el = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(self.width(), 10))
        super().setText(el)

class ClickableCover(QLabel):
    """Cover yang bisa diklik (kursor tangan)."""
    clicked = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

class ClickableElidedLabel(ElidedLabel):
    """Label teks terpotong (…) yang bisa diklik."""
    clicked = Signal()
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def setText(self, text: str):
        self._full = text
        self.setToolTip(f"{text}\nKlik untuk melihat daftar lagu selanjutnya" if text else "")
        self._apply()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

class IconButton(QPushButton):
    def __init__(self, name: str, size: int = 20, base: str = SUBTEXT, hover: str = TEXT, parent=None):
        super().__init__(parent)
        self.name, self.base, self.hover_color = name, base, hover
        self.active = False; self._hov = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(size, size))
        self.setFixedSize(size + 14, size + 14)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}")
        self._refresh()
    def set_name(self, name: str):
        self.name = name; self._refresh()
    def set_active(self, on: bool):
        self.active = on; self._refresh()
    def enterEvent(self, e):
        self._hov = True; self._refresh(); super().enterEvent(e)
    def leaveEvent(self, e):
        self._hov = False; self._refresh(); super().leaveEvent(e)
    def _refresh(self):
        color = GREEN if self.active else (self.hover_color if self._hov else self.base)
        self.setIcon(make_icon(self.name, color, self.iconSize().width(), dot=self.active))

class NavButton(QPushButton):
    def __init__(self, icon_name: str, text: str):
        super().__init__("   " + text)
        self.icon_name = icon_name; self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(24, 24)); self.setFixedHeight(44)
        self.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;text-align:left;padding-left:12px;"
            f"color:{SUBTEXT};font-weight:700;font-size:15px;}}"
            f"QPushButton:hover{{color:#fff;}} QPushButton:checked{{color:#fff;}}"
        )
        self.toggled.connect(self._refresh); self._refresh()
    def _refresh(self, *_):
        self.setIcon(make_icon(self.icon_name, "#ffffff" if self.isChecked() else SUBTEXT, 24))

class ClickSlider(QSlider):
    seek = Signal(int)
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("hot", False)
    def _set_hot(self, hot: bool):
        self.setProperty("hot", hot); self.style().unpolish(self); self.style().polish(self)
    def enterEvent(self, e):
        self._set_hot(True); super().enterEvent(e)
    def leaveEvent(self, e):
        self._set_hot(False); super().leaveEvent(e)
    def _value_at(self, x: float) -> int:
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), int(x), max(1, self.width()))
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True); self.setValue(self._value_at(e.position().x())); e.accept()
    def mouseMoveEvent(self, e):
        if self.isSliderDown(): self.setValue(self._value_at(e.position().x())); e.accept()
    def mouseReleaseEvent(self, e):
        if self.isSliderDown():
            self.setSliderDown(False); self.seek.emit(self.value()); e.accept()

class TrackCell(QWidget):
    def __init__(self, track: Track, cover_size: int = 40, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        h = QHBoxLayout(self); h.setContentsMargins(8, 0, 8, 0); h.setSpacing(12)
        cover = QLabel(); cover.setFixedSize(cover_size, cover_size)
        cover.setPixmap(make_cover(track, cover_size, 4))
        v = QVBoxLayout(); v.setSpacing(1); v.addStretch()
        self.title = ElidedLabel(track.title)
        self.artist = ElidedLabel(track.artist)
        self.artist.setStyleSheet(f"color:{SUBTEXT};font-size:12px;background:transparent;")
        v.addWidget(self.title); v.addWidget(self.artist); v.addStretch()
        h.addWidget(cover); h.addLayout(v, 1)
        self.set_active(False)
    def set_active(self, on: bool):
        color = GREEN if on else TEXT
        self.title.setStyleSheet(f"color:{color};font-weight:600;font-size:14px;background:transparent;")

class HoverDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        table = self.parent()
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if index.row() == table.hover_row and not selected:
            painter.fillRect(option.rect, QColor(HOVER))
        super().paint(painter, option, index)

class TrackTable(QTableWidget):
    playRequested = Signal(str)
    removeRequested = Signal(list)
    actionRequested = Signal(str, list)
    ROW_H = 56

    def __init__(self, parent=None):
        super().__init__(0, 4, parent)
        self.hover_row = -1
        self.allow_library = False
        self.cells: dict[str, TrackCell] = {}
        self.setHorizontalHeaderLabels(["#", "Judul", "Album", "Durasi"])
        self.verticalHeader().setVisible(False); self.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.setShowGrid(False); self.setCornerButtonEnabled(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setMouseTracking(True); self.setMouseTracking(True)
        self.setItemDelegate(HoverDelegate(self))

        hh = self.horizontalHeader()
        hh.setHighlightSections(False); hh.setSectionsClickable(False)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hh.resizeSection(0, 56); hh.resizeSection(2, 220); hh.resizeSection(3, 100)
        self.horizontalHeaderItem(3).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.setStyleSheet(f"""
            QTableWidget {{ background: transparent; border: none; color: {SUBTEXT}; outline: 0; font-size: 14px; }}
            QTableWidget::item {{ padding: 0 8px; border: none; }}
            QTableWidget::item:selected {{ background: #333333; color: #ffffff; }}
            QHeaderView {{ background: transparent; }}
            QHeaderView::section {{ background: transparent; color: {SUBTEXT}; border: none;
                                    border-bottom: 1px solid #2a2a2a; padding: 6px 8px; font-weight: 600; }}
        """)
        self.cellDoubleClicked.connect(self._on_double)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        delete_sc = QShortcut(QKeySequence("Delete"), self)
        delete_sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        delete_sc.activated.connect(lambda: self.removeRequested.emit(self.selected_paths()))

    def _on_double(self, row, _col):
        item = self.item(row, 0)
        if item: self.playRequested.emit(item.data(Qt.ItemDataRole.UserRole))

    def selected_paths(self) -> list:
        out = []
        for r in sorted({i.row() for i in self.selectedIndexes()}):
            it = self.item(r, 0)
            if it: out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def _context_menu(self, pos):
        row = self.rowAt(pos.y())
        if row < 0: return
        if not self.selectionModel().isRowSelected(row):
            self.clearSelection(); self.selectRow(row)
        paths = self.selected_paths()
        if not paths: return
        
        menu = QMenu(self)
        play = menu.addAction("Putar")
        play.setEnabled(len(paths) == 1)
        play.triggered.connect(lambda _=False: self.playRequested.emit(paths[0]))
        if self.allow_library:
            menu.addAction("Tambahkan ke Koleksi").triggered.connect(lambda _=False: self.actionRequested.emit("library", paths))
        menu.addAction("Tambahkan ke Antrean").triggered.connect(lambda _=False: self.actionRequested.emit("queue", paths))
        menu.addAction("Tambahkan ke Favorit").triggered.connect(lambda _=False: self.actionRequested.emit("fav", paths))
        menu.addAction("Tambahkan ke Playlist...").triggered.connect(lambda _=False: self.actionRequested.emit("playlist", paths))
        menu.addSeparator()
        rm = menu.addAction("Hapus dari daftar ini")
        rm.triggered.connect(lambda _=False: self.removeRequested.emit(paths))
        menu.exec(self.viewport().mapToGlobal(pos))

    def mouseMoveEvent(self, e):
        row = self.rowAt(int(e.position().y()))
        if row != self.hover_row:
            self.hover_row = row; self.viewport().update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self.hover_row = -1; self.viewport().update(); super().leaveEvent(e)

    def set_tracks(self, tracks: list):
        self.clearContents(); self.cells.clear(); self.setRowCount(len(tracks))
        for row, t in enumerate(tracks):
            num = QTableWidgetItem(str(row + 1))
            num.setData(Qt.ItemDataRole.UserRole, t.path)
            num.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 0, num)
            cell = TrackCell(t, 40)
            self.setCellWidget(row, 1, cell); self.cells[t.path] = cell
            self.setItem(row, 1, QTableWidgetItem(""))
            self.setItem(row, 2, QTableWidgetItem(t.album))
            dur = QTableWidgetItem(fmt(t.duration) if t.duration else "--:--")
            dur.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 3, dur)
        self.setFixedHeight(self.horizontalHeader().sizeHint().height() + len(tracks) * self.ROW_H + 4)

    def set_playing(self, path: str):
        for row in range(self.rowCount()):
            it = self.item(row, 0)
            if not it: continue
            playing = (it.data(Qt.ItemDataRole.UserRole) == path)
            it.setText("♪" if playing else str(row + 1))
            it.setForeground(QColor(GREEN if playing else SUBTEXT))
        for p, cell in self.cells.items():
            cell.set_active(p == path)

# ═══════════════════════════════════════════════════════════════════════════
#  TEMA "MUSIK LATAR" — aurora bergerak, piringan hitam berputar, equalizer
# ═══════════════════════════════════════════════════════════════════════════
HEADER_H = 360


def ambient_accent() -> str:
    """Warna dasar suasana sesuai waktu (dipakai saat belum ada lagu yang diputar)."""
    h = datetime.now().hour
    if h < 11: return "#6b4e1e"      # pagi  : hangat keemasan
    if h < 15: return "#1f5a56"      # siang : teal segar
    if h < 18: return "#6b3a2a"      # sore  : senja terakota
    return "#2a2560"                 # malam : indigo tenang


def tagline() -> str:
    h = datetime.now().hour
    if h < 11: return "Mulai harimu dengan alunan yang tenang."
    if h < 15: return "Teman fokus di tengah harimu."
    if h < 18: return "Santai sejenak, biarkan musik mengalun."
    return "Waktunya rileks bersama alunan malam."


class AmbientClock(QObject):
    """Satu jam animasi bersama. Hanya berdetak saat musik diputar DAN jendela terlihat,
    jadi tidak memakan CPU ketika di-minimize ke tray atau dijeda."""
    tick = Signal(float)

    def __init__(self):
        super().__init__()
        self.t = 3.0
        self.playing = False
        self.active = True
        self._cool = 0.0
        self._last = time.monotonic()
        self._timer = QTimer(self); self._timer.setInterval(50)      # ±20 fps
        self._timer.timeout.connect(self._step)

    def configure(self, playing: bool, visible: bool):
        if self.playing and not playing:
            self._cool = 1.4            # beri waktu animasi mengendap (equalizer turun, piringan melambat)
        self.playing, self.active = playing, visible
        self._sync()

    def _sync(self):
        run = self.active and (self.playing or self._cool > 0)
        if run and not self._timer.isActive():
            self._last = time.monotonic(); self._timer.start()
        elif not run and self._timer.isActive():
            self._timer.stop()

    def _step(self):
        now = time.monotonic()
        dt = min(0.2, now - self._last); self._last = now
        self.t += dt * (1.0 if self.playing else 0.3)
        if not self.playing: self._cool -= dt
        self.tick.emit(dt)
        if not self.playing and self._cool <= 0: self._sync()


_CLOCK: Optional[AmbientClock] = None

def get_clock() -> AmbientClock:
    global _CLOCK
    if _CLOCK is None: _CLOCK = AmbientClock()
    return _CLOCK


def paint_ambient(p: QPainter, rect: QRectF, accent: QColor, t: float):
    """Lukis 'aurora' lembut + bokeh melayang di area header halaman."""
    w, h = rect.width(), rect.height()
    if w <= 0 or h <= 0: return
    hue = max(0, accent.hsvHue()); sat = accent.hsvSaturation(); val = accent.value()
    s2 = sat if sat < 25 else min(255, sat + 40)            # abu-abu tetap netral
    v2 = min(255, int(val * 1.9) + 50)
    cols = [QColor.fromHsv((hue + d) % 360, s2, v2) for d in (0, 32, -32)]

    p.save()
    p.setClipRect(rect, Qt.ClipOperation.IntersectClip)
    p.setPen(Qt.PenStyle.NoPen)
    for i, col in enumerate(cols):                           # gumpalan cahaya yang melayang pelan
        cx = rect.left() + w * (0.18 + 0.32 * i + 0.10 * math.sin(t * 0.30 + i * 2.1))
        cy = rect.top() + h * (0.30 + 0.16 * math.cos(t * 0.23 + i * 1.7))
        r = max(w, 700.0) * (0.26 + 0.03 * math.sin(t * 0.45 + i))
        g = QRadialGradient(QPointF(cx, cy), r)
        c0 = QColor(col); c0.setAlpha(80)
        c1 = QColor(col); c1.setAlpha(0)
        g.setColorAt(0.0, c0); g.setColorAt(1.0, c1)
        p.setBrush(g); p.drawEllipse(QPointF(cx, cy), r, r)

    for i in range(9):                                       # bokeh naik perlahan
        frac = (t * (0.010 + 0.004 * (i % 4)) + i * 0.113) % 1.0
        x = rect.left() + w * ((i * 0.137 + 0.07) % 1.0) + 14 * math.sin(t * 0.5 + i)
        y = rect.top() + h * (1.0 - frac)
        rad = 5 + (i * 7) % 15
        a = int(80 * math.sin(math.pi * frac))
        base = QColor(cols[i % 3]).lighter(165)
        c_in = QColor(base); c_in.setAlpha(int(a * 0.45))
        c_mid = QColor(base); c_mid.setAlpha(a)
        c_out = QColor(base); c_out.setAlpha(0)
        g = QRadialGradient(QPointF(x, y), rad)
        g.setColorAt(0.0, c_in); g.setColorAt(0.75, c_mid); g.setColorAt(1.0, c_out)
        p.setBrush(g); p.drawEllipse(QPointF(x, y), rad, rad)
    p.restore()

    fade = QLinearGradient(0, rect.top() + h * 0.4, 0, rect.bottom())      # lebur ke warna panel di bawah
    f0 = QColor(PANEL); f0.setAlpha(0)
    fade.setColorAt(0.0, f0); fade.setColorAt(1.0, QColor(PANEL))
    p.fillRect(rect, fade)


class EqualizerBars(QWidget):
    """Batang equalizer animasi (dekoratif). Naik-turun saat lagu diputar, mengendap saat dijeda."""
    def __init__(self, bars: int = 5, bar_w: int = 3, gap: int = 2, height: int = 18, color: str = GREEN, parent=None):
        super().__init__(parent)
        self._n, self._bw, self._gap, self._color = bars, bar_w, gap, QColor(color)
        self._vals = [0.12] * bars
        self._targets = [0.12] * bars
        self._acc = 0.0
        self._playing = False
        self.setFixedSize(bars * bar_w + (bars - 1) * gap, height)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        get_clock().tick.connect(self._on_tick)

    def set_playing(self, on: bool):
        self._playing = on

    def _on_tick(self, dt: float):
        self._acc += dt
        if self._acc >= 0.11:
            self._acc = 0.0
            n = self._n
            self._targets = [
                (random.uniform(0.2, 1.0) * (0.55 + 0.45 * math.sin(math.pi * (i + 0.5) / n))) if self._playing else 0.12
                for i in range(n)
            ]
        k = min(1.0, dt * 12)
        for i in range(self._n):
            self._vals[i] += (self._targets[i] - self._vals[i]) * k
        if self.isVisible(): self.update()

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        H = float(self.height())
        for i, v in enumerate(self._vals):
            bh = max(3.0, v * H)
            x = i * (self._bw + self._gap)
            g = QLinearGradient(0, H - bh, 0, H)
            g.setColorAt(0.0, self._color.lighter(135)); g.setColorAt(1.0, self._color)
            p.setBrush(g)
            p.drawRoundedRect(QRectF(x, H - bh, self._bw, bh), self._bw / 2, self._bw / 2)


class VinylDisc(QWidget):
    """Piringan hitam yang berputar saat musik diputar; label tengahnya adalah cover lagu."""
    clicked = Signal()
    def __init__(self, size: int = 180, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._angle = 0.0
        self._speed = 0.0
        self._playing = False
        self._accent = QColor(GREEN)
        self._label = QPixmap()
        self._rebuild_label(None)
        get_clock().tick.connect(self._on_tick)

    def _rebuild_label(self, track: Optional[Track]):
        R = self.width() / 2 - 6
        ls = max(20, int(R * 0.84))
        self._label = make_cover(track, ls, ls // 2)

    def set_track(self, track: Optional[Track]):
        self._accent = QColor(track.color) if track else QColor(GREEN)
        self._rebuild_label(track); self.update()

    def set_playing(self, on: bool):
        self._playing = on

    def _on_tick(self, dt: float):
        target = 1.0 if self._playing else 0.0
        self._speed += (target - self._speed) * min(1.0, dt * 3.0)
        if self._speed < 0.01 and not self._playing:
            self._speed = 0.0; return
        self._angle = (self._angle + self._speed * 45.0 * dt) % 360.0
        if self.isVisible(): self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        W = float(self.width()); c = QPointF(W / 2, W / 2); R = W / 2 - 6

        glow = QRadialGradient(c, W / 2)                                  # cahaya lembut warna lagu
        g0 = QColor(self._accent); g0.setAlpha(95)
        g1 = QColor(self._accent); g1.setAlpha(0)
        glow.setColorAt(0.62, g0); glow.setColorAt(1.0, g1)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(glow); p.drawEllipse(c, W / 2, W / 2)

        p.save()
        p.translate(c); p.rotate(self._angle)
        disc = QRadialGradient(QPointF(0, 0), R)
        disc.setColorAt(0.0, QColor("#202020")); disc.setColorAt(1.0, QColor("#060606"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(disc); p.drawEllipse(QPointF(0, 0), R, R)
        p.setPen(QPen(QColor(255, 255, 255, 16), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        r = R * 0.46
        while r < R - 3:                                                   # alur piringan
            p.drawEllipse(QPointF(0, 0), r, r); r += 4.5
        lr = self._label.width() / self._label.devicePixelRatio() / 2
        p.drawPixmap(QRectF(-lr, -lr, 2 * lr, 2 * lr), self._label, QRectF(self._label.rect()))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(PANEL)); p.drawEllipse(QPointF(0, 0), 5, 5)
        p.restore()

        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 255, 255, 14))   # kilau tetap (tidak ikut berputar)
        box = QRectF(c.x() - R, c.y() - R, 2 * R, 2 * R)
        p.drawPie(box, 25 * 16, 40 * 16); p.drawPie(box, 205 * 16, 40 * 16)
        p.setPen(QPen(QColor(255, 255, 255, 34), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, R, R)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class NowPlayingHero(QFrame):
    """Kartu 'Sedang diputar' di Beranda: piringan hitam, judul, equalizer, dan perangkat output (TWS)."""
    toggleRequested = Signal()
    queueRequested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("hero")
        self.setStyleSheet("QFrame#hero{background:rgba(255,255,255,0.05);"
                           "border:1px solid rgba(255,255,255,0.07);border-radius:18px;}")
        self._playing = False; self._has_track = False
        h = QHBoxLayout(self); h.setContentsMargins(26, 22, 30, 22); h.setSpacing(30)
        self.disc = VinylDisc(180)
        h.addWidget(self.disc, 0, Qt.AlignmentFlag.AlignVCenter)

        v = QVBoxLayout(); v.setSpacing(4)
        self.kicker = QLabel("SIAP DIPUTAR")
        self.kicker.setStyleSheet(f"color:{GREEN};font-size:11px;font-weight:800;")
        self.title = ClickableElidedLabel("Belum ada lagu")
        self.title.setStyleSheet("QLabel{color:#fff;font-size:30px;font-weight:800;}"
                                 "QLabel:hover{text-decoration:underline;}")
        self.title.clicked.connect(self.queueRequested); self.disc.clicked.connect(self.queueRequested)
        self.artist = ElidedLabel("Pilih lagu untuk mulai")
        self.artist.setStyleSheet(f"color:{SUBTEXT};font-size:15px;")
        self.eq = EqualizerBars(20, 4, 3, 34, GREEN)

        self.btn = QPushButton("Putar"); self.btn.setStyleSheet(PILL_GREEN)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor); self.btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn.clicked.connect(self.toggleRequested)
        self.chip_icon = QLabel(); self.chip_icon.setPixmap(make_icon("headphones", SUBTEXT, 16).pixmap(16, 16))
        self.chip = ElidedLabel(""); self.chip.setStyleSheet(f"color:{SUBTEXT};font-size:12px;")
        row = QHBoxLayout(); row.setSpacing(8)
        row.addWidget(self.btn); row.addSpacing(8); row.addWidget(self.chip_icon); row.addWidget(self.chip, 1)

        v.addStretch(); v.addWidget(self.kicker); v.addWidget(self.title); v.addWidget(self.artist)
        v.addSpacing(10); v.addWidget(self.eq, 0, Qt.AlignmentFlag.AlignLeft)
        v.addSpacing(12); v.addLayout(row); v.addStretch()
        h.addLayout(v, 1)

    def _refresh_kicker(self):
        self.kicker.setText("SEDANG DIPUTAR" if self._playing else ("DIJEDA" if self._has_track else "SIAP DIPUTAR"))

    def set_track(self, t: Optional[Track]):
        self._has_track = t is not None
        self.disc.set_track(t)
        self.title.setText(t.title if t else "Belum ada lagu")
        self.artist.setText(t.artist if t else "Pilih lagu untuk mulai")
        self._refresh_kicker()

    def set_playing(self, on: bool):
        self._playing = on
        self.disc.set_playing(on); self.eq.set_playing(on)
        self.btn.setText("Jeda" if on else "Putar")
        self._refresh_kicker()

    def set_device(self, name: str, keys_on: bool):
        self.chip.setText(name + ("  •  Kontrol TWS aktif" if keys_on else ""))


class PlayerBar(QFrame):
    """Bilah pemutar dengan latar gradasi yang mengikuti warna lagu."""
    def __init__(self):
        super().__init__()
        self.accent = QColor(ambient_accent())

    def set_accent(self, color: QColor):
        self.accent = QColor(color); self.update()

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath(); path.addRoundedRect(r, 14, 14)
        p.setClipPath(path)
        p.fillRect(r, QColor(PANEL))
        g = QLinearGradient(r.topLeft(), r.topRight())
        a0 = QColor(self.accent); a0.setAlpha(230)
        a1 = QColor(self.accent); a1.setAlpha(0)
        g.setColorAt(0.0, a0); g.setColorAt(0.7, a1)
        p.fillRect(r, g)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 20), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)


# ═══════════════════════════════════════════════════════════════════════════
#  KONTROL TWS / TOMBOL MEDIA GLOBAL (Windows)
# ═══════════════════════════════════════════════════════════════════════════
class GlobalMediaKeys(QAbstractNativeEventFilter):
    """Menangkap tombol media (Play/Pause, Next, Prev, Stop) secara GLOBAL.

    Tombol di TWS/earbuds Bluetooth dikirim Windows sebagai tombol media. QShortcut biasa
    hanya menerimanya saat jendela Melodi sedang aktif; dengan RegisterHotKey, tombol tetap
    bekerja ketika Melodi disembunyikan di tray atau aplikasi lain yang sedang aktif."""
    WM_HOTKEY = 0x0312
    MOD_NOREPEAT = 0x4000
    KEYS = (("toggle", 0xB3, "Putar/Jeda"), ("next", 0xB0, "Berikutnya"),
            ("prev", 0xB1, "Sebelumnya"), ("stop", 0xB2, "Stop"))

    def __init__(self, callback):
        super().__init__()
        self._cb = callback
        self._map: dict = {}
        self._failed: list = []
        self._installed = False

    @property
    def active(self) -> bool:
        return bool(self._map)

    def start(self) -> bool:
        if sys.platform != "win32" or self._installed:
            return self.active
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            user32.RegisterHotKey.restype = wintypes.BOOL
        except Exception:
            return False
        self._map.clear(); self._failed = []
        for i, (name, vk, label) in enumerate(self.KEYS):
            hid = 0x5A00 + i
            if user32.RegisterHotKey(None, hid, self.MOD_NOREPEAT, vk): self._map[hid] = name
            else: self._failed.append(label)
        if self._map:
            QCoreApplication.instance().installNativeEventFilter(self)
            self._installed = True
        return self.active

    def stop(self):
        if sys.platform != "win32": return
        try:
            import ctypes
            for hid in list(self._map): ctypes.windll.user32.UnregisterHotKey(None, hid)
        except Exception:
            pass
        self._map.clear()
        if self._installed:
            try: QCoreApplication.instance().removeNativeEventFilter(self)
            except Exception: pass
            self._installed = False

    def nativeEventFilter(self, event_type, message):
        try:
            if bytes(event_type) == b"windows_generic_MSG":
                import ctypes
                from ctypes import wintypes
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == self.WM_HOTKEY and msg.wParam in self._map:
                    name = self._map[msg.wParam]
                    QTimer.singleShot(0, lambda n=name: self._cb(n))
                    return True, 0
        except Exception:
            pass
        return False, 0

    def status_text(self, enabled: bool) -> str:
        if sys.platform != "win32":
            return "Kontrol global hanya tersedia di Windows. Di sistem lain, tombol media bekerja saat jendela Melodi aktif."
        if not enabled:
            return "Nonaktif — tombol TWS hanya bekerja saat jendela Melodi sedang aktif."
        if self.active and not self._failed:
            return ("Aktif — tombol Putar/Jeda, Berikutnya, dan Sebelumnya di TWS, earbuds, atau keyboard "
                    "mengendalikan Melodi, bahkan saat aplikasi disembunyikan di tray.")
        if self.active:
            return f"Aktif sebagian — tombol {', '.join(self._failed)} sedang dipakai aplikasi lain."
        return ("Gagal diaktifkan — tombol media sedang dipakai aplikasi lain (mis. Spotify atau browser). "
                "Tutup aplikasi itu, lalu matikan dan nyalakan lagi opsi ini.")


class GradientPage(QWidget):
    def __init__(self, accent: str = "#1f4e3d"):
        super().__init__()
        self.accent = QColor(accent)
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)
        self.scroller = QScrollArea()
        self.scroller.setWidgetResizable(True); self.scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.scroller.viewport().setAutoFillBackground(False)
        self.inner = QWidget(); self.inner.setObjectName("inner")
        self.scroller.setWidget(self.inner); self.inner.setAutoFillBackground(False)
        lay.addWidget(self.scroller)
        self.scroller.verticalScrollBar().valueChanged.connect(lambda _v: self.update())
        get_clock().tick.connect(self._on_tick)

    def set_accent(self, color: QColor):
        self.accent = QColor(color); self.update()

    def _on_tick(self, _dt: float):
        if not self.isVisible(): return
        h = int(HEADER_H - self.scroller.verticalScrollBar().value())
        if h > 0: self.update(0, 0, self.width(), h)          # hanya area header yang digambar ulang

    def paintEvent(self, _e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath(); clip.addRoundedRect(QRectF(self.rect()), 12, 12); p.setClipPath(clip)
        p.fillRect(self.rect(), QColor(PANEL))
        off = self.scroller.verticalScrollBar().value()
        header = QRectF(0, -off, self.width(), HEADER_H)
        g = QLinearGradient(0, -off, 0, -off + HEADER_H)
        g.setColorAt(0, self.accent); g.setColorAt(1, QColor(PANEL))
        p.fillRect(header, g)
        if header.bottom() > 0:
            paint_ambient(p, header, self.accent, get_clock().t)

class QuickCard(QFrame):
    clicked = Signal(str)
    def __init__(self, track: Track):
        super().__init__()
        self.path = track.path
        self.setObjectName("quick")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        self.setStyleSheet("#quick{background:rgba(255,255,255,0.08);border-radius:6px;}"
                           "#quick:hover{background:rgba(255,255,255,0.18);}")
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 12, 0); h.setSpacing(12)
        cover = QLabel(); cover.setFixedSize(64, 64); cover.setPixmap(make_cover(track, 64, 6))
        title = ElidedLabel(track.title)
        title.setStyleSheet("color:#fff;font-weight:700;font-size:14px;background:transparent;")
        self.btn = QLabel(); self.btn.setFixedSize(40, 40)
        self._on = green_play_pixmap(40); self._off = QPixmap()
        h.addWidget(cover); h.addWidget(title, 1); h.addWidget(self.btn)
    def enterEvent(self, e):
        self.btn.setPixmap(self._on); super().enterEvent(e)
    def leaveEvent(self, e):
        self.btn.setPixmap(self._off); super().leaveEvent(e)
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self.clicked.emit(self.path)

class EmptyState(QWidget):
    addFiles = Signal()
    addFolder = Signal()
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self); v.setContentsMargins(0, 60, 0, 0); v.setSpacing(12); v.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cover = QLabel(); cover.setPixmap(make_cover(None, 120, 10)); cover.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        t = QLabel("Belum ada lagu"); t.setStyleSheet("color:#fff;font-size:26px;font-weight:800;"); t.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        d = QLabel("Tambahkan file musik dari komputermu untuk mulai mendengarkan.")
        d.setStyleSheet(f"color:{SUBTEXT};font-size:14px;"); d.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        row = QHBoxLayout(); row.setSpacing(12); row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        b1 = QPushButton("Tambah lagu"); b1.setStyleSheet(PILL_GREEN)
        b2 = QPushButton("Tambah folder"); b2.setStyleSheet(PILL_OUTLINE)
        for b in (b1, b2):
            b.setCursor(Qt.CursorShape.PointingHandCursor); b.setFocusPolicy(Qt.FocusPolicy.NoFocus); row.addWidget(b)
        b1.clicked.connect(self.addFiles); b2.clicked.connect(self.addFolder)
        v.addWidget(cover, 0, Qt.AlignmentFlag.AlignHCenter); v.addSpacing(8); v.addWidget(t); v.addWidget(d); v.addSpacing(8); v.addLayout(row)

class HomePage(GradientPage):
    playRequested = Signal(str)
    addFiles = Signal()
    addFolder = Signal()
    def __init__(self):
        super().__init__(ambient_accent())
        lay = QVBoxLayout(self.inner); lay.setContentsMargins(24, 28, 24, 24); lay.setSpacing(14)
        self.greet = QLabel(greeting()); self.greet.setStyleSheet("color:#fff;font-size:30px;font-weight:800;")
        lay.addWidget(self.greet)
        self.tagline = QLabel(tagline()); self.tagline.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        lay.addWidget(self.tagline)
        self.hero = NowPlayingHero()
        lay.addWidget(self.hero)

        self.quick_wrap = QWidget(); self.quick_grid = QGridLayout(self.quick_wrap)
        self.quick_grid.setContentsMargins(0, 6, 0, 10); self.quick_grid.setSpacing(12)
        for c in range(3): self.quick_grid.setColumnStretch(c, 1)
        lay.addWidget(self.quick_wrap)

        self.sec_title = QLabel("Semua lagu"); self.sec_title.setStyleSheet("color:#fff;font-size:22px;font-weight:800;")
        self.sec_sub = QLabel(""); self.sec_sub.setStyleSheet(f"color:{SUBTEXT};font-size:13px;")
        lay.addWidget(self.sec_title); lay.addWidget(self.sec_sub)
        self.table = TrackTable()
        lay.addWidget(self.table)

        self.empty = EmptyState()
        self.empty.addFiles.connect(self.addFiles); self.empty.addFolder.connect(self.addFolder)
        lay.addWidget(self.empty); lay.addStretch()

    def set_tracks(self, tracks: list):
        has = bool(tracks)
        self.empty.setVisible(not has)
        for w in (self.hero, self.quick_wrap, self.sec_title, self.sec_sub, self.table): w.setVisible(has)
        while self.quick_grid.count():
            w = self.quick_grid.takeAt(0).widget()
            if w: w.deleteLater()
        for i, t in enumerate(tracks[:6]):
            card = QuickCard(t); card.clicked.connect(self.playRequested)
            self.quick_grid.addWidget(card, i // 3, i % 3)
        self.table.set_tracks(tracks)
        self.sec_sub.setText(f"{len(tracks)} lagu")
        self.greet.setText(greeting()); self.tagline.setText(tagline())

class SearchPage(GradientPage):
    def __init__(self):
        super().__init__("#2b2b2b")
        self._tracks: list[Track] = []
        lay = QVBoxLayout(self.inner); lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(14)
        self.input = QLineEdit(); self.input.setPlaceholderText("Apa yang ingin kamu dengarkan?")
        self.input.setFixedHeight(46); self.input.setMaximumWidth(440)
        self.input.addAction(make_icon("search", SUBTEXT, 20), QLineEdit.ActionPosition.LeadingPosition)
        self.input.setClearButtonEnabled(True)
        self.input.setStyleSheet(
            "QLineEdit{background:#242424;border:2px solid transparent;border-radius:23px;"
            "color:#fff;padding:0 12px;font-size:14px;}"
            "QLineEdit:hover{background:#2a2a2a;}"
            "QLineEdit:focus{border-color:#ffffff;background:#2a2a2a;}"
        )
        lay.addWidget(self.input)
        self.heading = QLabel("Semua lagu"); self.heading.setStyleSheet("color:#fff;font-size:22px;font-weight:800;")
        lay.addWidget(self.heading)
        self.table = TrackTable()
        lay.addWidget(self.table)
        self.noresult = QLabel(""); self.noresult.setStyleSheet(f"color:{SUBTEXT};font-size:15px;")
        lay.addWidget(self.noresult); lay.addStretch()
        self.input.textChanged.connect(self._filter)

    def set_tracks(self, tracks: list):
        self._tracks = tracks; self._filter(self.input.text())

    def _filter(self, query: str):
        q = query.strip().lower()
        items = [t for t in self._tracks
                 if not q or q in t.title.lower() or q in t.artist.lower() or q in t.album.lower()]
        self.table.set_tracks(items)
        self.heading.setText("Hasil pencarian" if q else "Semua lagu")
        self.table.setVisible(bool(items))
        self.noresult.setText("" if items else f"Tidak ada hasil untuk “{query.strip()}”." if q else "Koleksi masih kosong.")

class SimpleListPage(GradientPage):
    def __init__(self, title: str, color: str = "#2b2b2b"):
        super().__init__(color)
        lay = QVBoxLayout(self.inner); lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(14)
        self.heading = QLabel(title); self.heading.setStyleSheet("color:#fff;font-size:32px;font-weight:800;")
        self.sub = QLabel(""); self.sub.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        lay.addWidget(self.heading); lay.addWidget(self.sub)
        self.action_btn = QPushButton(); self.action_btn.hide()
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor); self.action_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.action_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#ff7b7b;border:1px solid #7a3a3a;border-radius:16px;"
            "padding:7px 18px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:#3a1f1f;border-color:#ff7b7b;}")
        lay.addWidget(self.action_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.table = TrackTable()
        lay.addWidget(self.table); lay.addStretch()

    def enable_action(self, text: str):
        self.action_btn.setText(text); self.action_btn.show()

    def set_data(self, title: str, tracks: list):
        self.heading.setText(title)
        self.sub.setText(f"{len(tracks)} lagu")
        self.table.set_tracks(tracks)

class OnlinePage(GradientPage):
    searchRequested = Signal(str, str)
    settingsRequested = Signal()
    def __init__(self):
        super().__init__("#23485c")
        lay = QVBoxLayout(self.inner); lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(14)
        top = QHBoxLayout()
        title = QLabel("Musik Online"); title.setStyleSheet("color:#fff;font-size:32px;font-weight:800;")
        
        self.combo = QComboBox()
        self.combo.addItems(["Audius", "Jamendo", "YouTube Music"])
        self.combo.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_settings = QPushButton("Pengaturan"); self.btn_settings.setStyleSheet(PILL_WHITE)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_settings.clicked.connect(self.settingsRequested)
        
        top.addWidget(title); top.addSpacing(12); top.addWidget(self.combo)
        top.addStretch(); top.addWidget(self.btn_settings)
        lay.addLayout(top)

        self.input = QLineEdit(); self.input.setPlaceholderText("Cari lagu atau artis...")
        self.input.setFixedHeight(46); self.input.setMaximumWidth(520)
        self.input.addAction(make_icon("search", SUBTEXT, 20), QLineEdit.ActionPosition.LeadingPosition)
        self.input.setClearButtonEnabled(True)
        self.input.setStyleSheet(
            "QLineEdit{background:#242424;border:2px solid transparent;border-radius:23px;"
            "color:#fff;padding:0 12px;font-size:14px;}"
            "QLineEdit:hover{background:#2a2a2a;}"
            "QLineEdit:focus{border-color:#ffffff;background:#2a2a2a;}"
        )
        self.input.returnPressed.connect(lambda: self.searchRequested.emit(self.input.text(), self.combo.currentText()))
        lay.addWidget(self.input)

        self.status = QLabel(""); self.status.setWordWrap(True); self.status.setStyleSheet(f"color:{SUBTEXT};font-size:13px;")
        lay.addWidget(self.status)
        self.table = TrackTable(); self.table.allow_library = True; self.table.setVisible(False)
        lay.addWidget(self.table); lay.addStretch()

    def set_status(self, text: str):
        self.status.setText(text)

    def set_tracks(self, tracks: list):
        self.table.set_tracks(tracks); self.table.setVisible(bool(tracks))

class OnlineSettingsDialog(QDialog):
    def __init__(self, parent, jamendo_id: str = "", auto_cache: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Pengaturan Musik Online"); self.setMinimumWidth(480)
        v = QVBoxLayout(self); v.setSpacing(12)
        info = QLabel(
            "• Audius bekerja langsung dan tidak memerlukan kunci API.\n"
            "• Jamendo menggunakan Client ID default. Anda dapat menggantinya jika punya dari developers.jamendo.com.\n"
            "• YouTube Music memerlukan pustaka Python khusus. Ketikkan ini di Terminal/CMD agar YT Music bekerja:\n"
            "   pip install ytmusicapi yt-dlp")
        info.setWordWrap(True); info.setStyleSheet(f"color:{SUBTEXT};")
        form = QFormLayout()
        self.e_id = QLineEdit(jamendo_id)
        form.addRow("Jamendo Client ID", self.e_id)
        self.chk_cache = QCheckBox("Simpan otomatis lagu YouTube Music ke penyimpanan lokal (offline)")
        self.chk_cache.setChecked(auto_cache)
        
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        box.button(QDialogButtonBox.StandardButton.Save).setText("Simpan")
        box.button(QDialogButtonBox.StandardButton.Cancel).setText("Batal")
        box.accepted.connect(self.accept); box.rejected.connect(self.reject)
        v.addWidget(info); v.addLayout(form); v.addWidget(self.chk_cache); v.addWidget(box)

    def values(self) -> tuple:
        return self.e_id.text().strip(), self.chk_cache.isChecked()

class SettingsPage(GradientPage):
    def __init__(self, parent_win):
        super().__init__("#2a2a2a")
        self.parent_win = parent_win
        lay = QVBoxLayout(self.inner); lay.setContentsMargins(24, 24, 24, 24); lay.setSpacing(24)
        
        heading = QLabel("Pengaturan")
        heading.setStyleSheet("font-size:32px;font-weight:800;")
        lay.addWidget(heading)

        # Umum (General)
        grp_umum = QFrame(); grp_umum.setStyleSheet("background:rgba(255,255,255,0.05);border-radius:8px;")
        lay_umum = QFormLayout(grp_umum); lay_umum.setContentsMargins(16, 16, 16, 16); lay_umum.setSpacing(12)
        lbl_umum = QLabel("Umum (General)"); lbl_umum.setStyleSheet("font-size:18px;font-weight:bold;")
        lay_umum.addRow(lbl_umum)
        
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(["Bahasa Indonesia", "English"])
        
        self.cb_tz = QComboBox()
        self.cb_tz.addItems(["WIB (Asia/Jakarta)", "WITA (Asia/Makassar)", "WIT (Asia/Jayapura)", "Otomatis (Sistem)"])
        
        self.chk_startup = QCheckBox("Luncurkan otomatis saat komputer dinyalakan (Startup)")
        self.chk_startup.setCursor(Qt.CursorShape.PointingHandCursor)
        
        lbl_l = QLabel("Bahasa:"); lbl_l.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        lbl_tz = QLabel("Zona Waktu:"); lbl_tz.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        
        lay_umum.addRow(lbl_l, self.cb_lang)
        lay_umum.addRow(lbl_tz, self.cb_tz)
        lay_umum.addRow("", self.chk_startup)
        lay.addWidget(grp_umum)

        # Kontrol TWS & Tombol Media
        grp_media = QFrame(); grp_media.setObjectName("grpmedia")
        grp_media.setStyleSheet("QFrame#grpmedia{background:rgba(255,255,255,0.05);border-radius:8px;}")
        lay_media = QVBoxLayout(grp_media); lay_media.setContentsMargins(16, 16, 16, 16); lay_media.setSpacing(10)
        lbl_media = QLabel("Kontrol TWS & Tombol Media"); lbl_media.setStyleSheet("font-size:18px;font-weight:bold;")
        self.chk_media = QCheckBox("Aktifkan kontrol dari TWS / earbuds / keyboard (tetap bekerja di latar belakang)")
        self.chk_media.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_media_status = QLabel(""); self.lbl_media_status.setWordWrap(True)
        self.lbl_media_status.setStyleSheet(f"color:{SUBTEXT};font-size:12px;")
        lay_media.addWidget(lbl_media); lay_media.addWidget(self.chk_media); lay_media.addWidget(self.lbl_media_status)
        lay.addWidget(grp_media)

        # Tampilan (Appearance)
        grp_tampil = QFrame(); grp_tampil.setStyleSheet("background:rgba(255,255,255,0.05);border-radius:8px;")
        lay_tampil = QFormLayout(grp_tampil); lay_tampil.setContentsMargins(16, 16, 16, 16); lay_tampil.setSpacing(12)
        lbl_tampil = QLabel("Tampilan (Appearance)"); lbl_tampil.setStyleSheet("font-size:18px;font-weight:bold;")
        self.lbl_restart_info = QLabel("Beberapa perubahan tema mungkin memerlukan restart aplikasi.")
        self.lbl_restart_info.setStyleSheet(f"color:#d9534f;font-size:12px;font-weight:bold;"); self.lbl_restart_info.hide()
        lay_tampil.addRow(lbl_tampil)
        lay_tampil.addRow(self.lbl_restart_info)
        
        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["Gelap (Dark)", "Terang (Light)"])
        
        self.cb_text = QComboBox()
        self.cb_text.addItems(["Kecil", "Normal", "Besar", "Sangat Besar"])
        
        self.cb_layout = QComboBox()
        self.cb_layout.addItems(["Standar", "Kompak", "Luas"])
        
        self.cb_res = QComboBox()
        self.cb_res.addItems(["Otomatis (Responsive)", "1280x800", "1920x1080"])
        
        lbl_tm = QLabel("Tema:"); lbl_tm.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        lbl_tx = QLabel("Ukuran Teks:"); lbl_tx.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        lbl_ly = QLabel("Tata Letak:"); lbl_ly.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        lbl_rs = QLabel("Resolusi Jendela:"); lbl_rs.setStyleSheet(f"color:{SUBTEXT};font-size:14px;")
        
        lay_tampil.addRow(lbl_tm, self.cb_theme)
        lay_tampil.addRow(lbl_tx, self.cb_text)
        lay_tampil.addRow(lbl_ly, self.cb_layout)
        lay_tampil.addRow(lbl_rs, self.cb_res)
        lay.addWidget(grp_tampil)
        
        lay.addStretch()
        
        self._load_settings()
        
        # Sinyal perubahan disimpan otomatis
        self.cb_lang.currentIndexChanged.connect(self._save_settings)
        self.cb_tz.currentIndexChanged.connect(self._save_settings)
        self.chk_startup.toggled.connect(self._save_settings)
        self.chk_media.toggled.connect(self._save_settings)
        self.cb_theme.currentIndexChanged.connect(self._save_settings)
        self.cb_text.currentIndexChanged.connect(self._save_settings)
        self.cb_layout.currentIndexChanged.connect(self._save_settings)
        self.cb_res.currentIndexChanged.connect(self._save_settings)

    def set_media_status(self, text: str):
        self.lbl_media_status.setText(text)

    def _load_settings(self):
        s = self.parent_win.settings
        self.cb_lang.setCurrentText(s.value("opt_lang", "Bahasa Indonesia"))
        self.cb_tz.setCurrentText(s.value("opt_tz", "Otomatis (Sistem)"))
        self.chk_startup.setChecked(s.value("opt_startup", False, type=bool))
        self.chk_media.setChecked(s.value("opt_global_media", True, type=bool))
        self.cb_theme.setCurrentText(s.value("opt_theme", "Gelap (Dark)"))
        self.cb_text.setCurrentText(s.value("opt_text_size", "Normal"))
        self.cb_layout.setCurrentText(s.value("opt_layout", "Standar"))
        self.cb_res.setCurrentText(s.value("opt_res", "Otomatis (Responsive)"))

    def _save_settings(self):
        s = self.parent_win.settings
        s.setValue("opt_lang", self.cb_lang.currentText())
        s.setValue("opt_tz", self.cb_tz.currentText())
        s.setValue("opt_startup", self.chk_startup.isChecked())
        s.setValue("opt_global_media", self.chk_media.isChecked())
        
        prev_theme = s.value("opt_theme", "Gelap (Dark)")
        new_theme = self.cb_theme.currentText()
        if prev_theme != new_theme:
            self.lbl_restart_info.show()
        
        s.setValue("opt_theme", new_theme)
        s.setValue("opt_text_size", self.cb_text.currentText())
        s.setValue("opt_layout", self.cb_layout.currentText())
        s.setValue("opt_res", self.cb_res.currentText())
        
        self.parent_win.apply_app_settings()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Melodi")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 640)
        self.settings = QSettings("Melodi", "Melodi")

        # State Aplikasi
        self.tracks: list[Track] = []
        self.favorites: set[str] = set()
        self.playlists: dict[str, list[str]] = {}
        self.queue: list[str] = []
        self.play_context: list[str] = []
        self.current_path: str = ""

        self.shuffle = False
        self.repeat = 0
        self.history: list[str] = []

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.media_devices = QMediaDevices(self)
        self.output_id: Optional[str] = None
        self._active_id: Optional[str] = None

        self.probe = QMediaPlayer(self)
        self._probe_queue: list[Track] = []
        self._probing = False
        self._probe_track: Optional[Track] = None
        self._probe_token = 0
        
        self._is_quitting = False

        self._last_media_t: dict = {}
        self._media_keys = GlobalMediaKeys(self._media_action)

        self.api = OnlineClient()
        self.api.configure(str(self.settings.value("jamendo_client_id", DEFAULT_JAMENDO_ID) or ""))
        
        self._loading = False            
        self.lib_file = data_dir() / "library.json"
        self.auto_cache = bool(self.settings.value("yt_auto_cache", True, type=bool))
        self.dl_pool = QThreadPool(self); self.dl_pool.setMaxThreadCount(2)   
        self._want_play = False          
        self._end_handled = -1           
        self._err_streak = 0
        self._recoveries = 0
        self._last_recover = 0.0
        self._last_pos = -1
        self._last_pos_t = time.monotonic()
        self._ctx_anchor = ""            
        self._shuffle_next: Optional[str] = None
        self._prefetching: set = set()
        self._prefetch_token = -1
        self._pending_seek = 0
        self.net_pool = QThreadPool(self); self.net_pool.setMaxThreadCount(4)
        self.cover_pool = QThreadPool(self); self.cover_pool.setMaxThreadCount(3)
        self._remote: dict[str, Track] = {}
        self.online_results: list[Track] = []
        self._search_token = 0
        self._stream_token = 0
        self._cover_pending: set[str] = set()
        self._cover_lib_dirty = False
        self._cover_timer = QTimer(self); self._cover_timer.setSingleShot(True); self._cover_timer.setInterval(500)
        self._cover_timer.timeout.connect(self._refresh_after_covers)

        self._watch = QTimer(self); self._watch.setInterval(2000)
        self._watch.timeout.connect(self._watchdog); self._watch.start()

        self._build_ui()
        self._build_tray()
        self._connect_signals()

        vol = int(self.settings.value("volume", 60))
        self.vol_slider.setValue(vol)
        self.audio.setVolume(vol / 100)
        self._update_vol_icon()
        self._load_output()
        self._update_now_playing()
        self._load_saved()
        self._load_last_state()
        
        # Terapkan pengaturan (Ukuran teks, Tema, dll)
        self.apply_app_settings()
        
        QTimer.singleShot(5000, self._prune_cache)

    def _build_ui(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(8, 8, 8, 8); outer.setSpacing(8)

        body = QHBoxLayout(); body.setSpacing(8); body.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.home = HomePage()
        self.search = SearchPage()
        self.fav_page = SimpleListPage("Lagu Kesukaan", "#4a1c23")
        self.pl_page = SimpleListPage("Playlist", "#1c334a")
        self.queue_page = SimpleListPage("Antrean", "#333333")
        self.online_page = OnlinePage()
        self.settings_page = SettingsPage(self)
        
        for p in (self.home, self.search, self.fav_page, self.pl_page, self.queue_page, self.online_page, self.settings_page):
            self.stack.addWidget(p)
            
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)
        outer.addWidget(self._build_player_bar())

    def _build_sidebar(self) -> QWidget:
        side = QWidget(); side.setFixedWidth(330)
        v = QVBoxLayout(side); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(8)

        nav = QFrame(); nav.setObjectName("panel")
        nv = QVBoxLayout(nav); nv.setContentsMargins(12, 10, 12, 10); nv.setSpacing(2)
        brand = QHBoxLayout(); brand.setContentsMargins(12, 4, 0, 10); brand.setSpacing(10)
        logo = QLabel(); logo.setFixedSize(32, 32); logo.setPixmap(app_icon().pixmap(32, 32))
        bcol = QVBoxLayout(); bcol.setSpacing(0)
        brand_name = QLabel("Melodi"); brand_name.setStyleSheet("color:#fff;font-size:18px;font-weight:800;")
        brand_sub = QLabel("musik latar • santai & fokus"); brand_sub.setStyleSheet(f"color:{SUBTEXT};font-size:11px;")
        bcol.addWidget(brand_name); bcol.addWidget(brand_sub)
        brand.addWidget(logo); brand.addLayout(bcol, 1)
        nv.addLayout(brand)
        self.btn_home = NavButton("home", "Beranda")
        self.btn_search = NavButton("search", "Cari")
        self.btn_fav = NavButton("heart_fill", "Lagu Kesukaan")
        self.btn_online = NavButton("cloud", "Musik Online")
        self.btn_settings = NavButton("settings", "Pengaturan")
        
        group = QButtonGroup(self); group.setExclusive(True)
        for b in (self.btn_home, self.btn_search, self.btn_fav, self.btn_online, self.btn_settings):
            group.addButton(b); nv.addWidget(b)
        
        self.btn_home.setChecked(True)
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentWidget(self.home))
        self.btn_search.clicked.connect(self._open_search)
        self.btn_fav.clicked.connect(self._open_fav)
        self.btn_online.clicked.connect(self._open_online)
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings_page))
        v.addWidget(nav)

        lib = QFrame(); lib.setObjectName("panel")
        lv = QVBoxLayout(lib); lv.setContentsMargins(8, 12, 8, 8); lv.setSpacing(8)
        head = QHBoxLayout(); head.setContentsMargins(8, 0, 0, 0)
        icon = QLabel(); icon.setPixmap(make_icon("library", SUBTEXT, 24).pixmap(24, 24))
        title = QLabel("Koleksi Kamu"); title.setStyleSheet(f"color:{SUBTEXT};font-weight:700;font-size:15px;")
        add_btn = IconButton("plus", 20); add_btn.setToolTip("Tambah lagu")
        add_btn.clicked.connect(lambda: self._add_menu(add_btn))
        head.addWidget(icon); head.addSpacing(6); head.addWidget(title); head.addStretch(); head.addWidget(add_btn)
        lv.addLayout(head)
        
        pl_head = QHBoxLayout(); pl_head.setContentsMargins(8, 8, 0, 0)
        pl_title = QLabel("Playlist"); pl_title.setStyleSheet(f"color:{SUBTEXT};font-weight:700;font-size:13px;")
        pl_add = IconButton("plus", 16); pl_add.setToolTip("Buat Playlist Baru")
        pl_add.clicked.connect(self._create_playlist)
        pl_head.addWidget(pl_title); pl_head.addStretch(); pl_head.addWidget(pl_add)
        lv.addLayout(pl_head)
        
        self.pl_list = QListWidget(); self.pl_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pl_list.setStyleSheet(
            "QListWidget{background:transparent;border:none;outline:0; color:#b3b3b3; font-weight:600;}"
            "QListWidget::item{border-radius:4px; padding:6px;}"
            f"QListWidget::item:hover{{background:{ELEVATED}; color:#fff;}}"
            "QListWidget::item:selected{background:#2a2a2a; color:#fff;}"
        )
        self.pl_list.setFixedHeight(120)
        self.pl_list.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.pl_list.itemClicked.connect(self._open_playlist)
        self.pl_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pl_list.customContextMenuRequested.connect(self._playlist_menu)
        pl_delete = QShortcut(QKeySequence("Delete"), self.pl_list)
        pl_delete.setContext(Qt.ShortcutContext.WidgetShortcut)
        pl_delete.activated.connect(lambda: self._delete_playlist(self.pl_list.currentItem().text()
                                                                   if self.pl_list.currentItem() else ""))
        lv.addWidget(self.pl_list)

        self.empty_card = QFrame(); self.empty_card.setStyleSheet(f"QFrame#card{{background:{ELEVATED};border-radius:8px;}}")
        self.empty_card.setObjectName("card")
        ev = QVBoxLayout(self.empty_card); ev.setContentsMargins(20, 18, 20, 18); ev.setSpacing(6)
        t = QLabel("Mulai dengan musikmu"); t.setStyleSheet("color:#fff;font-weight:700;font-size:15px;")
        d = QLabel("Tambahkan lagu dari komputermu, mudah kok."); d.setWordWrap(True); d.setStyleSheet(f"color:{SUBTEXT};font-size:13px;")
        b = QPushButton("Tambah lagu"); b.setStyleSheet(PILL_WHITE)
        b.setCursor(Qt.CursorShape.PointingHandCursor); b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.clicked.connect(self.add_files_dialog)
        ev.addWidget(t); ev.addWidget(d); ev.addSpacing(8); ev.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
        lv.addWidget(self.empty_card)

        self.lib_list = QListWidget(); self.lib_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lib_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lib_list.setStyleSheet(
            "QListWidget{background:transparent;border:none;outline:0;}"
            "QListWidget::item{border-radius:6px;}"
            f"QListWidget::item:hover{{background:{ELEVATED};}}"
            "QListWidget::item:selected{background:#2a2a2a;}"
        )
        self.lib_list.itemDoubleClicked.connect(lambda it: self.play_path(it.data(Qt.ItemDataRole.UserRole), [t.path for t in self.tracks]))
        self.lib_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lib_list.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.lib_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lib_list.customContextMenuRequested.connect(self._lib_menu)
        lib_delete = QShortcut(QKeySequence("Delete"), self.lib_list)
        lib_delete.setContext(Qt.ShortcutContext.WidgetShortcut)
        lib_delete.activated.connect(lambda: self.confirm_remove(self._lib_selected()))
        lv.addWidget(self.lib_list, 1); v.addWidget(lib, 1)
        return side

    def _build_player_bar(self) -> QWidget:
        bar = PlayerBar(); bar.setFixedHeight(84); self.player_bar = bar
        h = QHBoxLayout(bar); h.setContentsMargins(16, 0, 12, 0)

        left = QWidget(); lh = QHBoxLayout(left); lh.setContentsMargins(0, 0, 0, 0); lh.setSpacing(12)
        self.np_cover = ClickableCover(); self.np_cover.setFixedSize(56, 56)
        self.np_cover.setToolTip("Lihat daftar lagu selanjutnya")
        tv = QVBoxLayout(); tv.setSpacing(2)
        self.np_title = ClickableElidedLabel("")
        self.np_title.setStyleSheet("QLabel{color:#fff;font-weight:600;font-size:14px;}"
                                    "QLabel:hover{text-decoration:underline;}")
        self.np_artist = ClickableElidedLabel(""); self.np_artist.setStyleSheet(f"color:{SUBTEXT};font-size:12px;")
        for w in (self.np_cover, self.np_title, self.np_artist):
            w.clicked.connect(self._open_queue)
        tv.addStretch(); tv.addWidget(self.np_title); tv.addWidget(self.np_artist); tv.addStretch()
        
        self.btn_like = IconButton("heart", 20); self.btn_like.setToolTip("Tambahkan ke Favorit")
        self.btn_like.clicked.connect(self._toggle_like_current)
        
        self.mini_eq = EqualizerBars(4, 3, 2, 16, GREEN)
        lh.addWidget(self.np_cover); lh.addLayout(tv, 1); lh.addWidget(self.mini_eq); lh.addWidget(self.btn_like)

        center = QWidget(); center.setMaximumWidth(720)
        cv = QVBoxLayout(center); cv.setContentsMargins(0, 8, 0, 8); cv.setSpacing(4)
        controls = QHBoxLayout(); controls.setSpacing(14)
        self.btn_shuffle = IconButton("shuffle", 20); self.btn_shuffle.setToolTip("Acak")
        self.btn_prev = IconButton("prev", 22); self.btn_prev.setToolTip("Sebelumnya")
        self.btn_play = IconButton("play", 20, "#000000", "#000000"); self.btn_play.setFixedSize(38, 38)
        self.btn_play.setStyleSheet(
            "QPushButton{background:#fff;border:none;border-radius:19px;}"
            "QPushButton:hover{background:#f0f0f0;}"
        )
        self.btn_next = IconButton("next", 22); self.btn_next.setToolTip("Berikutnya")
        self.btn_repeat = IconButton("repeat", 20); self.btn_repeat.setToolTip("Ulangi")
        controls.addStretch()
        for b in (self.btn_shuffle, self.btn_prev, self.btn_play, self.btn_next, self.btn_repeat): controls.addWidget(b)
        controls.addStretch()
        prog = QHBoxLayout(); prog.setSpacing(8)
        self.cur_label = QLabel("0:00"); self.cur_label.setFixedWidth(40)
        self.cur_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.total_label = QLabel("0:00"); self.total_label.setFixedWidth(40)
        for lb in (self.cur_label, self.total_label): lb.setStyleSheet(f"color:{SUBTEXT};font-size:11px;")
        self.progress = ClickSlider(); self.progress.setRange(0, 0)
        prog.addWidget(self.cur_label); prog.addWidget(self.progress, 1); prog.addWidget(self.total_label)
        cv.addLayout(controls); cv.addLayout(prog)

        right = QWidget(); rh = QHBoxLayout(right); rh.setContentsMargins(0, 0, 8, 0); rh.setSpacing(4)
        self.queue_btn = IconButton("queue", 20); self.queue_btn.setToolTip("Antrean")
        self.queue_btn.clicked.connect(self._open_queue)
        self.device_btn = IconButton("headphones", 20); self.device_btn.setToolTip("Pilih perangkat audio")
        self.vol_btn = IconButton("volume", 20)
        self.vol_slider = ClickSlider(); self.vol_slider.setRange(0, 100); self.vol_slider.setFixedWidth(110)
        rh.addStretch(); rh.addWidget(self.queue_btn); rh.addWidget(self.device_btn); rh.addWidget(self.vol_btn); rh.addWidget(self.vol_slider)

        h.addWidget(left, 3); h.addWidget(center, 4); h.addWidget(right, 3)
        return bar
        
    def _build_tray(self):
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("Melodi")
        menu = QMenu(self)
        menu.addAction("Putar / Jeda").triggered.connect(self.toggle_play)
        menu.addAction("Berikutnya").triggered.connect(lambda: self.next_track(auto=False))
        menu.addAction("Sebelumnya").triggered.connect(self.prev_track)
        menu.addSeparator()
        menu.addAction("Tampilkan Melodi").triggered.connect(self._restore_window)
        menu.addAction("Keluar").triggered.connect(self._quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _connect_signals(self):
        self.home.playRequested.connect(lambda p: self.play_path(p, [t.path for t in self.tracks]))
        self.home.table.playRequested.connect(lambda p: self.play_path(p, [t.path for t in self.tracks]))
        self.search.table.playRequested.connect(lambda p: self.play_path(p, [t.path for t in self.search._tracks]))
        self.fav_page.table.playRequested.connect(lambda p: self.play_path(p, self._get_fav_paths()))
        self.pl_page.table.playRequested.connect(lambda p: self.play_path(p, self.playlists.get(self.pl_page.heading.text(), [])))
        self.queue_page.table.playRequested.connect(self._play_from_queue_page)

        for p in (self.home, self.search, self.fav_page, self.pl_page, self.queue_page, self.online_page):
            p.table.actionRequested.connect(self._handle_table_action)

        self.online_page.searchRequested.connect(self._online_search)
        self.online_page.settingsRequested.connect(self._online_settings)
        self.online_page.table.playRequested.connect(lambda p: self.play_path(p, [t.path for t in self.online_results]))
        self.online_page.table.removeRequested.connect(self._online_remove_results)
            
        self.home.table.removeRequested.connect(self.confirm_remove)
        self.search.table.removeRequested.connect(self.confirm_remove)
        self.fav_page.table.removeRequested.connect(self._remove_from_fav)
        self.pl_page.table.removeRequested.connect(self._remove_from_playlist)
        self.pl_page.enable_action("Hapus playlist")
        self.pl_page.action_btn.clicked.connect(lambda: self._delete_playlist(self.pl_page.heading.text()))
        self.queue_page.table.removeRequested.connect(self._remove_from_queue)

        self.home.addFiles.connect(self.add_files_dialog)
        self.home.addFolder.connect(self.add_folder_dialog)

        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next.clicked.connect(lambda: self.next_track(auto=False))
        self.btn_prev.clicked.connect(self.prev_track)
        self.btn_shuffle.clicked.connect(self._toggle_shuffle)
        self.btn_repeat.clicked.connect(self._cycle_repeat)
        self.vol_btn.clicked.connect(self._toggle_mute)
        self.device_btn.clicked.connect(self._device_menu)
        self.media_devices.audioOutputsChanged.connect(self._on_devices_changed)

        self.progress.seek.connect(self.player.setPosition)
        self.progress.valueChanged.connect(
            lambda v: self.cur_label.setText(fmt(v)) if self.progress.isSliderDown() else None)
        self.vol_slider.valueChanged.connect(self._on_volume)

        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.errorOccurred.connect(self._on_error)
        self.probe.mediaStatusChanged.connect(self._on_probe_status)

        self._shortcuts = []
        for seq, fn in (("Space", self.toggle_play), ("Ctrl+Right", lambda: self.next_track(auto=False)), ("Ctrl+Left", self.prev_track)):
            sc = QShortcut(QKeySequence(seq), self); sc.activated.connect(fn); self._shortcuts.append(sc)

        # Cadangan saat jendela aktif / non-Windows. Di Windows, GlobalMediaKeys menangani tombol saat di latar belakang.
        for key, name in ((Qt.Key.Key_MediaTogglePlayPause, "toggle"), (Qt.Key.Key_MediaPlay, "play"),
                          (Qt.Key.Key_MediaPause, "pause"), (Qt.Key.Key_MediaStop, "stop"),
                          (Qt.Key.Key_MediaNext, "next"), (Qt.Key.Key_MediaPrevious, "prev")):
            sc = QShortcut(QKeySequence(key), self); sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
            sc.activated.connect(lambda n=name: self._media_action(n)); self._shortcuts.append(sc)

        self.home.hero.toggleRequested.connect(self.toggle_play)
        self.home.hero.queueRequested.connect(self._open_queue)

    def apply_app_settings(self):
        s = self.settings
        
        # Pengaturan Startup (Hanya Windows - registry)
        startup = s.value("opt_startup", False, type=bool)
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                if startup:
                    winreg.SetValueEx(key, "Melodi", 0, winreg.REG_SZ, f'"{sys.executable}"')
                else:
                    try: winreg.DeleteValue(key, "Melodi")
                    except Exception: pass
                winreg.CloseKey(key)
            except Exception: pass
            
        # Ukuran Teks Font Dasar
        size_map = {"Kecil": 9, "Normal": 10, "Besar": 12, "Sangat Besar": 14}
        ts = size_map.get(s.value("opt_text_size", "Normal"), 10)
        font = QApplication.instance().font()
        font.setPointSize(ts)
        QApplication.instance().setFont(font)
        
        # Resolusi Aplikasi
        res = s.value("opt_res", "Otomatis (Responsive)")
        if res == "1280x800":
            self.resize(1280, 800)
        elif res == "1920x1080":
            self.resize(1920, 1080)
            
        # Tema (Dasar implementasi Light Theme)
        theme = s.value("opt_theme", "Gelap (Dark)")
        is_light = "Terang" in theme
        
        app = QApplication.instance()
        pal = QPalette()
        
        if is_light:
            # Overriding warna sistem (Tema terang sederhana)
            pal.setColor(QPalette.ColorRole.Window, QColor("#e8e8e8"))
            pal.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
            pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#d0d0d0"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#000000"))
            pal.setColor(QPalette.ColorRole.Button, QColor("#cccccc"))
            pal.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor(GREEN))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            app.setPalette(pal)
            
            # Penggantian ringan string style untuk elemen dominan
            light_qss = APP_QSS.replace(BG, "#e8e8e8").replace(PANEL, "#ffffff").replace(TEXT, "#000000")
            light_qss += """
                QMenu { background: #ffffff; color: #000; border: 1px solid #ccc; }
                QMenu::item:selected { background: #d0d0d0; }
                QComboBox { background: #e0e0e0; color: #000; border: 1px solid #aaa; }
                QComboBox:hover { background: #d0d0d0; border-color: #888; }
                QComboBox QAbstractItemView { background: #ffffff; color: #000; }
                QTableWidget::item:selected { background: #e0e0e0; color: #000; }
                QListWidget::item:hover { background: #f0f0f0; }
                QListWidget::item:selected { background: #e0e0e0; }
                QCheckBox { color: #000; }
            """
            app.setStyleSheet(light_qss)
        else:
            pal.setColor(QPalette.ColorRole.Window, QColor(PANEL)); pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
            pal.setColor(QPalette.ColorRole.Base, QColor("#181818")); pal.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL))
            pal.setColor(QPalette.ColorRole.Text, QColor(TEXT)); pal.setColor(QPalette.ColorRole.Button, QColor("#282828"))
            pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT)); pal.setColor(QPalette.ColorRole.Highlight, QColor(GREEN))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000")); pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#282828"))
            pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
            app.setPalette(pal)
            app.setStyleSheet(APP_QSS)

        self._apply_media_keys()

    # ── Kontrol TWS / tombol media ──────────────────────────────────────────
    def _apply_media_keys(self):
        want = self.settings.value("opt_global_media", True, type=bool)
        if want and not self._media_keys.active: self._media_keys.start()
        elif not want and self._media_keys.active: self._media_keys.stop()
        self.settings_page.set_media_status(self._media_keys.status_text(want))
        self._refresh_device_chip()

    def _media_action(self, name: str):
        now = time.monotonic()                                   # cegah pemicu ganda (shortcut + hotkey / TWS dobel)
        if now - self._last_media_t.get(name, 0.0) < 0.4: return
        self._last_media_t[name] = now
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        if name == "toggle": self.toggle_play()
        elif name == "play":
            if not playing: self.toggle_play()
        elif name in ("pause", "stop"):
            if playing: self.player.pause()
        elif name == "next": self.next_track(auto=False)
        elif name == "prev": self.prev_track()

    def _refresh_device_chip(self):
        dev = self.audio.device()
        name = dev.description() if not dev.isNull() else "Tidak ada perangkat audio"
        self.home.hero.set_device(name, self._media_keys.active)

    # ── Animasi tema musik latar ────────────────────────────────────────────
    def _sync_clock(self):
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        get_clock().configure(playing, self.isVisible() and not self.isMinimized())

    def _sync_visuals(self, playing: bool):
        self.home.hero.set_playing(playing)
        self.mini_eq.set_playing(playing)
        self._sync_clock()
        self._update_tray_tip()

    def _update_tray_tip(self):
        if not hasattr(self, "tray"): return
        t = self._get_track(self.current_path) if self.current_path else None
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        tip = f"{'▶' if playing else '⏸'}  {t.title} • {t.artist}" if t else "Melodi"
        self.tray.setToolTip(tip[:120])

    def showEvent(self, e):
        super().showEvent(e); QTimer.singleShot(0, self._sync_clock)

    def hideEvent(self, e):
        super().hideEvent(e); QTimer.singleShot(0, self._sync_clock)

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.WindowStateChange: QTimer.singleShot(0, self._sync_clock)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick: self._restore_window()
            
    def _restore_window(self):
        self.show(); self.activateWindow()

    def _quit_app(self):
        self._is_quitting = True; QApplication.quit()
        
    def _save_final_state(self):
        if getattr(self, '_is_quitting_handled', False): return
        self._is_quitting_handled = True
        self._media_keys.stop()
        self._save_library()
        
        if self.current_path:
            self.settings.setValue("last_track", self.current_path)
            self.settings.setValue("last_pos", self.player.position())
            self.settings.setValue("last_context", self.play_context)
            self.settings.setValue("last_queue", self.queue)
        else:
            for k in ("last_track", "last_pos", "last_context", "last_queue"): self.settings.remove(k)
        self.settings.setValue("volume", self.vol_slider.value())

    def closeEvent(self, e):
        if getattr(self, '_is_quitting', False): e.accept()
        else:
            e.ignore(); self.hide()
            if not getattr(self, '_tray_notified', False):
                self.tray.showMessage("Melodi", "Aplikasi berjalan di latar belakang. Lagu tetap diputar.",
                                      QSystemTrayIcon.MessageIcon.Information, 4000)
                self._tray_notified = True

    def _get_track(self, path: str) -> Optional[Track]:
        for t in self.tracks:
            if t.path == path: return t
        return self._remote.get(path)

    def _get_fav_paths(self) -> list[str]:
        return [t.path for t in self.tracks if t.path in self.favorites]

    def _open_search(self):
        self.stack.setCurrentWidget(self.search)
        self.search.input.setFocus()

    def _open_fav(self):
        self.stack.setCurrentWidget(self.fav_page)
        tracks = [t for t in self.tracks if t.path in self.favorites]
        self.fav_page.set_data("Lagu Kesukaan", tracks)
        
    def _upcoming_paths(self, limit: int = 150) -> list:
        """Urutan lagu yang akan diputar: antrean manual dulu, lalu lanjutan dari daftar yang sedang diputar."""
        out = [p for p in self.queue if self._get_track(p)]
        ctx = [p for p in self.play_context if self._get_track(p)]
        if not ctx: return out[:limit]
        if self.shuffle:                                           # mode acak: hanya lagu berikutnya yang sudah pasti
            choices = [p for p in ctx if p != self.current_path] or ctx
            if self._shuffle_next not in choices: self._shuffle_next = random.choice(choices)
            out.append(self._shuffle_next)
        else:
            anchor = self._ctx_anchor if self._ctx_anchor in ctx else self.current_path
            idx = ctx.index(anchor) if anchor in ctx else -1
            rest = ctx[idx + 1:]
            if self.repeat == 1 and idx >= 0: rest += ctx[:idx]    # ulangi semua: kembali ke awal daftar
            out += rest
        return out[:limit]

    def _open_queue(self):
        self.stack.setCurrentWidget(self.queue_page)
        cur = self._get_track(self.current_path) if self.current_path else None
        up = [t for t in (self._get_track(p) for p in self._upcoming_paths()) if t]
        self.queue_page.set_data("Antrean", ([cur] if cur else []) + up)
        nq = len([p for p in self.queue if self._get_track(p)])
        parts = []
        if cur: parts.append(f"Sedang diputar: {cur.title}")
        parts.append(f"{nq} di antrean" if nq else "antrean kosong")
        if self.shuffle: parts.append("mode acak aktif")
        else: parts.append(f"{max(0, len(up) - nq)} lagu selanjutnya")
        self.queue_page.sub.setText("  •  ".join(parts))
        self.queue_page.table.set_playing(self.current_path)
        self.queue_page.scroller.verticalScrollBar().setValue(0)

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "Playlist Baru", "Nama Playlist:")
        if ok and name.strip() and name.strip() not in self.playlists:
            self.playlists[name.strip()] = []
            self._save_library(); self.refresh_views()

    def _playlist_menu(self, pos):
        item = self.pl_list.itemAt(pos)
        if not item: return
        self.pl_list.setCurrentItem(item)
        name = item.text()
        paths = [p for p in self.playlists.get(name, []) if self._get_track(p)]
        menu = QMenu(self)
        menu.addAction("Buka").triggered.connect(lambda _=False: self._open_playlist(item))
        play = menu.addAction("Putar playlist"); play.setEnabled(bool(paths))
        play.triggered.connect(lambda _=False: self.play_path(paths[0], list(paths)))
        menu.addSeparator()
        menu.addAction("Hapus playlist").triggered.connect(lambda _=False: self._delete_playlist(name))
        menu.exec(self.pl_list.viewport().mapToGlobal(pos))

    def _delete_playlist(self, name: str):
        if name not in self.playlists: return
        count = len(self.playlists[name])
        box = QMessageBox(self); box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Hapus playlist")
        box.setText(f"Hapus playlist “{name}”?\n\n"
                    f"Berisi {count} lagu. Lagunya tidak ikut terhapus dari koleksi.")
        ok = box.addButton("Hapus", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is not ok: return
        del self.playlists[name]
        self._save_library()
        if self.stack.currentWidget() is self.pl_page and self.pl_page.heading.text() == name:
            self.stack.setCurrentWidget(self.home); self.btn_home.setChecked(True)
        self.refresh_views()

    def _open_playlist(self, item):
        name = item.text()
        self.stack.setCurrentWidget(self.pl_page)
        paths = self.playlists.get(name, [])
        tracks = [self._get_track(p) for p in paths if self._get_track(p)]
        self.pl_page.set_data(name, tracks)

    def _handle_table_action(self, action: str, paths: list):
        if action == "library":
            added = self._ensure_in_library(paths)
            self.online_page.set_status(
                f"{added} lagu ditambahkan ke koleksi" + (" dan sedang disimpan untuk pemutaran lokal." if self.auto_cache else ".")
                if added else "Lagu sudah ada di koleksi.")
            return
        if action == "queue":
            self.queue.extend(paths)
            if self.stack.currentWidget() == self.queue_page: self._open_queue()
        elif action == "fav":
            self._ensure_in_library(paths)
            self.favorites.update(paths)
            self._save_library()
            if self.stack.currentWidget() == self.fav_page: self._open_fav()
            self._update_now_playing()
        elif action == "playlist":
            if not self.playlists:
                QMessageBox.information(self, "Info", "Belum ada playlist. Buat di menu kiri dulu (tekan tanda +).")
                return
            menu = QMenu(self)
            for name in self.playlists:
                menu.addAction(name).triggered.connect(lambda _=False, n=name: self._add_to_playlist(n, paths))
            menu.exec(QCursor.pos())

    def _add_to_playlist(self, name: str, paths: list):
        self._ensure_in_library(paths)          
        for p in paths:
            if p not in self.playlists[name]: self.playlists[name].append(p)
        self._save_library()
        if self.stack.currentWidget() == self.pl_page and self.pl_page.heading.text() == name:
            items = self.pl_list.findItems(name, Qt.MatchFlag.MatchExactly)
            if items: self._open_playlist(items[0])
            
    def _remove_from_fav(self, paths: list):
        self.favorites.difference_update(paths); self._save_library()
        self._open_fav(); self._update_now_playing()

    def _remove_from_playlist(self, paths: list):
        name = self.pl_page.heading.text()
        if name in self.playlists:
            self.playlists[name] = [p for p in self.playlists[name] if p not in paths]
            self._save_library()
            items = self.pl_list.findItems(name, Qt.MatchFlag.MatchExactly)
            if items: self._open_playlist(items[0])

    def _remove_from_queue(self, paths: list):
        self.queue = [p for p in self.queue if p not in paths]
        self.play_context = [p for p in self.play_context if p not in paths or p == self.current_path]
        if self._shuffle_next in paths: self._shuffle_next = None
        self._open_queue()

    def _toggle_like_current(self):
        if not self.current_path: return
        if self.current_path in self.favorites: self.favorites.remove(self.current_path)
        else:
            self._ensure_in_library([self.current_path])
            self.favorites.add(self.current_path)
        self._save_library(); self._update_now_playing()
        if self.stack.currentWidget() == self.fav_page: self._open_fav()

    def _add_menu(self, anchor: QWidget):
        menu = QMenu(self)
        menu.addAction("Tambah file lagu…", self.add_files_dialog)
        menu.addAction("Tambah folder…", self.add_folder_dialog)
        menu.addAction("Cari di Musik Online…", self._open_online)
        if self.tracks:
            menu.addSeparator(); menu.addAction("Kosongkan koleksi…", self.clear_library)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def add_files_dialog(self):
        start = str(Path.home() / "Music")
        files, _ = QFileDialog.getOpenFileNames(self, "Pilih lagu", start, AUDIO_FILTER)
        if files: self.add_files(files)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih folder musik", str(Path.home() / "Music"))
        if folder:
            files = sorted(str(f) for f in Path(folder).rglob("*") if f.suffix.lower() in AUDIO_EXTS)
            self.add_files(files)

    def add_files(self, paths: list):
        known = {t.path for t in self.tracks}
        new = [Track.from_path(p) for p in paths if p not in known and Path(p).is_file()]
        if not new: return
        self.tracks.extend(new)
        self._probe_queue.extend(new)
        self.refresh_views()
        self._save_library()
        if not self._probing: self._probe_next()

    def _load_saved(self):
        self._loading = True
        try:
            data = self._read_library_file() or self._legacy_from_qsettings()
            self.favorites = {str(x) for x in data["favorites"]}
            self.playlists = data["playlists"]

            self.add_files([p for p in data["local"] if p and not is_remote_path(p)])

            for d in data["online"]:
                if not isinstance(d, dict) or not is_remote_path(d.get("path", "")): continue
                t = Track.from_dict(d)
                if self._get_track(t.path): continue
                self._remote[t.path] = t; self.tracks.append(t); self._fetch_cover(t)

            self._recover_orphans()
        finally:
            self._loading = False
        self.refresh_views()
        self._save_library()

    def _recover_orphans(self):
        ids = set(self.favorites)
        for pl in self.playlists.values(): ids.update(pl)
        for path in sorted(i for i in ids if str(i).startswith(PREFIX_YT)):
            if self._get_track(path): continue
            vid = path[len(PREFIX_YT):]
            t = Track(path=path, title=f"Lagu YouTube Music ({vid})", artist="YouTube Music", album="YouTube Music")
            self._remote[path] = t; self.tracks.append(t)
            w = Worker(self.api.fetch_yt_meta, path, vid)
            w.signals.done.connect(self._on_orphan_meta)
            self.net_pool.start(w)

    def _on_orphan_meta(self, path, meta: dict):
        t = self._remote.get(path)
        if t is None: return
        if meta.get("title"): t.title = meta["title"]
        if meta.get("artist"): t.artist = meta["artist"]
        if meta.get("duration"): t.duration = meta["duration"]
        if meta.get("cover_url"): t.cover_url = meta["cover_url"]
        self._save_library(); self.refresh_views(); self._fetch_cover(t)

    def _read_library_file(self) -> Optional[dict]:
        for f in (self.lib_file, self.lib_file.with_suffix(".bak")):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(raw, dict):
                pl = raw.get("playlists") if isinstance(raw.get("playlists"), dict) else {}
                return {"local": as_list(raw.get("local")),
                        "online": [d for d in as_list(raw.get("online")) if isinstance(d, dict)],
                        "favorites": as_list(raw.get("favorites")),
                        "playlists": {str(k): [str(x) for x in v] for k, v in pl.items() if isinstance(v, list)}}
        return None

    def _legacy_from_qsettings(self) -> dict:
        try: remote = json.loads(self.settings.value("online_library", "[]") or "[]")
        except (ValueError, TypeError): remote = []
        return {"local": as_list(self.settings.value("library", [], type=list)),
                "online": [d for d in remote if isinstance(d, dict)] if isinstance(remote, list) else [],
                "favorites": as_list(self.settings.value("favorites", [], type=list)),
                "playlists": self._load_playlists()}

    def _load_playlists(self) -> dict:
        pl = {}
        raw = self.settings.value("playlists_json", "")
        if raw:
            try: pl = json.loads(raw)
            except (ValueError, TypeError): pl = {}
        if not isinstance(pl, dict) or not pl:
            legacy = self.settings.value("playlists", {})
            pl = {str(k): as_list(v) for k, v in legacy.items()} if isinstance(legacy, dict) else {}
        return {str(k): [str(x) for x in v] for k, v in pl.items() if isinstance(v, list)}

    def _load_last_state(self):
        last_path = self.settings.value("last_track", "")
        last_pos = int(self.settings.value("last_pos", 0) or 0)
        self.play_context = as_list(self.settings.value("last_context", [], type=list))
        self.queue = [p for p in as_list(self.settings.value("last_queue", [], type=list)) if self._get_track(p)]
        if not self.play_context: self.play_context = [t.path for t in self.tracks]
        
        if last_path and self._get_track(last_path):
            self.play_path(last_path, self.play_context, auto_play=False, start_pos=last_pos)

    def _save_library(self):
        if self._loading: return          
        data = {
            "version": 2,
            "local": [t.path for t in self.tracks if not t.is_remote],
            "online": [t.to_dict() for t in self.tracks if t.is_remote],
            "favorites": sorted(self.favorites),
            "playlists": self.playlists,
        }
        tmp = self.lib_file.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            if self.lib_file.exists():
                try: shutil.copy2(self.lib_file, self.lib_file.with_suffix(".bak"))
                except OSError: pass
            os.replace(tmp, self.lib_file)      
        except OSError as e:
            print(f"Gagal menyimpan koleksi: {e}", file=sys.stderr)

    def refresh_views(self):
        self.home.set_tracks(self.tracks); self.search.set_tracks(self.tracks)
        self.empty_card.setVisible(not self.tracks); self.lib_list.setVisible(bool(self.tracks))
        self.lib_list.clear()
        for t in self.tracks:
            item = QListWidgetItem(); item.setSizeHint(QSize(0, 64))
            item.setData(Qt.ItemDataRole.UserRole, t.path)
            self.lib_list.addItem(item); self.lib_list.setItemWidget(item, TrackCell(t, 48))
            
        self.pl_list.clear()
        for name in sorted(self.playlists.keys()): self.pl_list.addItem(name)
        
        if self.stack.currentWidget() == self.fav_page: self._open_fav()
        if self.stack.currentWidget() == self.queue_page: self._open_queue()
        if self.stack.currentWidget() == self.pl_page:
            items = self.pl_list.findItems(self.pl_page.heading.text(), Qt.MatchFlag.MatchExactly)
            if items: self._open_playlist(items[0])
        self._mark_playing()

    def _mark_playing(self):
        self.home.table.set_playing(self.current_path)
        self.search.table.set_playing(self.current_path)
        self.fav_page.table.set_playing(self.current_path)
        self.pl_page.table.set_playing(self.current_path)
        self.queue_page.table.set_playing(self.current_path)
        self.online_page.table.set_playing(self.current_path)
        for i in range(self.lib_list.count()):
            w = self.lib_list.itemWidget(self.lib_list.item(i))
            if w: w.set_active(self.lib_list.item(i).data(Qt.ItemDataRole.UserRole) == self.current_path)

    def confirm_remove(self, paths):
        paths = [p for p in paths if self._get_track(p)]
        if not paths: return
        box = QMessageBox(self); box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Hapus dari koleksi")
        box.setText(f"Hapus {len(paths)} lagu dari koleksi?\n\nFile di komputer Anda tidak terhapus.")
        ok = box.addButton("Hapus", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is ok: self.remove_tracks(paths)

    def _lib_selected(self) -> list:
        return [it.data(Qt.ItemDataRole.UserRole) for it in self.lib_list.selectedItems()]

    def _lib_menu(self, pos):
        menu = QMenu(self); item = self.lib_list.itemAt(pos)
        if item:
            if not item.isSelected():
                self.lib_list.clearSelection(); item.setSelected(True)
            paths = self._lib_selected()
            play = menu.addAction("Putar"); play.setEnabled(len(paths) == 1)
            play.triggered.connect(lambda _=False: self.play_path(paths[0], [t.path for t in self.tracks]))
            menu.addAction("Tambahkan ke Antrean").triggered.connect(lambda _=False: self._handle_table_action("queue", paths))
            menu.addAction("Tambahkan ke Favorit").triggered.connect(lambda _=False: self._handle_table_action("fav", paths))
            menu.addAction("Tambahkan ke Playlist...").triggered.connect(lambda _=False: self._handle_table_action("playlist", paths))
            menu.addSeparator()
            rm = menu.addAction("Hapus dari koleksi" if len(paths) == 1 else f"Hapus {len(paths)} lagu")
            rm.triggered.connect(lambda _=False: self.confirm_remove(paths))
            menu.addSeparator()
        if self.tracks:
            menu.addAction("Kosongkan koleksi…").triggered.connect(lambda _=False: self.clear_library())
        if not menu.isEmpty(): menu.exec(self.lib_list.viewport().mapToGlobal(pos))

    def clear_library(self):
        if not self.tracks: return
        box = QMessageBox(self); box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Kosongkan koleksi")
        box.setText(f"Hapus seluruh {len(self.tracks)} lagu dari koleksi?")
        ok = box.addButton("Kosongkan", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is ok: self.remove_tracks([t.path for t in self.tracks])

    def remove_tracks(self, paths):
        removed = set(paths)
        if not removed: return
        
        if self.current_path in removed:
            self._want_play = False
            self.player.stop(); self.player.setSource(QUrl()); self.current_path = ""
            self.progress.setRange(0, 0); self.cur_label.setText("0:00"); self.total_label.setText("0:00")
            
        self.history = [h for h in self.history if h not in removed]
        self.play_context = [p for p in self.play_context if p not in removed]
        self.queue = [p for p in self.queue if p not in removed]
        self.favorites.difference_update(removed)
        for pl in self.playlists.values(): pl[:] = [p for p in pl if p not in removed]
            
        self.tracks = [t for t in self.tracks if t.path not in removed]
        alive = {t.path for t in self.tracks}
        self._probe_queue = [t for t in self._probe_queue if t.path in alive]
        for p in removed:
            if p.startswith(PREFIX_YT): self.api.delete_cached(p[len(PREFIX_YT):])
        self._save_library(); self.refresh_views(); self._update_now_playing()

    def _open_online(self):
        self.btn_online.setChecked(True)
        self.stack.setCurrentWidget(self.online_page)
        if not self.online_results: self.online_page.set_status("Cari dan temukan lagu dari Audius, Jamendo, atau YouTube Music.")
        self.online_page.input.setFocus()

    def _online_settings(self):
        dlg = OnlineSettingsDialog(self, self.api.jamendo_id, self.auto_cache)
        if dlg.exec() != QDialog.DialogCode.Accepted: return
        jid, auto = dlg.values()
        self.settings.setValue("jamendo_client_id", jid)
        self.api.configure(jid)
        self.auto_cache = auto
        self.settings.setValue("yt_auto_cache", auto)

    def _online_search(self, query: str, provider: str):
        q = query.strip()
        if not q: return
        self._search_token += 1
        self.online_page.set_status(f"Mencari “{q}” di {provider}…")
        w = Worker(self.api.search, self._search_token, q, provider, 30)
        w.signals.done.connect(self._on_online_results); w.signals.failed.connect(self._on_online_search_failed)
        self.net_pool.start(w)

    def _on_online_results(self, token, items):
        if token != self._search_token: return
        tracks = []
        for d in items:
            path = d["id"]
            t = self._remote.get(path)
            if t is None:
                t = Track(path=path, title=d["title"], artist=d["artist"], album=d["album"], 
                          duration=d["duration"], cover_url=d["cover_url"], stream_url=d["stream_url"])
                self._remote[path] = t
            tracks.append(t)
        self.online_results = tracks
        self.online_page.set_tracks(tracks)
        self.online_page.set_status(f"{len(tracks)} hasil. Klik dua kali untuk memutar, klik kanan untuk menambah ke koleksi."
                                if tracks else "Tidak ada hasil.")
        self._mark_playing()
        for t in tracks: self._fetch_cover(t)

    def _on_online_search_failed(self, token, msg: str):
        if token != self._search_token: return
        self.online_page.set_status(f"Pencarian gagal: {msg}")

    def _online_remove_results(self, paths: list):
        gone = set(paths)
        self.online_results = [t for t in self.online_results if t.path not in gone]
        self.online_page.set_tracks(self.online_results); self._mark_playing()

    def _ensure_in_library(self, paths: list) -> int:
        known = {t.path for t in self.tracks}
        added = []
        for p in paths:
            t = self._remote.get(p)
            if t is not None and p not in known:
                self.tracks.append(t); known.add(p); added.append(t)
        if added:
            self._save_library(); self.refresh_views()
            if self.auto_cache:
                for t in added:
                    if t.path.startswith(PREFIX_YT): self._prefetch_vid(t.path[len(PREFIX_YT):])
        return len(added)

    def _fetch_cover(self, t: Track):
        if t.cover is not None or not t.cover_url or t.path in self._cover_pending: return
        self._cover_pending.add(t.path)
        w = Worker(self.api.fetch_bytes, t.path, t.cover_url)
        w.signals.done.connect(self._on_cover); w.signals.failed.connect(self._on_cover_failed)
        self.cover_pool.start(w)

    def _on_cover(self, path, data):
        self._cover_pending.discard(path)
        t = self._remote.get(path)
        if t is None or not data: return
        img = QImage.fromData(data)
        if img.isNull(): return
        t.cover = img
        if any(x.path == path for x in self.tracks): self._cover_lib_dirty = True
        self._cover_timer.start()

    def _on_cover_failed(self, path, _msg: str):
        self._cover_pending.discard(path)

    def _refresh_after_covers(self):
        self.online_page.set_tracks(self.online_results)
        if self._cover_lib_dirty:
            self._cover_lib_dirty = False; self.refresh_views()
        self._mark_playing()
        cur = self._get_track(self.current_path)
        if cur is not None:
            self.np_cover.setPixmap(make_cover(cur, 56, 4)); self.home.hero.set_track(cur)

    def _probe_next(self):
        if not self._probe_queue:
            self._probing = False; self.refresh_views(); return
        self._probing = True; self._probe_track = self._probe_queue.pop(0)
        self._probe_token += 1
        self.probe.setSource(QUrl.fromLocalFile(self._probe_track.path))
        QTimer.singleShot(4000, lambda t=self._probe_token: self._probe_timeout(t))

    def _probe_timeout(self, token: int):
        if self._probing and token == self._probe_token: self._probe_next()

    def _on_probe_status(self, status):
        if not self._probing or self._probe_track is None: return
        S = QMediaPlayer.MediaStatus
        if status == S.LoadedMedia:
            t = self._probe_track; t.duration = self.probe.duration()
            md = self.probe.metaData(); K = QMediaMetaData.Key
            def meta(key) -> str:
                v = md.value(key)
                if isinstance(v, (list, tuple)): v = ", ".join(str(x) for x in v)
                return str(v).strip() if v else ""
            title = meta(K.Title); artist = meta(K.ContributingArtist) or meta(K.AlbumArtist) or meta(K.Author)
            if title: t.title = title
            if artist: t.artist = artist
            if album := meta(K.AlbumTitle): t.album = album
            for key in (K.ThumbnailImage, K.CoverArtImage):
                img = md.value(key)
                if isinstance(img, QImage) and not img.isNull():
                    t.cover = img; break
            self._probe_next()
        elif status == S.InvalidMedia: self._probe_next()

    def play_path(self, path: str, context: list[str] = None, auto_play: bool = True, start_pos: int = 0):
        t = self._get_track(path)
        if not t: return
        self.current_path = path
        if context is not None: self.play_context = context
        if path in self.play_context: self._ctx_anchor = path

        self.history.append(path); self.history = self.history[-200:]
        self._stream_token += 1
        self._pending_seek = start_pos if start_pos > 0 else 0
        self._want_play = auto_play
        self._recoveries = 0
        self._last_pos = -1; self._last_pos_t = time.monotonic()

        self.player.stop()
        self._load_track(t, auto_play)

    def _load_track(self, t: Track, auto_play: bool):
        if t.path.startswith(PREFIX_YT):
            cached = self.api.cached_yt_file(t.path[len(PREFIX_YT):])
            if not cached:
                self._update_now_playing(); self._mark_playing()
                self.np_artist.setText("Memuat lagu dari YouTube Music…")
                self._prepare_yt(t, auto_play)
                return
            self.player.setSource(QUrl.fromLocalFile(cached))
        elif t.is_remote:
            if not t.stream_url:
                self._update_now_playing(); self._mark_playing(); return
            self.player.setSource(QUrl(t.stream_url))
        else:
            self.player.setSource(QUrl.fromLocalFile(t.path))

        if auto_play: self.player.play()
        else: self.player.pause()
        self._update_now_playing(); self._mark_playing()

    def _prepare_yt(self, t: Track, auto_play: bool):
        ctx = (self._stream_token, t.path, auto_play)
        w = Worker(self.api.prepare_yt_audio, ctx, t.path[len(PREFIX_YT):])
        w.signals.done.connect(self._on_yt_ready)
        w.signals.failed.connect(self._on_yt_failed)
        self.dl_pool.start(w, 10)           

    def _on_yt_ready(self, ctx, res: dict):
        token, path, auto_play = ctx
        t = self._get_track(path)
        if t is None: return
        if res.get("url"): t.stream_url, t.stream_time = res["url"], time.time()
        if token != self._stream_token: return        
        if res.get("file"): self.player.setSource(QUrl.fromLocalFile(res["file"]))
        elif res.get("url"): self.player.setSource(QUrl(res["url"]))
        else:
            self._on_yt_failed(ctx, "sumber audio tidak ditemukan"); return
        if auto_play: self.player.play()
        else: self.player.pause()
        self._update_now_playing(); self._mark_playing()

    def _on_yt_failed(self, ctx, msg: str):
        token, path, _ = ctx
        if token != self._stream_token: return
        self.np_artist.setText(f"Gagal memutar YT Music: {msg}")
        self._skip_after_error()

    def _prefetch_vid(self, vid: str):
        if vid in self._prefetching or self.api.cached_yt_file(vid): return
        self._prefetching.add(vid)
        w = Worker(self.api.prepare_yt_audio, vid, vid)
        w.signals.done.connect(self._on_prefetch_done)
        w.signals.failed.connect(self._on_prefetch_failed)
        self.dl_pool.start(w, 0)

    def _on_prefetch_done(self, vid, _res): self._prefetching.discard(vid)
    def _on_prefetch_failed(self, vid, _msg): self._prefetching.discard(vid)

    def _prefetch_next(self):
        nxt = self._pick_next(auto=True, consume=False)
        if nxt and nxt.startswith(PREFIX_YT): self._prefetch_vid(nxt[len(PREFIX_YT):])

    def _prune_cache(self):
        keep = {t.path[len(PREFIX_YT):] for t in self.tracks if t.path.startswith(PREFIX_YT)}
        try: self.api.prune_cache(keep)
        except Exception: pass

    def _reload_current(self, pos: int):
        t = self._get_track(self.current_path)
        if t is None: return
        want = self._want_play
        was_local = self.player.source().isLocalFile()
        self._stream_token += 1
        self._last_pos = -1; self._last_pos_t = time.monotonic()
        self._pending_seek = pos
        self.player.stop(); self.player.setSource(QUrl())
        if t.path.startswith(PREFIX_YT):
            if was_local: self.api.delete_cached(t.path[len(PREFIX_YT):])   
            t.stream_url, t.stream_time = "", 0.0
        self._load_track(t, want)

    def _recover(self, msg: str):
        t = self._get_track(self.current_path)
        if t is None: return
        now = time.monotonic()
        if now - self._last_recover < 2.0: return          
        self._last_recover = now
        if t.is_remote and self._recoveries < 2:
            self._recoveries += 1
            self._reload_current(max(0, self.player.position()))
            return
        self.np_artist.setText(f"Tidak dapat memutar: {msg}" if msg else "Tidak dapat memutar file ini")
        self._skip_after_error()

    def _skip_after_error(self):
        if not self._want_play: return
        self._err_streak += 1
        if self._err_streak > 5: return
        tok = self._stream_token
        QTimer.singleShot(1500, lambda: self._auto_skip(tok))

    def _auto_skip(self, tok: int):
        if tok == self._stream_token and self._want_play: self.next_track(auto=True)

    def _watchdog(self):
        if not self.current_path or not self._want_play: return
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState: return
        if time.monotonic() - self._last_pos_t < STALL_SECONDS: return
        self._last_pos_t = time.monotonic()
        dur, pos = self.player.duration(), self.player.position()
        if dur > 0 and pos >= dur - 3000:
            self._schedule_track_end(); return
        self._recover("koneksi macet")

    def _schedule_track_end(self):
        if self._end_handled == self._stream_token: return    
        self._end_handled = self._stream_token
        QTimer.singleShot(0, lambda tok=self._stream_token: self._finish_track(tok))

    def _finish_track(self, tok: int):
        if tok != self._stream_token: return
        if self.repeat == 2:
            self._end_handled = -1
            self.player.setPosition(0); self.player.play()
        else:
            self.next_track(auto=True)

    def _play_from_queue_page(self, path: str):
        try:
            idx = self.queue.index(path)
            self.queue = self.queue[idx+1:]
        except ValueError: pass
        self.play_path(path, context=None)
        if self.stack.currentWidget() == self.queue_page: self._open_queue()

    def toggle_play(self):
        if not self.current_path:
            if self.tracks: self.play_path(random.choice(self.tracks).path if self.shuffle else self.tracks[0].path, [t.path for t in self.tracks])
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else: self.player.play()

    def _pick_next(self, auto: bool, consume: bool) -> Optional[str]:
        q = [p for p in self.queue if self._get_track(p)]
        if q:
            if consume: self.queue = q[1:]
            return q[0]

        ctx = [p for p in self.play_context if self._get_track(p)]
        if not ctx: return None

        if self.shuffle:
            choices = [p for p in ctx if p != self.current_path] or ctx
            if self._shuffle_next not in choices: self._shuffle_next = random.choice(choices)
            nxt = self._shuffle_next
            if consume: self._shuffle_next = None
            return nxt

        anchor = self._ctx_anchor if self._ctx_anchor in ctx else self.current_path
        idx = ctx.index(anchor) if anchor in ctx else -1
        nxt = idx + 1
        if nxt >= len(ctx):
            if auto and self.repeat == 0: return None      
            nxt = 0
        return ctx[nxt]

    def next_track(self, auto: bool = False):
        nxt = self._pick_next(auto, consume=True)
        if nxt is None:
            if auto:
                self._want_play = False
                self.player.stop(); self.player.setPosition(0)
            return
        self.play_path(nxt, auto_play=True)
        if self.stack.currentWidget() == self.queue_page: self._open_queue()

    def prev_track(self):
        ctx = [p for p in self.play_context if self._get_track(p)]
        if not ctx: return
        if self.player.position() > 3000 or not self.current_path:
            self.player.setPosition(0); return

        if self.shuffle and len(self.history) > 1:
            self.history.pop()
            self.play_path(self.history.pop(), context=None, auto_play=True)
            return

        anchor = self._ctx_anchor if self._ctx_anchor in ctx else self.current_path
        idx = ctx.index(anchor) if anchor in ctx else 0
        self.play_path(ctx[(idx - 1) % len(ctx)], context=None, auto_play=True)

    def _toggle_shuffle(self):
        self.shuffle = not self.shuffle; self.btn_shuffle.set_active(self.shuffle)

    def _cycle_repeat(self):
        self.repeat = (self.repeat + 1) % 3
        self.btn_repeat.set_name("repeat1" if self.repeat == 2 else "repeat")
        self.btn_repeat.set_active(self.repeat != 0)

    def _on_volume(self, v: int):
        self.audio.setVolume(v / 100)
        if self.audio.isMuted() and v > 0: self.audio.setMuted(False)
        self.settings.setValue("volume", v); self._update_vol_icon()

    def _toggle_mute(self):
        self.audio.setMuted(not self.audio.isMuted()); self._update_vol_icon()

    def _update_vol_icon(self):
        muted = self.audio.isMuted() or self.vol_slider.value() == 0
        self.vol_btn.set_name("mute" if muted else "volume")

    @staticmethod
    def _dev_id(dev) -> str: return bytes(dev.id()).decode("utf-8", "ignore")

    def _load_output(self):
        saved = self.settings.value("audio_device", "")
        self.output_id = str(saved) if saved else None; self._apply_output()

    def _apply_output(self):
        prev_active = self._active_id
        dev = None
        if self.output_id:
            for d in QMediaDevices.audioOutputs():
                if self._dev_id(d) == self.output_id:
                    dev = d; break
        lost = bool(self.output_id) and dev is None
        if dev is None: dev = QMediaDevices.defaultAudioOutput()
        new_id = self._dev_id(dev) if not dev.isNull() else ""
        if new_id != self._active_id or self.audio.device().isNull():
            self.audio.setDevice(dev); self._active_id = new_id

        self.device_btn.set_active(self.output_id is not None and not lost)
        name = dev.description() if not dev.isNull() else "tidak ada perangkat audio"
        self.device_btn.setToolTip(f"Perangkat: {name}")
        self._refresh_device_chip()

        if lost and prev_active == self.output_id:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            QToolTip.showText(self.device_btn.mapToGlobal(QPoint(-120, -44)),
                              f"Perangkat terputus. Dialihkan ke: {name}", self.device_btn, self.device_btn.rect(), 4000)

    def _on_devices_changed(self): self._apply_output()

    def _choose_device(self, dev_id: Optional[str]):
        self.output_id = dev_id
        if dev_id: self.settings.setValue("audio_device", dev_id)
        else: self.settings.remove("audio_device")
        self._apply_output()

    def _device_menu(self):
        menu = QMenu(self); header = menu.addAction("Putar di perangkat"); header.setEnabled(False); menu.addSeparator()
        auto = menu.addAction(("✓  " if self.output_id is None else "     ") + "Otomatis (ikuti default sistem)")
        auto.triggered.connect(lambda _=False: self._choose_device(None))

        devices = QMediaDevices.audioOutputs()
        if not devices: menu.addAction("Tidak ada perangkat").setEnabled(False)
        for d in devices:
            did = self._dev_id(d)
            label = ("✓  " if self.output_id == did else "     ") + d.description()
            if d.isDefault(): label += "  (default)"
            menu.addAction(label).triggered.connect(lambda _=False, i=did: self._choose_device(i))

        if sys.platform == "win32":
            menu.addSeparator(); bt = menu.addAction("Pengaturan Bluetooth…")
            bt.triggered.connect(lambda _=False: QDesktopServices.openUrl(QUrl("ms-settings:bluetooth")))

        size = menu.sizeHint()
        menu.exec(self.device_btn.mapToGlobal(QPoint(self.device_btn.width() - size.width(), -size.height())))

    def _on_position(self, pos: int):
        self._last_pos = pos; self._last_pos_t = time.monotonic()
        if not self.progress.isSliderDown():
            self.progress.blockSignals(True)
            self.progress.setValue(pos)
            self.progress.blockSignals(False)
            self.cur_label.setText(fmt(pos))

    def _on_duration(self, dur: int):
        self.progress.setRange(0, max(0, dur)); self.total_label.setText(fmt(dur))

    def _on_state(self, state):
        P = QMediaPlayer.PlaybackState
        playing = state == P.PlayingState
        self.btn_play.set_name("pause" if playing else "play")
        self.btn_play.setToolTip("Jeda" if playing else "Putar")
        self._sync_visuals(playing)

        if playing:
            self._want_play = True
            self._last_pos_t = time.monotonic()
            if self._prefetch_token != self._stream_token:      
                self._prefetch_token = self._stream_token
                self._prefetch_next()
        elif state == P.PausedState:
            self._want_play = False
        elif state == P.StoppedState and self._want_play and self.current_path:
            dur = self.player.duration()
            if dur > 0 and self._last_pos > 0 and self._last_pos >= dur - 2500:
                self._schedule_track_end()

    def _on_status(self, status):
        S = QMediaPlayer.MediaStatus
        if status in (S.LoadedMedia, S.BufferedMedia):
            self._err_streak = 0
        if status == S.LoadedMedia:
            if self._pending_seek > 0:
                self.player.setPosition(self._pending_seek)
                self._pending_seek = 0
            self._on_duration(self.player.duration())
        elif status == S.EndOfMedia:
            self._schedule_track_end()

    def _on_error(self, _error, message: str):
        self._recover(message)

    def _update_now_playing(self):
        t = self._get_track(self.current_path)
        if t:
            self.np_cover.setPixmap(make_cover(t, 56, 4))
            self.np_title.setText(t.title)
            self.np_artist.setText(t.artist)
            self.btn_like.set_name("heart_fill" if t.path in self.favorites else "heart")
            self.btn_like.set_active(t.path in self.favorites)
            accent = t.color.darker(210)
            self.setWindowTitle(f"{t.title} • {t.artist}")
        else:
            self.np_cover.setPixmap(make_cover(None, 56, 4))
            self.np_title.setText("Belum ada lagu")
            self.np_artist.setText("Pilih lagu untuk mulai")
            self.btn_like.set_name("heart")
            self.btn_like.set_active(False)
            accent = QColor(ambient_accent())
            self.setWindowTitle("Melodi")

        self.home.hero.set_track(t)
        self.player_bar.set_accent(accent)
        self._update_tray_tip()
        if self.stack.currentWidget() is self.queue_page: self._open_queue()
        for page in (self.home, self.search, self.queue_page, self.settings_page):
            if hasattr(page, 'set_accent'): page.set_accent(accent)


_LOG_FILE = None

def _install_crash_handlers():
    import faulthandler
    import traceback
    global _LOG_FILE
    base = Path(os.environ.get("APPDATA") or Path.home()) / "Melodi"
    try: base.mkdir(parents=True, exist_ok=True)
    except OSError: base = Path.home()
    log_path = base / "melodi_error.log"
    try:
        _LOG_FILE = open(log_path, "a", encoding="utf-8")
        faulthandler.enable(file=_LOG_FILE)
    except OSError: _LOG_FILE = None

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        print(text, file=sys.stderr)
        if _LOG_FILE:
            _LOG_FILE.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n{text}"); _LOG_FILE.flush()
        try: QMessageBox.critical(None, "Melodi - terjadi kesalahan", f"{text[-1800:]}\n\nDetail tersimpan di:\n{log_path}")
        except Exception: pass
    sys.excepthook = hook

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Melodi")
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Melodi.Player")
        except Exception: pass
    app.setWindowIcon(app_icon())
    _install_crash_handlers()

    font = QFont(); font.setFamilies(["Circular Std", "Segoe UI", "Inter", "Helvetica Neue", "Arial"]); font.setPointSize(10)
    app.setFont(font)

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(PANEL)); pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor("#181818")); pal.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT)); pal.setColor(QPalette.ColorRole.Button, QColor("#282828"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT)); pal.setColor(QPalette.ColorRole.Highlight, QColor(GREEN))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000")); pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#282828"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    app.setPalette(pal); app.setStyleSheet(APP_QSS)

    try:
        win = MainWindow()
        app.aboutToQuit.connect(win._save_final_state)
    except Exception:
        sys.excepthook(*sys.exc_info())
        return 1
        
    win.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
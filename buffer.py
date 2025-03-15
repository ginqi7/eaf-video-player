#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2018 Andy Stewart
#
# Author:     Andy Stewart <lazycat.manatee@gmail.com>
# Maintainer: Andy Stewart <lazycat.manatee@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from math import floor
import os

import pysrt
from core.buffer import Buffer
from core.utils import interactive, message_to_emacs, eval_in_emacs, PostGui
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QEvent, QRectF, QSizeF, Qt, QUrl
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

class AppBuffer(Buffer):
    def __init__(self, buffer_id, url, arguments):
        Buffer.__init__(self, buffer_id, url, arguments, True)
        self.wheel_delta = 0
        self.background_color = QColor(0, 0, 0)

        self.add_widget(
            VideoPlayer(self.theme_background_color, self.theme_foreground_color)
        )
        self.buffer_widget.play(url)

        self.build_all_methods(self.buffer_widget)

    def all_views_hide(self):
        # Pause video before all views hdie, otherwise will got error "Internal data stream error".
        if (
            self.buffer_widget.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.buffer_widget.media_player.pause()
            self.buffer_widget.video_need_replay = True

    def some_view_show(self):
        if self.buffer_widget.video_need_replay is True:
            self.buffer_widget.media_player.play()

    def save_session_data(self):
        return str(self.buffer_widget.media_player.position())

    def restore_session_data(self, session_data):
        position = int(session_data)
        self.buffer_widget.media_player.setPosition(position)

    def toggle_play(self):
        if (
            self.buffer_widget.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        ):
            self.buffer_widget.media_player.pause()
            self.buffer_widget.video_need_replay = False
        else:
            self.buffer_widget.media_player.play()
            self.buffer_widget.video_need_replay = True

    def destroy_buffer(self):
        self.buffer_widget.media_player.pause()

        super().destroy_buffer()

    def wheelEvent(self, event):
        delta = event.delta()
        self.wheel_delta += delta
        if self.wheel_delta < -300:
            self.play_backward_subtitle()
            self.wheel_delta = 0
        elif self.wheel_delta > 300:
            self.play_forward_subtitle()
            self.wheel_delta = 0

    def mousePressEvent(self, event):
        # if self.buffer_widget.progress_bar.isHidden():
        self.toggle_play()
        event.accept()

    @PostGui()
    def message_box_update(self, text, x, y):
        # print(self.buffer_widget.message_box)
        message_box = self.buffer_widget.message_box
        message_box.update(text, x, y)


class VideoPlayer(QWidget):
    def __init__(self, theme_background_color, theme_foreground_color):
        super(VideoPlayer, self).__init__()
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor(0, 0, 0, 255)))

        self.graphics_view = QGraphicsView(self.scene)
        self.graphics_view.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.graphics_view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.graphics_view.setFrameStyle(0)
        self.graphics_view.setStyleSheet(
            "QGraphicsView {background: transparent; border: 3px; outline: none;}"
        )

        self.is_button_press = False

        self.video_item = QGraphicsVideoItem()

        self.panel_height = 60
        self.progress_bar_height = 60
        self.panel_padding_x = 0
        self.panel_padding_y = (self.panel_height - self.progress_bar_height) / 2

        self.control_panel_widget = QWidget()
        self.control_panel_widget.setStyleSheet("background-color: transparent;")
        self.progress_bar_layout = QHBoxLayout(self.control_panel_widget)
        self.progress_bar_layout.setContentsMargins(
            int(self.panel_padding_x),
            int(self.panel_padding_y),
            int(self.panel_padding_x),
            int(self.panel_padding_x),
        )

        self.control_panel = ControlPanel()

        self.progress_bar = ProgressBar(theme_background_color, theme_foreground_color)
        self.progress_bar.progress_changed.connect(self.update_video_progress)
        self.progress_bar_layout.addWidget(self.progress_bar)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.graphics_view)

        self.subtitles = Subtitles(self)
        self.message_box = MessageBox(self)

        self.scene.addItem(self.video_item)
        self.scene.addItem(self.control_panel)
        self.scene.addItem(self.subtitles)
        self.scene.addItem(self.message_box)

        self.control_panel_proxy_widget = self.scene.addWidget(
            self.control_panel_widget
        )

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()

        self.media_player.positionChanged.connect(self.progress_change)
        self.media_player.setVideoOutput(self.video_item)
        self.media_player.setAudioOutput(self.audio_output)

        self.video_need_replay = False
        self.video_seek_durcation = 10000  # in milliseconds

        QtCore.QTimer().singleShot(2000, self.hide_control_panel)

        self.graphics_view.viewport().installEventFilter(self)

    def update_video_progress(self, percent):
        self.media_player.setPosition(int(self.media_player.duration() * percent))

    def progress_change(self, position):
        self.progress_bar.update_progress(self.media_player.duration(), position)
        self.subtitles.update_subtitle(position)

    def resizeEvent(self, event):
        self.video_item.setSize(QSizeF(event.size().width(), event.size().height()))

        self.control_panel.update_size(event.size().width(), self.panel_height)
        self.control_panel.setPos(0, event.size().height() - self.panel_height)

        self.control_panel_widget.resize(event.size().width(), self.panel_height)
        self.control_panel_proxy_widget.setPos(
            0, event.size().height() - self.panel_height
        )

        self.progress_bar.resize(
            event.size().width() - self.panel_padding_x * 2, self.progress_bar_height
        )

        QWidget.resizeEvent(self, event)

    def play(self, url):
        self.subtitles.open(url)
        self.media_player.setSource(QUrl.fromLocalFile(url))
        self.media_player.play()

    def eventFilter(self, obj, event):
        if event.type() in [QEvent.Type.MouseButtonPress]:
            self.is_button_press = True
        elif event.type() in [QEvent.Type.MouseButtonRelease]:
            self.is_button_press = False

        if event.type() == QEvent.Type.MouseMove:
            if event.position().y() > self.height() - self.progress_bar_height:
                self.show_control_panel()
            else:
                self.hide_control_panel()

        return False

    def hide_control_panel(self):
        self.control_panel.hide()
        self.control_panel_proxy_widget.hide()

    def show_control_panel(self):
        self.control_panel.show()
        self.control_panel_proxy_widget.show()

    def download_subtitles_thread(self, url):
        """Subtitle download function executed in multiple processes"""
        from babelfish import Language
        from subliminal import download_best_subtitles, region, save_subtitles, scan_video
        try:
            # Configure Cache
            region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})

            # Scan Video
            video = scan_video(url)

            # Download the best subtitles.
            subtitles = download_best_subtitles([video], {Language('eng')})

            # Save subtitles to disk
            save_subtitles(video, subtitles[video])
            print("Subtitle download complete.")
            message_to_emacs("Subtitle download complete.")

        except Exception as e:
            print(f"Error downloading subtitles: {e}")
            message_to_emacs(f"Error downloading subtitles: {e}")

    @interactive
    def play_forward_subtitle(self):
        subs = self.subtitles.subs
        current_sub = self.subtitles.current_sub
        # The index starts from 1 in subtitles, but the index of the array starts from 0.
        index = min(len(subs), current_sub.index)
        start = subs[index].start
        self.media_player.setPosition(floor(self.subtitles.parse_srt_time(start)))
        message_to_emacs(f"Forward to: {start}")

    @interactive
    def play_backward_subtitle(self):
        subs = self.subtitles.subs
        current_sub = self.subtitles.current_sub
        # The index starts from 1 in subtitles, but the index of the array starts from 0.
        index = max(0, current_sub.index - 2)
        start = subs[index].start
        self.media_player.setPosition(floor(self.subtitles.parse_srt_time(start)))
        message_to_emacs(f"Forward to: {start}")

    @interactive
    def play_forward(self):
        video_position = self.media_player.position()
        self.media_player.setPosition(video_position + self.video_seek_durcation)
        message_to_emacs(
            "Forward to: {}%".format(
                self.media_player.position() / self.media_player.duration() * 100
            )
        )

    @interactive
    def play_backward(self):
        video_position = self.media_player.position()
        self.media_player.setPosition(
            max(video_position - self.video_seek_durcation, 0)
        )
        message_to_emacs(
            "Forward to: {}%".format(
                self.media_player.position() / self.media_player.duration() * 100
            )
        )

    @interactive
    def increase_volume(self):
        self.audio_output.setVolume(self.audio_output.volume() + 0.1)
        message_to_emacs(
            "Increase volume to: {}%".format(self.audio_output.volume() * 100)
        )

    @interactive
    def decrease_volume(self):
        self.audio_output.setVolume(self.audio_output.volume() - 0.1)
        message_to_emacs(
            "Decrease volume to: {}%".format(self.audio_output.volume() * 100)
        )

    @interactive
    def download_subtitles(self):
        import threading
        message_to_emacs("Downloading subtitle.")
        # Retrieve video path
        url = self.media_player.source().path()
        thread = threading.Thread(target=self.download_subtitles_thread, args=(url,))
        thread.start()

    @interactive
    def reload_subtitles(self):
        url = self.media_player.source().path()
        self.subtitles.open(url)

    @interactive
    def restart(self):
        self.media_player.setPosition(0)


class ControlPanel(QtWidgets.QGraphicsItem):
    def __init__(self, parent=None):
        super(ControlPanel, self).__init__(parent)
        self.height = 0
        self.width = 0
        self.background_color = QColor(0, 0, 0, 255)
        self.setOpacity(0.9)

    def update_size(self, width, height):
        self.width = width
        self.height = height
        self.update()

    def paint(self, painter, option, widget):
        painter.setPen(self.background_color)
        painter.setBrush(self.background_color)
        painter.drawRect(0, 0, self.width, self.height)

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)


class ProgressBar(QWidget):
    progress_changed = QtCore.pyqtSignal(float)

    def __init__(self, theme_background_color, theme_foreground_color):
        super(QWidget, self).__init__()
        self.foreground_color = QColor(theme_foreground_color)
        self.background_color = QColor(theme_background_color)
        self.position = 0
        self.duration = 0
        self.is_press = False
        self.render_height = 10

    def update_progress(self, duration, position):
        self.position = position
        self.duration = duration
        self.update()

    def mousePressEvent(self, event):
        self.is_press = True
        self.progress_changed.emit(event.position().x() * 1.0 / self.width())

    def mouseReleaseEvent(self, event):
        self.is_press = False

    def mouseMoveEvent(self, event):
        if self.is_press:
            self.progress_changed.emit(event.position().x() * 1.0 / self.width())

    def paintEvent(self, event):
        painter = QPainter(self)

        render_y = (self.height() - self.render_height) / 2

        painter.setPen(self.background_color)
        painter.setBrush(self.background_color)
        painter.drawRect(0, int(render_y), int(self.width()), int(self.render_height))

        if self.duration > 0:
            painter.setPen(self.foreground_color)
            painter.setBrush(self.foreground_color)
            painter.drawRect(
                0,
                int(render_y),
                int(self.width() * self.position / self.duration),
                int(self.render_height),
            )


class Subtitles(QtWidgets.QGraphicsTextItem):
    def __init__(self, video_player: VideoPlayer):
        super(Subtitles, self).__init__()
        self.video_player = video_player
        self.x_offset = 0
        self.y_offset = 0
        self.subs = []
        self.current_sub = None

    def searchSubtitlesFile(self, url):
        base = os.path.splitext(url)[0]
        directory = os.path.dirname(url)
        srt_files = [f for f in os.listdir(directory) if f.endswith(".srt")]
        for srt_file in srt_files:
            srt_path = os.path.join(directory, srt_file)
            if srt_path.startswith(base):
                return srt_path

    def open(self, url):
        subtitle_url = self.searchSubtitlesFile(url)
        if subtitle_url and os.path.exists(subtitle_url):
            message_to_emacs(f'Subtitle is: {subtitle_url}')
            self.subs = pysrt.open(subtitle_url, encoding="utf-8")
        else:
            message_to_emacs("There is no subtitles.")

    def parse_srt_time(self, sub_rip_time):
        total_seconds = (
            sub_rip_time.hours * 3600
            + sub_rip_time.minutes * 60
            + sub_rip_time.seconds
            + sub_rip_time.milliseconds / 1000.0
        )
        return total_seconds * 1000

    def update_subtitle(self, position):
        for sub in self.subs:
            start_time = self.parse_srt_time(sub.start)
            end_time = self.parse_srt_time(sub.end)
            if start_time <= position and end_time >= position:
                if self.current_sub != sub:
                    self.current_sub = sub
                    self.update_view(sub.text)

    def add_child(self, child: QtWidgets.QGraphicsTextItem):
        child.setParentItem(self)
        child.setPos(self.x_offset, self.y_offset)
        video_size = self.video_player.size()
        max_width = video_size.width() - 200
        child_rect = child.boundingRect()
        self.x_offset += child_rect.width() + 5
        if self.x_offset >= max_width:
            self.x_offset = 0
            self.y_offset += child_rect.height() + 1

    def reposition(self):
        video_size = self.video_player.size()
        subtitle_rect = self.childrenBoundingRect()
        x_position = (video_size.width() - subtitle_rect.width()) / 2
        y_position = (video_size.height() - subtitle_rect.height()) - 60
        for item in self.childItems():
            pos = item.pos()
            item.setPos(x_position + pos.x(), y_position + pos.y())

    def update_view(self, text: str):
        self.clear()
        words = text.split()
        for word in words:
            subtitle_word = SubtitleWord(word, self.video_player)
            self.add_child(subtitle_word)
        self.reposition()

    def clear(self):
        children = self.childItems()
        self.x_offset = 0
        self.y_offset = 0
        for child in children:
            self.scene().removeItem(child)
            del child


class SubtitleWord(QtWidgets.QGraphicsTextItem):
    def __init__(self, text, video_player: VideoPlayer):
        super(SubtitleWord, self).__init__(text)
        self.video_player = video_player
        self.setAcceptHoverEvents(True)

        # Set Font
        font = QFont("Alegreya")
        font.setPixelSize(50)
        self.setFont(font)

        # Text front color is white
        self.setDefaultTextColor(QColor("white"))

        # Add Black Outline
        self.setOutlineEffect()


    def setOutlineEffect(self):

        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(3)
        shadow.setColor(QColor("black"))
        shadow.setOffset(1, 1)

        self.setGraphicsEffect(shadow)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.explain_sentence(event)
        else:
            super().mousePressEvent(event)

    def explain_sentence(self, event):
        self.video_player.media_player.pause()
        subtitles = self.video_player.subtitles
        sentence = " ".join([item.toPlainText() for item in subtitles.childItems()])
        x = subtitles.childrenBoundingRect().x()
        y = subtitles.childrenBoundingRect().y()
        eval_in_emacs("eaf-video-player-explain-sentence", [sentence, x, y])

    def hoverEnterEvent(self, event):
        self.video_player.media_player.pause()
        self.setDefaultTextColor(QColor("green"))
        scene_pos = self.mapToScene(event.pos())
        self.video_player.message_box.show()
        x = scene_pos.x()
        y = self.parentItem().childrenBoundingRect().y()
        eval_in_emacs("eaf-video-player-lookup", [self.toPlainText(), x, y])

    def hoverLeaveEvent(self, event):
        self.video_player.media_player.play()
        self.setDefaultTextColor(QColor("white"))
        self.video_player.message_box.hide()


class MessageBox(QtWidgets.QGraphicsTextItem):
    def __init__(
        self, video_player: VideoPlayer, background_color=Qt.GlobalColor.white
    ):
        super().__init__()
        self.video_player = video_player
        font = QFont("TsangerJinKai04")
        self.setDefaultTextColor(QColor("white"))
        font.setPixelSize(15)
        self.hide()
        self.setFont(font)
        self.background_color = background_color

    def paint(self, painter, option, widget=None):

        # Transparent Black Rounded Rectangle
        painter.setBrush(QColor(0, 0, 0, 128))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.boundingRect(), 10, 10)
        super().paint(painter, option, widget)

    def update(self, text: str, x, y):
        # `-1` unsets text width, allowing it to adjust automatically based on content.
        self.setTextWidth(-1)
        self.setPlainText(text)
        rect = self.boundingRect()

        max_width = self.video_player.width()

        if rect.width() >= max_width:
            # If the text width exceeds the maximum width, set the text to the maximum width.
            self.setTextWidth(max_width - 50)
            rect = self.boundingRect()

        if x + rect.width() / 2 >= max_width:
            x  = max_width - rect.width()
        else:
            x = x - rect.width() / 2

        y = y - rect.height()

        x = 0 if x < 0 else x
        y = 0 if y < 0 else y

        self.setPos(x, y)

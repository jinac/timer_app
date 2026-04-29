#!/usr/bin/env python3

import sys
import time
import json
import os

from PyQt6.QtCore import pyqtSignal, Qt, QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QProgressBar, QPushButton, QWidget, QLineEdit, QListWidget, QTabWidget, QGroupBox
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class SettingsManager:
    """
    Handles loading, saving, and managing workout profiles in a JSON file.
    """
    def __init__(self, filename="workouts.json"):
        self.filename = os.path.join(BASE_DIR, filename)
        self.profiles = self.load_all()

    def load_all(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_profile(self, name, duration_minutes, num_sets):
        self.profiles[name] = {
            "duration_minutes": duration_minutes,
            "num_sets": num_sets
        }
        self._write_to_disk()

    def delete_profile(self, name):
        if name in self.profiles:
            del self.profiles[name]
            self._write_to_disk()

    def list_profiles(self):
        return list(self.profiles.keys())

    def get_profile(self, name):
        return self.profiles.get(name)

    def _write_to_disk(self):
        with open(self.filename, 'w') as f:
            json.dump(self.profiles, f, indent=4)



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.setWindowTitle("Workout Timer")
        self.resize(400, 500)

        # Audio Setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.set_audio_paths()

    def set_audio_paths(self):
        self.transition_url = QUrl.fromLocalFile(os.path.join(BASE_DIR, "oot_navi_hey1.mp3"))
        self.completion_url = QUrl.fromLocalFile(os.path.join(BASE_DIR, "139-item-catch.mp3"))


        # UI Elements
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # --- Tab 1: Active Timer ---
        self.timer_tab = QWidget()
        self.timer_layout = QVBoxLayout(self.timer_tab)
        
        self.timer_label = QLabel("00:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 48px; font-weight: bold;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        self.timer_controls_layout = QVBoxLayout()
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        self.timer_controls_layout.addWidget(self.pause_button)
        
        self.start_button = QPushButton("Start Workout")
        self.start_button.clicked.connect(self.toggle_timer)
        self.timer_controls_layout.addWidget(self.start_button)
        
        self.timer_layout.addWidget(self.timer_label)
        self.timer_layout.addWidget(self.progress_bar)
        self.timer_layout.addLayout(self.timer_controls_layout)
        self.timer_layout.addStretch()
        
        # --- Tab 2: Profiles ---
        self.profiles_tab = QWidget()
        self.profiles_layout = QVBoxLayout(self.profiles_tab)
        
        # Create Profile Group
        self.create_profile_group = QGroupBox("Create New Profile")
        self.create_profile_layout = QVBoxLayout(self.create_profile_group)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile Name")
        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("Duration (minutes)")
        self.sets_input = QLineEdit()
        self.sets_input.setPlaceholderText("Number of Sets")
        self.save_button = QPushButton("Save Profile")
        self.save_button.clicked.connect(self.save_profile_clicked)
        self.create_profile_layout.addWidget(self.name_input)
        self.create_profile_layout.addWidget(self.duration_input)
        self.create_profile_layout.addWidget(self.sets_input)
        self.create_profile_layout.addWidget(self.save_button)
        
        # Manage Profile Group
        self.manage_profile_group = QGroupBox("Saved Profiles")
        self.manage_profile_layout = QVBoxLayout(self.manage_profile_group)
        self.profile_list = QListWidget()
        self.profile_list.itemClicked.connect(self.load_profile_clicked)
        self.delete_button = QPushButton("Delete Selected Profile")
        self.delete_button.clicked.connect(self.delete_profile_clicked)
        self.manage_profile_layout.addWidget(self.profile_list)
        self.manage_profile_layout.addWidget(self.delete_button)
        
        self.profiles_layout.addWidget(self.create_profile_group)
        self.profiles_layout.addWidget(self.manage_profile_group)
        self.profiles_layout.addStretch()
        
        # Add tabs to the main tab widget
        self.tabs.addTab(self.timer_tab, "Active Timer")
        self.tabs.addTab(self.profiles_tab, "Profiles")
        
        self.refresh_profile_list()



        # Timer State
        self.timer = QTimer()
        self.timer.timeout.connect(self.timer_tick)
        self.is_running = False
        self.is_paused = False
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.num_sets = 0
        self.current_set = 1
        self.interval_duration = 0
        self.start_time = 0

    def refresh_profile_list(self):
        self.profile_list.clear()
        self.profile_list.addItems(self.settings_manager.list_profiles())

    def save_profile_clicked(self):
        name = self.name_input.text()
        try:
            dur = int(self.duration_input.text())
            sets = int(self.sets_input.text())
            if name:
                self.settings_manager.save_profile(name, dur, sets)
                self.refresh_profile_list()
                self.name_input.clear()
                self.duration_input.clear()
                self.sets_input.clear()
        except ValueError:
            pass # In a real app, show an error dialog

    def load_profile_clicked(self, item):
        name = item.text()
        profile = self.settings_manager.get_profile(name)
        if profile:
            self.name_input.setText(name)
            self.duration_input.setText(str(profile["duration_minutes"]))
            self.sets_input.setText(str(profile["num_sets"]))

    def delete_profile_clicked(self):
        current_item = self.profile_list.currentItem()
        if current_item:
            name = current_item.text()
            self.settings_manager.delete_profile(name)
            self.refresh_profile_list()
            self.name_input.clear()
            self.duration_input.clear()
            self.sets_input.clear()

    def _apply_timer_style(self, color: str):
        self.timer_label.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {color};")

    def toggle_pause(self):
        if self.is_running:
            if not self.is_paused:
                self.is_paused = True
                self.pause_button.setText("Resume")
                self._apply_running_style("orange")
            else:
                self.is_paused = False
                self.pause_button.setText("Pause")
                self._apply_timer_style("green")
        
        self.pause_button.setEnabled(self.is_running)

    def _apply_running_style(self, color: str):
        self.timer_label.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {color};")

    def toggle_timer(self):
        if not self.is_running:
            # For prototype, use inputs if available, otherwise 6min/5 sets
            try:
                dur_min = float(self.duration_input.text()) if self.duration_input.text() else 6
                dur_sec = int(dur_min * 60)
                sets = int(self.sets_input.text()) if self.sets_input.text() else 5
            except:
                dur_sec, sets = 60, 5
                
            self._apply_timer_style("black")
            self.total_seconds = dur_sec
            self.num_sets = sets
            self.interval_duration = dur_sec / sets if sets > 0 else 0
            self.current_set = 1
            self.start_time = time.time()
            self.is_running = True
            self.is_paused = False
            
            self.timer.start(100)  # Update every 100ms
            
            self.start_button.setText("Stop")
            self.pause_button.setEnabled(True)
            self.pause_button.setText("Pause")
        else:
            self.stop_timer()
            self.pause_button.setEnabled(False)
            self.pause_button.setText("Pause")

    def stop_timer(self):
        self.timer.stop()
        self.is_running = False
        self.start_button.setText("Start Workout")
        self.pause_button.setEnabled(False)
        self.pause_button.setText("Pause")

    def timer_tick(self):
        if self.is_paused:
            return

        now = time.time()
        elapsed = now - self.start_time
        remaining = max(0, self.total_seconds - elapsed)

        if remaining <= 0:
            self.on_finished()
            return

        progress = (elapsed / self.total_seconds) * 100
        mins, secs = divmod(int(remaining), 60)
        time_str = f"{mins:02d}:{secs:02d}"
        self.update_label(time_str, progress)

        # Check for set transition
        expected_set_start = (self.current_set - 1) * self.interval_duration
        if elapsed >= expected_set_start and self.current_set <= self.num_sets:
            self.on_set_started(self.current_set)
            self.current_set += 1

    def update_label(self, time_str, progress):
        self.timer_label.setText(time_str)
        self.progress_bar.setValue(int(progress))

    def on_set_started(self, set_number):
        self._apply_timer_style("green")
        print(f"Set {set_number} started!")
        if hasattr(self, 'transition_url'):
            self.player.setSource(self.transition_url)
            self.player.play()

    def on_finished(self):
        self.stop_timer()
        self.timer_label.setText("DONE!")
        self.update_label("00:00", 0)
        self._apply_timer_style("red")
        if hasattr(self, 'completion_url'):
            self.player.setSource(self.completion_url)
            self.player.play()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


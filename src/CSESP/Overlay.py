import sys
import win32gui
import win32con
import win32api
import win32com.client
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QCheckBox, QVBoxLayout, QDialog, QPushButton, QColorDialog

from CSESP.ESP import ESP
from CSESP.Offsets import Offsets
from CSESP.Config import Config



class OverlayMenu(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        
        self.checkboxes = {}
        self.color_buttons = {}
        self._setup_ui()


    def _setup_ui(self):
        layout = QVBoxLayout()

        self.state_label = QtWidgets.QLabel("ESP: ON")
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        self.state_label.setFont(QtGui.QFont("Segoe UI", 12, QtGui.QFont.Bold))
        self.state_label.setStyleSheet("color: lime;")
        layout.addWidget(self.state_label)

        for label in ["draw_box", "draw_names", "draw_health", "draw_distance", "draw_skeleton", "draw_head", "draw_lines", "draw_teammates", "draw_bomb"]:
            cb = QCheckBox(label.replace('_', ' ').title())
            cb.setChecked(self.config[label])
            cb.stateChanged.connect(lambda state, key=label: self._on_feature_toggle(key, state))
            self.checkboxes[label] = cb
            layout.addWidget(cb)

        for team, label in [("color_t", "Terrorist Color"), ("color_ct", "Counter Terrorist Color")]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"background-color: {self.config[team].name()}; color: black;")
            btn.clicked.connect(lambda _, key=team, b=btn: self._on_color_picker(key, b))
            self.color_buttons[team] = btn
            layout.addWidget(btn)

        keybind_layout = QtWidgets.QHBoxLayout()
        keybind_layout.addWidget(QtWidgets.QLabel("ESP Toggle:"))
        self.keybind_button = QPushButton(self.config["toggle_keybind"])
        self.keybind_button.clicked.connect(self._on_keybind_select)
        keybind_layout.addWidget(self.keybind_button)
        layout.addLayout(keybind_layout)

        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_to_defaults)
        layout.addWidget(reset_button)

        self.setLayout(layout)


    def set_esp_state(self, enabled: bool):
        if enabled:
            self.state_label.setText("ESP: ON")
            self.state_label.setStyleSheet("color: lime;")
        else:
            self.state_label.setText("ESP: OFF")
            self.state_label.setStyleSheet("color: red;")


    def _on_feature_toggle(self, key, state):
        self.config[key] = bool(state)
        self.config.save()


    def _on_color_picker(self, key, button):
        color = QColorDialog.getColor(initial=self.config[key], parent=self)
        if color.isValid():
            self.config[key] = color
            button.setStyleSheet(f"background-color: {color.name()}; color: black;")
            win32gui.SetForegroundWindow(int(self.winId()))
            self.config.save()


    def _on_keybind_select(self):
        original_text = self.keybind_button.text()
        self.keybind_button.setText("Press any key...")
        
        original_key_press = self.keyPressEvent
        revert_timer = QtCore.QTimer(self)
        revert_timer.setSingleShot(True)
        revert_timer.timeout.connect(lambda: self._revert_keybind_button(original_text, original_key_press))
        revert_timer.start(3000)  # 3 second timeout
        
        def keyPressEvent(event):
            revert_timer.stop()
            key = event.key()
            key_name = QtGui.QKeySequence(key).toString()
            
            if key_name:
                self.config["toggle_keybind"] = key_name
                self.keybind_button.setText(key_name)
                self.config.save()
                self.keyPressEvent = original_key_press
            else:
                self._revert_keybind_button(original_text, original_key_press)
        
        self.keyPressEvent = keyPressEvent


    def _revert_keybind_button(self, original_text, original_key_press):
        self.keybind_button.setText(original_text)
        self.keyPressEvent = original_key_press


    def _reset_to_defaults(self):
        for label in self.checkboxes:
            self.checkboxes[label].setChecked(self.config.default_config[label])
            self.config[label] = self.config.default_config[label]

        for team, button in self.color_buttons.items():
            default_color = self.config._dict_to_qcolor(self.config.default_config[team])
            self.config[team] = default_color
            button.setStyleSheet(f"background-color: {default_color.name()}; color: black;")

        self.config.save()


    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if hasattr(self.parent(), "_toggle_menu"):
                self.parent()._toggle_menu()
            event.accept()
        else:
            super().keyPressEvent(event)



class OverlayRenderer:
    def __init__(self, esp, config, window_size):
        self.esp = esp
        self.config = config
        self.window_size = window_size
        self.scene = QGraphicsScene()


    def update(self):
        """Update the overlay with current entity data"""
        self.scene.clear()
        
        if not self._is_window_focused("Counter-Strike 2"):
            return

        self.esp.update_entities()

        if self.config["draw_bomb"]:
            self._draw_bomb()

        for entity in self.esp.entities:
            if not entity.pos:
                continue
            if entity.lifestate == 258: # I THINK this is the value for spectators
                continue
            if entity.team == self.esp.local_player.team and not self.config["draw_teammates"]:
                continue
            self._draw_entity(entity)


    def _draw_bomb(self):
        """Draw bomb information if planted"""
        try:
            bomb_info = self.esp.get_bomb_info()
            if not bomb_info or not bomb_info["planted"] or bomb_info["is_defused"] or bomb_info["has_exploded"]:
                return  # Don't draw if bomb isn't planted or has been defused or has exploded

            bomb_screen = self._world_to_screen(bomb_info["position"])
            if not bomb_screen:
                return
            if bomb_info["time_remaining"] > 0:
                if bomb_info["being_defused"]:
                    text = f'BOMB {bomb_info["time_remaining"]:.1f}s | DEFUSING {bomb_info["defuse_time_remaining"]:.1f}s'
                else:
                    text = f'BOMB {bomb_info["time_remaining"]:.1f}s'
                
                bomb_text = self.scene.addText(text, QtGui.QFont('Arial', 10, QtGui.QFont.Bold))
                bomb_text.setPos(bomb_screen[0], bomb_screen[1])
                bomb_text.setDefaultTextColor(QtGui.QColor(255, 0, 0))
        except Exception as e:
            print(f"Error drawing bomb: {e}")


    def _draw_entity(self, entity):
        head_pos = self._get_bone_position(entity, 6)
        feet_pos = entity.pos
        if not head_pos or not feet_pos:
            return

        head_screen = self._world_to_screen(head_pos)
        feet_screen = self._world_to_screen(feet_pos)
        if not head_screen or not feet_screen:
            return

        if any(self.config[key] for key in ["draw_box", "draw_health", "draw_names", "draw_distance"]):
            self._draw_player_box(head_screen, feet_screen, entity)

        if self.config["draw_skeleton"] or self.config["draw_head"]:
            self._draw_skeleton(entity)

        if self.config["draw_lines"]:
            self._draw_line_to_entity(feet_screen, entity.team)


    def _draw_player_box(self, head_screen, feet_screen, entity):
        height = feet_screen[1] - head_screen[1]
        width = height / 2
        box_x = feet_screen[0] - width / 2
        box_y = head_screen[1]

        team_color = self.config["color_t"] if entity.team == 2 else self.config["color_ct"]

        if self.config["draw_box"]:
            box = QtWidgets.QGraphicsRectItem(box_x, box_y, width, height)
            box.setPen(QtGui.QPen(team_color, 2))
            self.scene.addItem(box)

        if self.config["draw_health"]:
            self._draw_health_bar(box_x, box_y, height, entity)

        if self.config["draw_names"]:
            self._draw_name(box_x, box_y, width, entity.name)

        if self.config["draw_distance"]:
            dist = self._calculate_distance(self.esp.local_player.pos, entity.pos)
            self._draw_distance(box_x, box_y, width, height, dist)


    def _draw_health_bar(self, x, y, height, entity):
        health_height = height * (entity.health / 100)
        health_color = self._get_health_color(entity.health)
        health_bar = QtWidgets.QGraphicsRectItem(x - 10, y + height - health_height, 3, health_height)
        health_bar.setBrush(QtGui.QBrush(health_color))
        self.scene.addItem(health_bar)

        armor_height = height * (entity.armor / 100)
        armor_bar = QtWidgets.QGraphicsRectItem(x - 6, y + height - armor_height, 3, armor_height)
        armor_bar.setBrush(QtGui.QBrush(QtGui.QColor(0, 150, 255, 180)))
        self.scene.addItem(armor_bar)


    def _draw_name(self, x, y, width, name):
        name_item = self.scene.addText(name, QtGui.QFont('Arial', 8))
        name_item.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        name_item.setPos(x + width / 2 - name_item.boundingRect().width() / 2, y - name_item.boundingRect().height() - 2)


    def _draw_distance(self, x, y, width, height, distance):
        distance_item = self.scene.addText(distance, QtGui.QFont('Arial', 8))
        distance_item.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        distance_item.setPos(x + width / 2 - distance_item.boundingRect().width() / 2, y + height + 2)


    def _draw_line_to_entity(self, feet_screen, team):
        screen_center_x = self.window_size[0] // 2
        screen_bottom_y = self.window_size[1] - 150
        line = QtWidgets.QGraphicsLineItem(screen_center_x, screen_bottom_y, feet_screen[0], feet_screen[1])
        line.setPen(QtGui.QPen(self.config["color_t"] if team == 2 else self.config["color_ct"], 1))
        self.scene.addItem(line)


    def _draw_skeleton(self, entity):
        bone_ids = {
            "head": 6, "neck": 5, "waist": 0,
            "left_shoulder": 13, "right_shoulder": 8,
            "left_arm": 14, "right_arm": 9,
            "left_hand": 16, "right_hand": 11,
            "left_knee": 26, "right_knee": 23,
            "left_foot": 27, "right_foot": 24,
        }

        bone_screen = {}
        for name, index in bone_ids.items():
            bone_pos = self._get_bone_position(entity, index)
            if bone_pos:
                screen = self._world_to_screen(bone_pos)
                if screen:
                    bone_screen[name] = screen

        def draw_line(a, b):
            if a in bone_screen and b in bone_screen:
                line = QtWidgets.QGraphicsLineItem(*bone_screen[a], *bone_screen[b])
                line.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 150), 1))
                self.scene.addItem(line)

        if self.config["draw_skeleton"]:
            connections = [
                ("head", "neck"), ("neck", "waist"),
                ("neck", "left_shoulder"), ("left_shoulder", "left_arm"), ("left_arm", "left_hand"),
                ("neck", "right_shoulder"), ("right_shoulder", "right_arm"), ("right_arm", "right_hand"),
                ("waist", "left_knee"), ("left_knee", "left_foot"),
                ("waist", "right_knee"), ("right_knee", "right_foot")
            ]
            for a, b in connections:
                draw_line(a, b)

        if self.config["draw_head"] and "head" in bone_screen:
            self._draw_head_circle(bone_screen["head"], entity.team == self.esp.local_player.team)


    def _draw_head_circle(self, head_pos, is_teammate):
        x, y = head_pos
        radius = 5
        circle = QtWidgets.QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
        if is_teammate:
            circle.setPen(QtGui.QPen(QtGui.QColor(0, 255, 0), 1.5))
            circle.setBrush(QtGui.QBrush(QtGui.QColor(0, 255, 0, 100)))
        else:
            circle.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 1.5))
            circle.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 100)))
        self.scene.addItem(circle)


    def _get_health_color(self, health):
        """Get color based on health percentage"""
        if health > 75:
            return QtGui.QColor(0, 255, 0, 180)      # Green
        elif health > 50:
            return QtGui.QColor(255, 255, 0, 180)    # Yellow
        elif health > 25:
            return QtGui.QColor(255, 165, 0, 180)    # Orange
        return QtGui.QColor(255, 0, 0, 180)          # Red


    def _get_bone_position(self, entity, bone_index):
        """Get 3D position of a specific bone"""
        try:
            scene_node = self.esp.pm.read_ulonglong(entity.pawn + Offsets.m_pGameSceneNode)
            bone_array = self.esp.pm.read_ulonglong(scene_node + Offsets.m_pBoneArray)
            return tuple(self.esp.pm.read_float(bone_array + bone_index * 32 + i * 4) for i in range(3))
        except Exception:
            return None


    def _world_to_screen(self, pos):
        """Convert 3D world position to 2D screen coordinates"""
        try:
            matrix = [self.esp.pm.read_float(self.esp.client + Offsets.dwViewMatrix + i * 4) for i in range(16)]
            
            x = matrix[0] * pos[0] + matrix[1] * pos[1] + matrix[2] * pos[2] + matrix[3]
            y = matrix[4] * pos[0] + matrix[5] * pos[1] + matrix[6] * pos[2] + matrix[7]
            w = matrix[12] * pos[0] + matrix[13] * pos[1] + matrix[14] * pos[2] + matrix[15]
            
            if w < 0.01:
                return None
                
            inv_w = 1.0 / w
            return (
                self.window_size[0] / 2 * (1 + x * inv_w),
                self.window_size[1] / 2 * (1 - y * inv_w)
            )
        except Exception:
            return None


    def _calculate_distance(self, point1, point2):
        """Returns a string showing the distance between two points"""
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        
        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1
        
        distance = (dx * dx + dy * dy + dz * dz) ** 0.5
        return f"{distance:.0f}m"


    def _is_window_focused(self, title):
        """Check if the specified window is currently focused"""
        hwnd = win32gui.FindWindow(None, title)
        return hwnd and win32gui.GetForegroundWindow() == hwnd



class ESPOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.esp = ESP()
        if not self.esp.initialize():
            sys.exit("[Overlay] Failed to initialize ESP")

        self.window_size = self._get_game_window_size()
        if not self.window_size[0]:
            sys.exit("[Overlay] Could not find CS2 window")

        self.config = Config(Path(__name__).parent / "options.json")
        self.renderer = OverlayRenderer(self.esp, self.config, self.window_size)
        self.menu = OverlayMenu(self.config, self)
        
        self.menu_visible = False
        self.esp_enabled = True
        self._setup_overlay_window()
        self._setup_graphics()
        self._setup_timers()


    def _setup_overlay_window(self):
        self.setGeometry(0, 0, *self.window_size)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE, win32gui.GetWindowLong(self.winId(), win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)


    def _setup_graphics(self):
        self.view = QGraphicsView(self.renderer.scene, self)
        self.view.setGeometry(0, 0, *self.window_size)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.view.setSceneRect(0, 0, *self.window_size)


    def _setup_timers(self):
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self._update_overlay)
        timer.start(16) # ~60 fps

        keybind_timer = QtCore.QTimer(self)
        keybind_timer.timeout.connect(self._check_toggle_keybind)
        keybind_timer.start(100)

        key_timer = QtCore.QTimer(self)
        key_timer.timeout.connect(self._check_insert_key)
        key_timer.start(100)


    def _update_overlay(self):
        if self.esp_enabled:
            self.renderer.update()
        else:
            self.renderer.scene.clear()


    def _check_insert_key(self):
        VK_INSERT = 0x2D
        if win32api.GetAsyncKeyState(VK_INSERT) & 0x8000:
            if self._is_window_focused(title="Counter-Strike 2") or self._is_window_focused(hwnd=int(self.menu.winId())):
                if not hasattr(self, "_insert_pressed") or not self._insert_pressed:
                    self._toggle_menu()
                    self._insert_pressed = True
        else:
            self._insert_pressed = False


    def _check_toggle_keybind(self):
        if not self._is_window_focused(title="Counter-Strike 2"):
            return
        
        key_name = self.config["toggle_keybind"]
        if not key_name:
            return
        
        key_sequence = QtGui.QKeySequence(key_name)
        if key_sequence.isEmpty():
            return
        
        qt_key = key_sequence[0]
        windows_vk = self._qt_key_to_vk(qt_key)
        
        if windows_vk and win32api.GetAsyncKeyState(windows_vk) & 0x8000:
            if not hasattr(self, "_toggle_key_pressed") or not self._toggle_key_pressed:
                self._toggle_key_pressed = True
                self.esp_enabled = not self.esp_enabled
                self.menu.set_esp_state(self.esp_enabled)
        else:
            self._toggle_key_pressed = False


    def _qt_key_to_vk(self, qt_key):
        key = qt_key.key()
        
        # Map Qt key codes to Windows virtual key codes
        # Probably a better way to do this, but...
        # Fuck it, we ball
        if key >= QtCore.Qt.Key_F1 and key <= QtCore.Qt.Key_F24:
            return win32con.VK_F1 + (key - QtCore.Qt.Key_F1)
        elif key == QtCore.Qt.Key_Insert:
            return win32con.VK_INSERT
        elif key == QtCore.Qt.Key_Delete:
            return win32con.VK_DELETE
        elif key == QtCore.Qt.Key_Home:
            return win32con.VK_HOME
        elif key == QtCore.Qt.Key_End:
            return win32con.VK_END
        elif key == QtCore.Qt.Key_PageUp:
            return win32con.VK_PRIOR
        elif key == QtCore.Qt.Key_PageDown:
            return win32con.VK_NEXT
        elif key >= QtCore.Qt.Key_A and key <= QtCore.Qt.Key_Z:
            return ord(chr(key).upper())
        elif key >= QtCore.Qt.Key_0 and key <= QtCore.Qt.Key_9:
            return ord(chr(key))
        
        return None


    def _toggle_menu(self):
        self.menu_visible = not self.menu_visible
        self.menu.setVisible(self.menu_visible)

        ex_style = win32gui.GetWindowLong(self.winId(), win32con.GWL_EXSTYLE)

        if self.menu_visible:
            screen_width = self.window_size[0]
            menu_width = self.menu.width()
            self.menu.move(screen_width - menu_width - 40, 40)
            
            win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE, ex_style & ~win32con.WS_EX_TRANSPARENT)

            # For some reason it'll throw an error unless we
            # Send the ALT key first
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys('%')
            win32gui.SetForegroundWindow(int(self.menu.winId()))

            menu_geom = self.menu.frameGeometry()
            x = menu_geom.left() + menu_geom.width() // 2
            y = menu_geom.top() + menu_geom.height() // 2
            win32api.SetCursorPos((x, y))
        else:
            win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TRANSPARENT)
            hwnd_game = win32gui.FindWindow(None, "Counter-Strike 2")
            if hwnd_game:
                win32gui.SetForegroundWindow(hwnd_game)


    def _get_game_window_size(self):
        """Get the dimensions of the game window"""
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            return (rect[2] - rect[0], rect[3] - rect[1])
        return (None, None)


    def _is_window_focused(self, title=None, hwnd=None):
        """Check if the specified window is currently focused"""
        if title:
            hwnd = win32gui.FindWindow(None, title)
        elif hwnd is None:
            return False
        return hwnd and win32gui.GetForegroundWindow() == hwnd
import sys
import win32gui
import win32con
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView

from CSESP.ESP import ESP
from CSESP.Offsets import Offsets



class ESPOverlay(QtWidgets.QWidget):
    """PyQt overlay window for displaying ESP information"""
    def __init__(self):
        super().__init__()
        self.esp = ESP()
        if not self.esp.initialize():
            sys.exit("[Overlay] Failed to initialize ESP")
            
        self.window_size = self._get_game_window_size()
        if not self.window_size[0]:
            sys.exit("[Overlay] Could not find CS2 window")
            
        self._setup_overlay_window()
        self._setup_graphics()
        self._setup_timer()


    def _setup_overlay_window(self):
        """Configure the overlay window properties"""
        self.setGeometry(0, 0, *self.window_size)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | 
            QtCore.Qt.WindowStaysOnTopHint | 
            QtCore.Qt.Tool
        )
        
        # Make window click-through
        hwnd = self.winId()
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)


    def _setup_graphics(self):
        """Set up the graphics scene for drawing"""
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setGeometry(0, 0, *self.window_size)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.view.setSceneRect(0, 0, *self.window_size)


    def _setup_timer(self):
        """Set up the refresh timer for the overlay"""
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self._update_overlay)
        timer.start(16)  # ~60 FPS


    def _update_overlay(self):
        """Main update loop for the overlay"""
        if not self._is_game_focused():
            self.scene.clear()
            return

        self.scene.clear()
        self.esp.update_entities()
        
        for entity in self.esp.entities:
            if entity.team == self.esp.local_player.team or not entity.pos:
                continue
                
            self._draw_entity(entity)


    def _draw_entity(self, entity):
        """Draw all ESP elements for a single entity"""
        head_pos = self._get_bone_position(entity, 6)  # Head bone index
        feet_pos = entity.pos
        
        if not head_pos or not feet_pos:
            return
            
        head_screen = self._world_to_screen(head_pos)
        feet_screen = self._world_to_screen(feet_pos)
        
        if not head_screen or not feet_screen:
            return
            
        self._draw_player_box(head_screen, feet_screen, entity)
        self._draw_skeleton(entity)


    def _draw_player_box(self, head_screen, feet_screen, entity):
        """Draw the player box with health/armor bars, etc"""
        height = feet_screen[1] - head_screen[1]
        width = height / 2
        box_x = feet_screen[0] - width / 2
        box_y = head_screen[1]
        
        # Draw main box
        team_color = QtGui.QColor(234, 209, 139) if entity.team == 2 else QtGui.QColor(182, 212, 238)
        box = QtWidgets.QGraphicsRectItem(box_x, box_y, width, height)
        box.setPen(QtGui.QPen(team_color, 2))
        self.scene.addItem(box)
        
        # Draw health bar
        health_height = height * (entity.health / 100)
        health_color = self._get_health_color(entity.health)
        health_bar = QtWidgets.QGraphicsRectItem(
            box_x - 10, box_y + height - health_height, 3, health_height
        )
        health_bar.setBrush(QtGui.QBrush(health_color))
        self.scene.addItem(health_bar)
        
        # Draw armor bar
        armor_height = height * (entity.armor / 100)
        armor_bar = QtWidgets.QGraphicsRectItem(
            box_x - 6, box_y + height - armor_height, 3, armor_height
        )
        armor_bar.setBrush(QtGui.QBrush(QtGui.QColor(0, 150, 255, 180)))
        self.scene.addItem(armor_bar)
        
        # Draw player name
        name = self.scene.addText(entity.name, QtGui.QFont('Arial', 8))
        name.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        name.setPos(
            box_x + width / 2 - name.boundingRect().width() / 2,
            box_y - name.boundingRect().height() - 2
        )

        distance = self.scene.addText(self._calculate_distance(self.esp.local_player.pos, entity.pos), QtGui.QFont('Arial', 8))
        distance.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        distance.setPos(
            box_x + width / 2 - distance.boundingRect().width() / 2,
            box_y + height + 2  # 2px below the box
        )


    def _draw_skeleton(self, entity):
        """Draw skeletal lines and a head circle using bone positions"""
        bone_ids = {
            "head": 6,
            "neck": 5,
            "waist": 0,
            "left_shoulder": 13,
            "right_shoulder": 8,
            "left_arm": 14,
            "right_arm": 9,
            "left_hand": 16,
            "right_hand": 11,
            "left_knee": 26,
            "right_knee": 23,
            "left_foot": 27,
            "right_foot": 24,
        }

        # Get bone screen positions
        bone_screen = {}
        for name, index in bone_ids.items():
            bone_pos = self._get_bone_position(entity, index)
            if not bone_pos:
                continue
            screen_pos = self._world_to_screen(bone_pos)
            if screen_pos:
                bone_screen[name] = screen_pos

        # Use team color
        team_color = QtGui.QColor(234, 209, 139) if entity.team == 2 else QtGui.QColor(182, 212, 238)

        def draw_line(p1, p2):
            if p1 in bone_screen and p2 in bone_screen:
                line = QtWidgets.QGraphicsLineItem(
                    bone_screen[p1][0], bone_screen[p1][1],
                    bone_screen[p2][0], bone_screen[p2][1]
                )
                line.setPen(QtGui.QPen(team_color, 1))
                self.scene.addItem(line)

        # Draw skeleton connections
        draw_line("head", "neck")
        draw_line("neck", "waist")

        draw_line("neck", "left_shoulder")
        draw_line("left_shoulder", "left_arm")
        draw_line("left_arm", "left_hand")

        draw_line("neck", "right_shoulder")
        draw_line("right_shoulder", "right_arm")
        draw_line("right_arm", "right_hand")

        draw_line("waist", "left_knee")
        draw_line("left_knee", "left_foot")

        draw_line("waist", "right_knee")
        draw_line("right_knee", "right_foot")

        # Draw head circle
        if "head" in bone_screen:
            head_x, head_y = bone_screen["head"]
            radius = 5  # Size of the head circle
            circle = QtWidgets.QGraphicsEllipseItem(
                head_x - radius, head_y - radius,
                radius * 2, radius * 2
            )
            circle.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 1.5))  # Red outline
            circle.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 100)))  # Semi-transparent fill
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
            matrix = [self.esp.pm.read_float(self.esp.client + Offsets.dwViewMatrix + i * 4) 
                     for i in range(16)]
            
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


    def _get_game_window_size(self):
        """Get the dimensions of the game window"""
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            return (rect[2] - rect[0], rect[3] - rect[1])
        return (None, None)


    def _is_game_focused(self):
        """Check if the game window is currently focused"""
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        return hwnd and win32gui.GetForegroundWindow() == hwnd
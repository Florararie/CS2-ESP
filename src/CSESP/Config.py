import json
from PySide6 import QtGui



class Config:
    def __init__(self, config_path):
        self.config_path = config_path
        self.default_config = {
            "draw_box": True,
            "draw_names": True,
            "draw_health": True,
            "draw_distance": True,
            "draw_skeleton": False,
            "draw_head": False,
            "draw_lines": False,
            "draw_teammates": False,
            "draw_bomb": False,
            "toggle_keybind": "F1",
            "color_t": {"r": 234, "g": 209, "b": 139, "a": 255},
            "color_ct": {"r": 182, "g": 212, "b": 238, "a": 255}
        }
        self.config = self._load_config()
        self._convert_color_configs()


    def _convert_color_configs(self):
        """Convert color dictionaries to QColor objects"""
        self.config["color_t"] = self._dict_to_qcolor(self.config["color_t"])
        self.config["color_ct"] = self._dict_to_qcolor(self.config["color_ct"])


    def _dict_to_qcolor(self, color_dict):
        """Convert dictionary to QColor object"""
        return QtGui.QColor(
            color_dict["r"],
            color_dict["g"],
            color_dict["b"],
            color_dict.get("a", 255)
        )


    def _qcolor_to_dict(self, qcolor):
        """Convert QColor object to dictionary"""
        return {
            "r": qcolor.red(),
            "g": qcolor.green(),
            "b": qcolor.blue(),
            "a": qcolor.alpha()
        }


    def _load_config(self):
        """Load configuration from file or create default if not exists"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    config = self.default_config.copy()
                    config.update(loaded_config)
                    return config
        except Exception as e:
            print(f"[Config] Error loading config: {e}")
        
        return self.default_config.copy()


    def save(self):
        """Save current configuration to file"""
        try:
            save_config = self.config.copy()
            save_config["color_t"] = self._qcolor_to_dict(self.config["color_t"])
            save_config["color_ct"] = self._qcolor_to_dict(self.config["color_ct"])
            
            with open(self.config_path, 'w') as f:
                json.dump(save_config, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")


    def __getitem__(self, key):
        return self.config[key]


    def __setitem__(self, key, value):
        self.config[key] = value
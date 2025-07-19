# CS2-ESP
Just a shoddily written ESP Cheat for CS2 in Python

---

## Features

All options are togglable with the config menu, so you can pick and choose what you'd like


- Box ESP (Customizable color, but by default assigns Blue / Orange to their respective teams - Terrorists and Counter Terrorists)
- Show player names
- Show player health / armor
- Show distance between your current location and each ESP entry
- Outlines player bones for a skeleton ESP
- - Optionally outlines the head bone with a marker for easier aiming (Red for enemies. Green for allies)
- Draw lines to each ESP entry for further visibility
- Show information about the bomb once planted (EG: time left until explosion, as well as realtime defusal status)
- Can draw ESP for teammates as well

## Changelog

### V1.0
Initial Commit

### V1.1
- Migrated from PyQt5 to PySide6
- Made ESP togglable via keybind. Default key is `F1` but this can be changed.
- Created a configuration menu, and thus all features can now be toggled / customized
- - Press INSERT and it will open automatically over the game. No need to tab out. Cursor focus is handled automatically as well
- - Also added a simple JSON configuration system so last chosen options are respected persistently
- ESP Colors can now be customized via a color picker in the configuration menu
- - Colors are bound by team. So terrorists have their own color while counter terrorists have another. Figured this would make it easier to differentiate between allies / foes.
- Can now show information about the C4 once planted
- - Shows location, time left until explosion, defusal status / how much time left until defusal. Makes sure to keep track of explosion and defusal success to avoid any persistence on screen

<div style="display: flex; justify-content: space-between;">
    <img src="/Images/config.png" alt="Configuration Menu" style="height: 800px; width: auto;"/>
    <img src="/Images/ingame.png" alt="In-Game Demonstration" style="height: 800px; width: auto;"/>
</div>

## Usage
Just run while in-game and it will automatically create a click-through overlay to display ESP content as well as a config menu. Press `INSERT` to open.

## Things to note!
~~The overlay window is made using PyQt5- as such, it may occasionally have artifacting. I'm too lazy to fix this, so.. deal with it lol.~~  
PySide6 may still occasionally have artifacting. I havent seen much, been keep that in mind

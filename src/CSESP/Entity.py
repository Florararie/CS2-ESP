from dataclasses import dataclass



@dataclass
class Entity:
    controller: int
    pawn: int
    name: str = "Unknown"
    health: int = 0
    armor: int = 0
    team: int = 0
    pos: tuple = None
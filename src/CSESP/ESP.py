import pymem
import pymem.process

from CSESP.Offsets import Offsets
from CSESP.Entity import Entity



class ESP:
    """Handles game memory reading and entity tracking"""
    def __init__(self):
        self.pm = None
        self.client = None
        self.entities = []
        self.local_player = None


    def initialize(self) -> bool:
        """Initialize memory reader and load game offsets"""
        try:
            self.pm = pymem.Pymem("cs2.exe")
            self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
            Offsets.load()
            return True
        except Exception as e:
            print(f"[ESP Init] Error: {e}")
            return False


    def update_entities(self):
        """Update list of all entities in the game"""
        self.entities.clear()
        
        try:
            # Get local player info
            local_controller = self.pm.read_ulonglong(self.client + Offsets.dwLocalPlayerController)
            local_pawn = self.pm.read_ulonglong(self.client + Offsets.dwLocalPlayerPawn)
            
            if not local_controller or not local_pawn:
                return
                
            self.local_player = Entity(local_controller, local_pawn)
            self.local_player.team = self.pm.read_int(local_pawn + Offsets.m_iTeamNum)
            self.local_player.pos = tuple(self.pm.read_float(local_pawn + Offsets.m_vOldOrigin + i * 4) for i in range(3))
            
            # Process entity list
            entity_list = self.pm.read_ulonglong(self.client + Offsets.dwEntityList)
            if not entity_list:
                return
                
            for i in range(1, 65):  # Max players
                self._process_entity(entity_list, i, local_controller)
                
        except Exception as e:
            print(f"[Entity Update] Error: {e}")


    def _process_entity(self, entity_list, index, local_controller):
        """Process a single entity from the entity list"""
        try:
            list_entry = self.pm.read_ulonglong(entity_list + (8 * (index & 0x7FFF) >> 9) + 16)
            if not list_entry:
                return
                
            controller = self.pm.read_ulonglong(list_entry + 120 * (index & 0x1FF))
            if not controller or controller == local_controller:
                return
                
            # Get pawn information
            pawn_handle = self.pm.read_ulonglong(controller + Offsets.m_hPlayerPawn)
            pawn_entry = self.pm.read_ulonglong(entity_list + (8 * ((pawn_handle & 0x7FFF) >> 9)) + 16)
            pawn = self.pm.read_ulonglong(pawn_entry + 120 * (pawn_handle & 0x1FF))
            
            if not pawn:
                return
                
            # Create and populate entity
            entity = Entity(controller, pawn)
            entity.health = self.pm.read_int(pawn + Offsets.m_iHealth)
            
            if not 0 < entity.health <= 100:
                return
                
            entity.armor = self.pm.read_int(pawn + Offsets.m_ArmorValue)
            entity.team = self.pm.read_int(pawn + Offsets.m_iTeamNum)
            entity.name = self.pm.read_string(controller + Offsets.m_iszPlayerName)
            entity.pos = tuple(self.pm.read_float(pawn + Offsets.m_vOldOrigin + i * 4) for i in range(3))
            
            self.entities.append(entity)
        except Exception:
            pass
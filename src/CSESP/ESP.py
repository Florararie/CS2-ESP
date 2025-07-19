import time
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


    def get_bomb_info(self):
        """Get information about the bomb if planted"""
        try:
            bomb_planted = self.pm.read_bool(self.client + Offsets.dwPlantedC4 - 8)
            
            if not bomb_planted:
                if hasattr(self, '_bomb_planted_time'):
                    del self._bomb_planted_time
                if hasattr(self, '_defuse_start_time'):
                    del self._defuse_start_time
                return None
                
            pre_bomb = self.pm.read_ulonglong(self.client + Offsets.dwPlantedC4)
            bomb_entity = self.pm.read_ulonglong(pre_bomb)
            if not bomb_entity:
                return None
                
            scene_node = self.pm.read_ulonglong(bomb_entity + Offsets.m_pGameSceneNode)
            bomb_pos = (
                self.pm.read_float(scene_node + Offsets.m_vecAbsOrigin),
                self.pm.read_float(scene_node + Offsets.m_vecAbsOrigin + 4),
                self.pm.read_float(scene_node + Offsets.m_vecAbsOrigin + 8)
            )
            
            timer_length = self.pm.read_float(bomb_entity + Offsets.m_flTimerLength)
            being_defused = self.pm.read_bool(bomb_entity + Offsets.m_bBeingDefused)
            defuse_length = self.pm.read_float(bomb_entity + Offsets.m_flDefuseLength)
            is_defused = self.pm.read_bool(bomb_entity + Offsets.m_bBombDefused)
            has_exploded = self.pm.read_bool(bomb_entity + Offsets.m_bHasExploded)
            
            if not hasattr(self, '_bomb_planted_time'):
                self._bomb_planted_time = time.time()
                
            if being_defused:
                if not hasattr(self, '_defuse_start_time'):
                    self._defuse_start_time = time.time()
                    self._initial_defuse_length = defuse_length
            else:
                if hasattr(self, '_defuse_start_time'):
                    del self._defuse_start_time
                    del self._initial_defuse_length
            
            time_remaining = 0 if is_defused else max(0, timer_length - (time.time() - self._bomb_planted_time))
            defuse_time_remaining = 0
            if being_defused and hasattr(self, '_defuse_start_time'):
                elapsed_defuse_time = time.time() - self._defuse_start_time
                defuse_time_remaining = max(0, self._initial_defuse_length - elapsed_defuse_time)
            
            return {
                "planted": True,
                "position": bomb_pos,
                "time_remaining": time_remaining,
                "being_defused": being_defused,
                "defuse_time_remaining": defuse_time_remaining,
                "is_defused": is_defused,
                "has_exploded": has_exploded
            }
        except Exception as e:
            print(f"[Bomb Update] Error: {e}")
            return None


    def update_entities(self):
        """Update list of all entities in the game"""
        self.entities.clear()
        
        try:
            local_controller = self.pm.read_ulonglong(self.client + Offsets.dwLocalPlayerController)
            local_pawn = self.pm.read_ulonglong(self.client + Offsets.dwLocalPlayerPawn)
            
            if not local_controller or not local_pawn:
                return
                
            self.local_player = Entity(local_controller, local_pawn)
            self.local_player.team = self.pm.read_int(local_pawn + Offsets.m_iTeamNum)
            self.local_player.pos = tuple(self.pm.read_float(local_pawn + Offsets.m_vOldOrigin + i * 4) for i in range(3))
            
            entity_list = self.pm.read_ulonglong(self.client + Offsets.dwEntityList)
            if not entity_list:
                return
                
            for i in range(1, 65):
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
            if controller == local_controller:
                return
                
            pawn_handle = self.pm.read_ulonglong(controller + Offsets.m_hPlayerPawn)
            pawn_entry = self.pm.read_ulonglong(entity_list + (8 * ((pawn_handle & 0x7FFF) >> 9)) + 16)
            pawn = self.pm.read_ulonglong(pawn_entry + 120 * (pawn_handle & 0x1FF))
            
            if not pawn:
                return
                
            entity = Entity(controller, pawn)
            entity.health = self.pm.read_int(pawn + Offsets.m_iHealth)
            
            if not 0 < entity.health <= 100:
                return
                
            entity.armor = self.pm.read_int(pawn + Offsets.m_ArmorValue)
            entity.team = self.pm.read_int(pawn + Offsets.m_iTeamNum)
            entity.lifestate = self.pm.read_int(pawn + Offsets.m_lifeState)
            entity.name = self.pm.read_string(controller + Offsets.m_iszPlayerName)
            entity.pos = tuple(self.pm.read_float(pawn + Offsets.m_vOldOrigin + i * 4) for i in range(3))
            
            self.entities.append(entity)
        except Exception:
            pass
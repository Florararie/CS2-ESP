import sys
import requests



class Offsets:
    # Centralized offset storage
    dwEntityList = None
    dwLocalPlayerController = None
    dwLocalPlayerPawn = None
    dwViewMatrix = None
    m_iszPlayerName = None
    m_iHealth = None
    m_ArmorValue = None
    m_iTeamNum = None
    m_vOldOrigin = None
    m_hPlayerPawn = None
    m_pGameSceneNode = None
    m_pBoneArray = None
    m_pClippingWeapon = None


    @classmethod
    def load(cls):
        try:
            offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
            client_dll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()
            
            cls.dwEntityList = offsets["client.dll"]["dwEntityList"]
            cls.dwLocalPlayerController = offsets["client.dll"]["dwLocalPlayerController"]
            cls.dwLocalPlayerPawn = offsets["client.dll"]["dwLocalPlayerPawn"]
            cls.dwViewMatrix = offsets["client.dll"]["dwViewMatrix"]
            
            cls.m_iszPlayerName = client_dll["client.dll"]["classes"]["CBasePlayerController"]["fields"]["m_iszPlayerName"]
            cls.m_iHealth = client_dll["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_iHealth"]
            cls.m_ArmorValue = client_dll["client.dll"]["classes"]["C_CSPlayerPawn"]["fields"]["m_ArmorValue"]
            cls.m_iTeamNum = client_dll["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_iTeamNum"]
            cls.m_vOldOrigin = client_dll["client.dll"]["classes"]["C_BasePlayerPawn"]["fields"]["m_vOldOrigin"]
            cls.m_hPlayerPawn = client_dll["client.dll"]["classes"]["CCSPlayerController"]["fields"]["m_hPlayerPawn"]
            cls.m_pGameSceneNode = client_dll["client.dll"]["classes"]["C_BaseEntity"]["fields"]["m_pGameSceneNode"]
            cls.m_pBoneArray = client_dll["client.dll"]["classes"]["CSkeletonInstance"]["fields"]["m_modelState"] + 128
        except Exception as e:
            print(f"Failed to load offsets: {e}")
            sys.exit(1)
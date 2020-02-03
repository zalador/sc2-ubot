import sc2
from sc2.constants import *

from typing import List, Tuple, Dict


"""
All units are taken from 

https://liquipedia.net/starcraft2/Protoss_Units_(Legacy_of_the_Void)
https://liquipedia.net/starcraft2/Terran_Units_(Legacy_of_the_Void)
https://liquipedia.net/starcraft2/Zerg_Units_(Legacy_of_the_Void)

unsure about versions of game but alas, this has to do
"""

"""
PROTOSS units
"""
PROTOSS_UNITS: Set[UnitTypeId] = {
    PROBE,
    ZEALOT,
    STALKER,
    SENTRY,
    ADEPT,
    HIGHTEMPLAR,
    DARKTEMPLAR,
    IMMORTAL,
    COLOSSUS,
    DISRUPTOR,
    ARCHON,
    OBSERVER,
    WARPPRISM,
    PHOENIX,
    VOIDRAY,
    ORACLE,
    CARRIER,
    TEMPEST,
    MOTHERSHIP
}

PROTOSS_BUILDINGS: Set[UnitTypeId] = {
    NEXUS,
    PYLON,
    ASSIMILATOR,
    GATEWAY,
    FORGE,
    CYBERNETICSCORE,
    PHOTONCANNON,
    SHIELDBATTERY,
    ROBOTICSFACILITY,
    WARPGATE,
    STARGATE,
    TWILIGHTCOUNCIL,
    ROBOTICSBAY,
    FLEETBEACON,
    TEMPLARARCHIVE,
    DARKSHRINE
}

PROTOSS_ALL_UNITS: Set[UnitTypeId] = PROTOSS_UNITS.union(PROTOSS_BUILDINGS)

def get_protoss_unit_map():
    return {x: 0 for x in PROTOSS_ALL_UNITS}

"""
TERRAN units
"""
TERRAN_UNITS: Set[UnitTypeId] = {
    SCV,
    MARINE,
    MARAUDER,
    REAPER,
    GHOST,
    HELLION,
    SIEGETANK,
    CYCLONE,
    WIDOWMINE,
    THOR,
    VIKINGFIGHTER,
    MEDIVAC,
    LIBERATOR,
    RAVEN,
    BANSHEE,
    BATTLECRUISER
}

TERRAN_BUILDINGS: Set[UnitTypeId] = {
    COMMANDCENTER,
    SUPPLYDEPOT,
    REFINERY,
    BARRACKS,
    ENGINEERINGBAY,
    BUNKER,
    SENSORTOWER,
    MISSILETURRET,
    FACTORY,
    GHOSTACADEMY,
    STARPORT,
    ARMORY,
    FUSIONCORE,
    REACTOR, # these are probably important, should be needed
    TECHLAB
}

TERRAN_ALL_UNITS: Set[UnitTypeId] = TERRAN_UNITS.union(TERRAN_BUILDINGS)

def get_terran_unit_map():
    return {x: 0 for x in TERRAN_ALL_UNITS}

"""
ZERG units
"""
ZERG_UNITS: Set[UnitTypeId] = {
    DRONE,
    QUEEN,
    ZERGLING,
    BANELING,
    ROACH,
    RAVAGER,
    HYDRALISK,
    LURKERMP,
    INFESTOR,
    SWARMHOSTMP,
    ULTRALISK,
    OVERLORD,
    #OVERSEER,
    MUTALISK,
    CORRUPTOR,
    BROODLORD,
    VIPER
}

ZERG_BUILDINGS: Set[UnitTypeId] = {
    HATCHERY,
    SPINECRAWLER,
    SPORECRAWLER,
    EXTRACTOR,
    SPAWNINGPOOL,
    EVOLUTIONCHAMBER,
    ROACHWARREN,
    BANELINGNEST,
    LAIR, # these are important but might be difficult to keep track of
    HYDRALISKDEN,
    LURKERDENMP,
    INFESTATIONPIT,
    SPIRE,
    NYDUSNETWORK,
    HIVE, # same as lair
    GREATERSPIRE,
    ULTRALISKCAVERN
}

ZERG_ALL_UNITS: Set[UnitTypeId] = ZERG_UNITS.union(ZERG_BUILDINGS)

def get_zerg_unit_map():
    return {x: 0 for x in ZERG_ALL_UNITS}

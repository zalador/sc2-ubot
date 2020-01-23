import random
from copy import copy, deepcopy

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

from typing import List, Tuple, Dict

from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM
from sc2.dicts.unit_train_build_abilities import TRAIN_INFO
from sc2.dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from sc2.dicts.unit_research_abilities import RESEARCH_INFO

MINERALS_PER_TICK = 36.444 / (60*16) 
VESPENE_PER_TICK = 38.000 / (60*16)

class BusyUnit:
    """
    Units that are building or are being built are a 'BusyUnit'
    """
    def __init__(self, unit_id, ticks_left):
        self.unit_id: UnitTypeId = unit_id
        self.ticks_left: int = ticks_left

    def __lt__(self, other):
        return self.ticks_left < other.ticks_left

class BuildorderState:
    """
    State that is used in our buildorder planner
    Keeps track of resources and resource-gathering rate
    Handles tech-tree building of advanced structures and units
    Abstracts workers to gather at a specific rate: TODO
    """
    
    def __init__(self, minerals, vespene, w_minerals, w_vespene,
                       supply, supply_cap,
                       idle_buildings: Dict[UnitTypeId, int],
                       units: Dict[UnitTypeId, int],
                       busy_units: List[Tuple[UnitTypeId, int]],
                       plan: List[UnitTypeId],
                       bot: sc2.BotAI):
        """
        parameter idle_buildings: number of each specific building we have
        parameter units: number of each specific unit we have
        parameter busy_units: list of (id, time) for units that are not idle (under construction
                               or constructing)
        parameter plan: initial plan, but most often empty
        parameter bot: reference to sc2.BotAI so we can access UnitTypeId tables and what not
        """
        self.minerals: int = minerals
        self.vespene: int = vespene
        self.w_minerals: int = w_minerals
        self.w_vespene: int = w_vespene
        self.supply: int = supply
        self.supply_cap: int = supply_cap
        self.idle_buildings = idle_buildings
        self.units = units
        self.busy_units: List[BusyUnit] = [BusyUnit(unit_id, time) for unit_id, time in busy_units]
        self.plan: List[UnitTypeId] = plan
        self.bot: BotAI = bot        

        self.ticks = 0


    def __str__(self):
        """
        Prints the basic information:
        ticks, resources, workers, supply and plan
        """
        s = "ticks: {}, (m, w_m): ({}, {}), (v, w_v): ({}, {})\n".format(self.ticks, self.minerals,
                self.w_minerals, self.vespene, self.w_vespene)
        s += "(s, s_c): ({}, {}), plan: {}".format(self.supply,
                self.supply_cap, self.ticks, self.plan)
        return s

    def __lt__(self, other):
        """
        We induce a order on the plans through the plan length in ticks
        """
        return self.ticks < other.ticks

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "bot":
                print("Exclude the bot from the deepcopy")
                continue
            setattr(result, k, deepcopy(v, memo))


    #TODO Fix these functions, no sense of looking at unit as builders are the only "when" we can care about on the unit side
    def when_unit_ready(self, unit: UnitTypeId) -> int:
        """
        Returns the number of ticks until a unit is ready
        Returns -1 if no building is found
        """
        START_TIME = 10000
        min_time = START_TIME
        if unit in self.units and self.units[unit] > 0:
            return 0
        for busy_unit in self.busy_units:
            if busy_unit.unit_id == unit:
                min_time = min(min_time, time)

        return min_time if min_time != START_TIME else -1


    def when_building_ready(self, unit: UnitTypeId, only_busy=False) -> int:
        """
        Returns the number of ticks until a building is ready
        Can either be ready directly or when moved from self.busy_units
        Returns -1 if no building is found
        """
        START_TIME = 10000
        min_time = START_TIME
        if not only_busy and unit in self.idle_buildings and self.idle_buildings[unit] > 0:
            # check if we have atleast one idle
            return 0
    
        return self.when_unit_ready(unit)

    def when(self, unit: UnitTypeId) -> int:
        """
        Returns the number of ticks it takes until we can build this unit
        We need to possess tech requirements, resources and supply
        -1 if impossible
        """
        max_time = 0
        cost = self.bot.calculate_cost(unit)
        cost_minerals = cost.minerals
        cost_vespene = cost.vespene
        cost_supply = self.bot.calculate_supply_cost(unit)

        if self.minerals - cost_minerals < 0:
            if self.w_minerals == 0:
                return -1
            diff = cost_minerals - self.minerals
            max_time = max(max_time, diff / (MINERALS_PER_TICK*self.w_minerals))
        print("minerals ok")

        if self.vespene - cost_vespene < 0:
            if self.w_vespene == 0:
                return -1
            diff = cost_vespene - self.vespene
            max_time = max(max_time, diff / (VESPENE_PER_TICK*self.w_vespene))
        print("vespene ok")

        print("cost supply: {}".format(cost_supply))
        if self.supply + cost_supply > self.supply_cap:
            if self.supply_cap > 200: # we cannot build more supply
                return -1
            time = self.when_building_ready(PYLON, only_busy=True) # we require a new pylon
            if time < 0:
                return -1
            max_time = max(max_time, time)
        print("supply ok")

        # check that we can fullfill all tech requirements
        req = unit
        while req in PROTOSS_TECH_REQUIREMENT:
            time = self.when_building_ready(PROTOSS_TECH_REQUIREMENT[unit])
            if time < 0:
                return -1
            max_time = max(max_time, time)
            req = PROTOSS_TECH_REQUIREMENT[unit]
        print("req ok")
    
        creators = list(UNIT_TRAINED_FROM[unit])
        print("creators: " + str(creators))
        print("units: " + str(self.units))
        min_time_creator = 10000
        for creator in creators:
            # handle the probe case seperately
            time = -1
            if creator == PROBE:
                if PROBE in self.units and self.units[PROBE] > 0:
                    min_time_creator = 0
                    break
                # we have no PROBE but perhaps we are building one?
                time = self.when_unit_ready(PROBE)
            else:
                time = self.when_building_ready(unit)
                
            if time < 0:
                return -1
            min_time_creator = min(min_time_creator, time)
        print("creator ok")

        max_time = max(max_time, min_time_creator)
        return max_time

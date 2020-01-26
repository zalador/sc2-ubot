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

    def __repr__(self):
        return "BusyUnit({}, {})".format(self.unit_id, self.ticks_left)

class BuildorderState:
    """
    State that is used in our buildorder planner
    Keeps track of resources and resource-gathering rate
    Handles tech-tree building of advanced structures and units
    Abstracts workers to gather at a specific rate: TODO
    """
    
    def __init__(self, minerals, vespene, w_minerals, w_vespene,
                       supply, supply_cap,
                       units: Dict[UnitTypeId, int],
                       busy_units: List[Tuple[UnitTypeId, int]],
                       plan: List[UnitTypeId],
                       bot: sc2.BotAI):
        """
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
        s += "(s, s_c): ({}, {}), plan: {}\n".format(self.supply,
                self.supply_cap, self.ticks, self.plan)
        s += "busy_units: {}\nunits: {}".format(self.busy_units, self.units)
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


    #def when_unit_ready(self, unit: UnitTypeId) -> int:
    #    """
    #    Returns the number of ticks until a unit is ready
    #    Returns -1 if no building is found
    #    """
    #    START_TIME = 10000
    #    min_time = START_TIME
    #    if unit in self.units and self.units[unit] > 0:
    #        return 0
    #    for busy_unit in self.busy_units:
    #        if busy_unit.unit_id == unit:
    #            min_time = min(min_time, busy_unit.ticks_left)

    #    return min_time if min_time != START_TIME else -1


    def when_unit_ready(self, unit: UnitTypeId, only_busy=False) -> int:
        """
        Returns the number of ticks until a building is ready
        Can either be ready directly or when moved from self.busy_units
        Returns -1 if no building is found
        """
        START_TIME = 10000
        min_time = START_TIME
        if not only_busy and unit in self.units and self.units[unit] > 0:
            # check if we have atleast one idle
            return 0
        for busy_unit in self.busy_units:
            if busy_unit.unit_id == unit:
                min_time = min(min_time, busy_unit.ticks_left)

        return min_time if min_time != START_TIME else -1
    

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
                print("Building unit {} failed due to no mineral workers".format(unit))
                return -1
            diff = cost_minerals - self.minerals
            max_time = max(max_time, diff / (MINERALS_PER_TICK*self.w_minerals))

        if self.vespene - cost_vespene < 0:
            if self.w_vespene == 0:
                print("Building unit {} failed due to no vespene workers".format(unit))
                return -1
            diff = cost_vespene - self.vespene
            max_time = max(max_time, diff / (VESPENE_PER_TICK*self.w_vespene))

        if self.supply + cost_supply > self.supply_cap:
            if self.supply_cap > 200: # we cannot build more supply
                print("Building unit {} failed due to no supply space (>=200)".format(unit))
                return -1
            time = self.when_unit_ready(PYLON, only_busy=True) # we require a new pylon
            if time < 0:
                print("Building unit {} failed due to not having no pylons on the way".format(unit))
                return -1
            max_time = max(max_time, time)

        # check that we can fullfill all tech requirements
        req = unit
        while req in PROTOSS_TECH_REQUIREMENT:
            time = self.when_unit_ready(PROTOSS_TECH_REQUIREMENT[req])
            if time < 0:
                print("Building unit {} failed due to not having tech-req {}".format(unit, PROTOSS_TECH_REQUIREMENT[req]))
                return -1
            max_time = max(max_time, time)
            req = PROTOSS_TECH_REQUIREMENT[req]
    
        creators = list(UNIT_TRAINED_FROM[unit])
        MAX_TIME = 10000
        min_time_creator = MAX_TIME 
        
        # For e.g. gateway units, they can also be constructed from warpgates
        # Here we check for if any creator exists
        for creator in creators:
            # handle the probe case seperately
            time = 10000
            if creator == PROBE:
                if PROBE in self.units and self.units[PROBE] > 0:
                    min_time_creator = 0
                    break
                # we have no PROBE but perhaps we are building one?
                time = self.when_unit_ready(PROBE)
            else:
                time = self.when_unit_ready(creator)
                
            if time < 0: # this particular creator does not exists
                continue
            min_time_creator = min(min_time_creator, time)

        if min_time_creator == MAX_TIME: # no creator exists
            print("Building unit {} failed due to not having creators {}".format(unit, creators))
            return -1

        max_time = max(max_time, min_time_creator)
        return max_time

    def sim(self, ticks, bot):
        """
        Simulates the current BuildorderState 'ticks' forward.
        Adds resources
        Handles busy_units: updates supply if pylon is built, workers working if probe is
        finished, and of course the number of units if something is finished
        """
        self.ticks += ticks

        # update resources
        self.minerals += self.w_minerals * MINERALS_PER_TICK * ticks
        self.vespene += self.w_vespene * VESPENE_PER_TICK * ticks

        new_busy = []
        for i in range(len(self.busy_units)):
            busy_unit = self.busy_units[i].unit_id
            ticks_left = self.busy_units[i].ticks_left
            tick_diff = ticks - ticks_left

            if ticks_left - ticks <= 0:
                if busy_unit == PROBE: # we add new probes to minerals
                    self.w_minerals += 1 # TODO fix max mineral utilization 
                    self.minerals += tick_diff * MINERALS_PER_TICK

                elif busy_unit == ASSIMILATOR: # we always utilize assimilators fully
                    if not ASSIMILATOR in self.units:
                        self.units[ASSIMILATOR] = 1
                    else:
                        self.units[ASSIMILATOR] += 1

                    self.w_minerals = min(0, self.w_minerals-3)
                    self.w_vespene += 3
                    self.minerals -= 3 * tick_diff * MINERALS_PER_TICK
                    self.vespene += 3* tick_diff * VESPENE_PER_TICK

                elif busy_unit == PYLON:
                    if not PYLON in self.units:
                        self.units[PYLON] = 1
                    else:
                        self.units[PYLON] += 1
                    self.supply_cap = min(200, self.supply_cap + 8) 

                else:
                    if not busy_unit in self.units:
                        self.units[busy_unit] = 1
                    else:
                        self.units[busy_unit] += 1

            else: # the unit is still busy
                new_busy.append(BusyUnit(busy_unit, ticks_left - ticks))

        # update the busy_units
        self.busy_units = new_busy


    def build(self, unit: UnitTypeId, bot):
        """
        Updates the state of self when building 'unit'
        Removes resources and adds to busy_units
        Note: assumes that the unit can be built
        """
        cost = bot.calculate_cost(unit)
        cost_minerals = cost.minerals
        cost_vespene = cost.vespene
        build_time = cost.time
        supply_cost = bot.calculate_supply_cost(unit)

        creators = list(UNIT_TRAINED_FROM[unit])
        for creator in creators:
            if creator == PROBE: # the probe needs to move away and build the structure
                self.minerals -= 10

            elif creator in self.units:
                self.units[creator] -= 1
                new_busy_creator = BusyUnit(creator, build_time)
                self.busy_units.append(new_busy_creator)
                break
        
        new_busy_unit = BusyUnit(unit, build_time)
        self.busy_units.append(new_busy_unit)
        self.plan.append(unit)

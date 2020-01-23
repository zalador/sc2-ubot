import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

from typing import List, Tuple, Dict

from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM
from sc2.dicts.unit_train_build_abilities import TRAIN_INFO
from sc2.dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from sc2.dicts.unit_research_abilities import RESEARCH_INFO

from base_manager import BaseManager
from buildorder_state import BuildorderState

class ManagerBuild(BaseManager):
    """
    Class that handles the building units and buildings
    Will handle build orders at some point in the future

    The building is pretty general, the placement is not
    """
    def __init__(self):
        """
        We keep a linear list of stuff to build
        To handle research ids, a more general list is needed, perhaps a isinstance can work
        """
        self.build_queue: List[UnitTypeId] = [PROBE, PROBE, PYLON, PROBE, PROBE, GATEWAY, PROBE, PYLON, PROBE, PROBE, GATEWAY, PROBE, ASSIMILATOR, PYLON, ZEALOT, PROBE, CYBERNETICSCORE, ZEALOT, ZEALOT, ZEALOT, ZEALOT, ZEALOT, PYLON, ZEALOT, ZEALOT, PYLON, STALKER, STALKER, STALKER, ZEALOT]

    async def build_unit(self, bot : sc2.BotAI, unit_id : UnitTypeId) -> bool:
        """
        Tries to build a unit with id: unit_id
        returns True if successfull

        Currently does not handle complex buildings (warpgates, assimilators, nexuses)
        """
        if not bot.can_afford(unit_id):
            return False

        build_req = self.build_info(unit_id)
        for from_id, build_dict in build_req:
            # we handle structures and probes seperately
            requires_power = ("requires_power" in build_dict)
            pylon = bot.structures(PYLON).ready.random_or(None)
            nexus = bot.structures(NEXUS).random

            if requires_power and not pylon:
                return False

          
            if from_id == PROBE:
                # Here we need a big switch case for all different buildings
                if unit_id == ASSIMILATOR:
                    for th in bot.townhalls.ready:
                        # Find all vespene geysers that are closer than range 10 to this townhall
                        # Can currently only build at townhalls that are ready, consider fixing this
                        vgs = bot.vespene_geyser.closer_than(10, th)
                        for vg in vgs:
                            if await bot.can_place(ASSIMILATOR , vg.position): 
                                workers = bot.workers.gathering
                                if workers:  # same condition as above
                                    worker = workers.closest_to(vg)
                                    # Caution: the target for the refinery has to be
                                    # the vespene geyser, not its position!
                                    bot.do(worker.build(unit_id, vg), subtract_cost=True)
                                    bot.do(worker.stop(queue=True))
                                    return True
                    
                elif unit_id == NEXUS:
                    pass

                else:
                    await bot.build(unit_id, near=pylon if requires_power else nexus)                

            else: # it is a structure that builds it, perhaps this needs to be generalized so that we can handle Archons and so on
                if from_id == WARPGATE:
                    # we need to handle this seperately
                    continue
                building = bot.structures(from_id).ready.idle.random_or(None)
                if not building:
                    # no building is ready, if we have no such building then we need replan
                    return False
                                
                bot.do(building.train(unit_id), subtract_cost=True, subtract_supply=True)

        return True


    def build_info(self, unit_id : UnitTypeId) -> List[Tuple[UnitTypeId, Dict]]:
        """
        Returns a list of pairs: [UnitTypeId, {"ability" : AbilityId, constraints}] 
        that specify what builds the unit and with what ability
        The constraints specify 'requires_position' and 'requires_power' etc
        """
        # all units that can build the one we are looking for
        built_from = list(UNIT_TRAINED_FROM[unit_id])
        # all abilities that build what we are looking for
        ids = [TRAIN_INFO[unit][unit_id] for unit in built_from]
        return list(zip(built_from, ids))
    
    def test(self, bot):
        minerals = bot.minerals
        vespene = bot.vespene
        w_minerals = 12 # fix this
        w_vespene = 0
        supply = bot.supply_used
        supply_cap = bot.supply_cap
        
        idle_buildings = {}
        for structure in bot.structures.filter(lambda s: s.is_idle and s.is_ready):
            if structure in idle_buildings:
                idle_buildings[structure.type_id] += 1
            else:
                idle_buildings[structure.type_id] = 1

        units = {}
        for unit in bot.units:
            if unit in units:
                units[unit.type_id] += 1
            else:
                units[unit.type_id] = 1

        busy_units = []
        for structure in bot.structures.filter(lambda s: not s.is_idle):
            busy_units.append((structure.type_id, 50)) # fix this

        plan = []
        
        bo_state = BuildorderState(minerals, vespene,
                        w_minerals, w_vespene,
                        supply, supply_cap,
                        idle_buildings,
                        units,
                        busy_units,
                        plan,
                        bot)
        print(bo_state)

        #print("TEST PYLON")
        #test_pylon = bo_state.when(PYLON)
        #print("time: {}\n".format(test_pylon))
        print("TEST PROBE")
        test_probe = bo_state.when(PROBE)
        print("time: {}\n".format(test_probe))
        #print("TEST ZEALOT")
        #test_zealot = bo_state.when(ZEALOT)

        
        #print("tests: \n pylon: {} \n probe: {} \n zealot: {}".format(test_pylon, test_probe, test_zealot))


    async def on_step(self, bot: sc2.BotAI, iteration):
        self.test(bot)
        if len(self.build_queue) == 0:
            return

        if not bot.townhalls.ready:
            for worker in bot.workers:
                bot.do(worker.attack(self.enemy_start_locations[0]))
            return
        else:
            nexus = bot.townhalls.ready.random
        
        build_unit = self.build_queue[0]
        if await self.build_unit(bot, build_unit):
            del self.build_queue[0]


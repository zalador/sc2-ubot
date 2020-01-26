import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.unit import Unit

from typing import List, Tuple, Dict

from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM
from sc2.dicts.unit_train_build_abilities import TRAIN_INFO
from sc2.dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from sc2.dicts.unit_research_abilities import RESEARCH_INFO

from base_manager import BaseManager

class ManagerResources(BaseManager):
    """
    Class that handles resource gathering
    Need to be general in the sense that new nexuses need to be utilized and
    assimilators need to be filled when built

    Probably need functions such as:
    listen_for_assimilator_built - kinda works
    balance_probes (potentially based on needes)
    listen_for_probe_built to assign for best patch - kinda works
    workers_working, (minerals, gas) 
    maybe select_worker functions
    handle multiple nexuses
    """
    def __init__(self):
        pass

    def workers_working(self, bot: sc2.BotAI) -> Tuple[int, int]:
        bases = bot.townhalls.ready
        gas_buildings = bot.gas_buildings.ready

        minerals = 0
        gas = 0
        for mining_place in bases | gas_buildings:
            if mining_place.has_vespene:
                gas += mining_place.assigned_harvesters
            else:
                minerals += mining_place.assigned_harvesters

        return (minerals, gas)

    def assign_closest_mineral(self, bot: sc2.BotAI, unit: Unit) -> bool:
        """
        Assigns unit to the closest mineral field that is not utilized
        """
        bases = bot.townhalls.ready.sorted_by_distance_to(unit.position)
        for mining_place in bases:
            if mining_place.surplus_harvesters < 0:
                local_minerals = {
                    mineral for mineral \
                        in bot.mineral_field if mineral.distance_to(mining_place) <= 8
                }
                target_mineral = max(local_minerals, key=lambda mineral: mineral.mineral_contents, default=None)
                bot.do(unit.gather(target_mineral))
                return True
        return False

    def assign_closest_gas(self, bot: sc2.BotAI, unit: Unit):
        gas_buildings = bot.gas_buildings.ready.sorted_by_distance_to(unit.position)
        
        for mining_place in gas_buildings:
            if mining_place.has_vespene and mining_place.surplus_harvesters < 0:
                bot.do(unit.gather(mining_place))
                return True
        return False

    def assign_probe(self, bot: sc2.BotAI, unit: Unit, prio_gas: bool):
        """
        Assigns the unit (PROBE) to either the closes gas or mineral patch depending
        on prio_gas
        """
        if prio_gas:
            if not self.assign_closest_gas(bot, unit) and not self.assign_closest_mineral(bot, unit):
                closest_mineral = bot.mineral_field.closest_to(unit)
                bot.do(unit.gather(closest_mineral))

        else:
            if not self.assign_closest_mineral(bot, unit) and not self.assign_closest_gas(bot, unit):
                closest_mineral = bot.mineral_field.closest_to(unit)
                bot.do(unit.gather(closest_mineral))

    def is_base_full(self, bot: sc2.BotAI, base: Unit) -> bool:
        """
        Returns True if all 'numbers' are full over a nexus and its assimilators
        """
        # find the assimilators close to this base
        assimilators = bot.structures(ASSIMILATOR).closer_than(8, base.position).filter(lambda assimilator: assimilator.has_vespene)
        count = sum(map(lambda assimilator: assimilator.assigned_harvesters, assimilators))
        count += base.assigned_harvesters
        return count >= (base.ideal_harvesters + 3*assimilators.amount)

    def is_all_bases_full(self, bot: sc2.BotAI) -> bool:
        """
        Returns True if all 'numbers' are full over all nexus and all assimilators
        """
        for th in bot.townhalls:
            if not self.is_base_full(bot, th):
                return False
        return True

    async def on_step(self, bot: sc2.BotAI, iteration):
        # assign idle workers to closest
        w = self.workers_working(bot)
        
        idle = bot.workers.idle
        for worker in idle:
            self.assign_probe(bot, worker, bot.gas_focus)

        # every n:th iteration, rebalance
        if iteration % 10*16:
            await bot.distribute_workers()


    async def on_unit_created(self, bot: sc2.BotAI, unit: Unit):
        if unit.type_id == PROBE:
            self.assign_probe(bot, unit, bot.gas_focus)


    async def on_building_construction_complete(self, bot: sc2.BotAI, unit: Unit):
        unit_id: UnitTypeId = unit.type_id
        if unit_id == ASSIMILATOR:
            diff = -unit.surplus_harvesters
            if diff < 0:
                print("ASSIMILATOR WHEN BUILT HAS 4 OR MORE ASSIGNED ALREADY")
            # add three workers to it
            local_minerals_tags = {
                mineral.tag for mineral in bot.mineral_field if mineral.distance_to(unit.position) <= 8
            }
            n_closest_workers = bot.workers.filter(lambda worker: worker.order_target in local_minerals_tags or worker.is_carrying_minerals).n_closest_to_distance(unit.position, 20, diff)
            if n_closest_workers == None:
                # no workers close to the new built assimilator, do nothing
                pass
            for worker in n_closest_workers:
                bot.do(worker.gather(unit))

        elif unit_id == NEXUS:
            # do stuff here also
            pass

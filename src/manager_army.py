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


ARMY_UNITS = [ZEALOT, STALKER, IMMORTAL]

class ManagerArmy(BaseManager):
    """
    At the start, handle all army units in a big blob
    Mikro comes at a later stage

    What is needed:
    list of all units - yes, but now List[Unit], perhaps Units is better
    on_unit_created to add to list - easy
    on_unit_destroyed to remove from list - harder as it uses unit_tag
    movement of blob - currently only attack
    simple attack - attacks when squad reaches 5 units
    """



    def __init__(self):
        self.army: List[Unit] = []
        self.squads: List[List[Unit]] = []
        self.state = "DEFENCE"
        self.squad_size = 5
        pass

    async def on_step(self, bot: sc2.BotAI, iteration):
        ramp_pos = bot.main_base_ramp.protoss_wall_warpin
        if self.state == "DEFENCE":
            if len(self.army) >= self.squad_size:
                self.squads.append(self.army.copy())
                self.army.clear()
            for unit in self.army:
                bot.do(unit.attack(ramp_pos))
            
        # select all enemy units, filter out invis units
        targets = (bot.enemy_units | bot.enemy_structures).filter(lambda unit: unit.can_be_attacked)
        for squad in self.squads:
            for unit in squad:
                if targets:
                    target = targets.closest_to(unit)
                    bot.do(unit.attack(target))
                else:
                    bot.do(unit.attack(bot.enemy_start_locations[0]))


    async def on_unit_created(self, bot: sc2.BotAI, unit: Unit):
        if unit.type_id in ARMY_UNITS:
            self.army.append(unit)

    async def on_unit_destroyed(self, bot: sc2.BotAI, unit_tag: int):
        for unit in self.army:
            if unit.tag == unit_tag:
                self.army.remove(unit)
                
        
        remove = False
        for squad in self.squads:
            for unit in squad:
                if unit.tag == unit_tag:
                    squad.remove(unit)
                    if len(squad) == 0:
                        remove = True
                        break
            if remove:
                self.squads.remove(squad)

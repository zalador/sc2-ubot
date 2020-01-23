import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

from base_manager import BaseManager
import manager_build
import manager_resources
import manager_army

class UBot(sc2.BotAI):
    def __init__(self):
        # Initialize inherited class
        sc2.BotAI.__init__(self)
        
        # apperantly we are running 8 frames per on_step
        # this should be settable through some sort of
        # self._client.game_step = 

        self.managers: List[BaseManager] = []
        self.gas_focus = True

        self.managers.append(manager_build.ManagerBuild())
        self.managers.append(manager_resources.ManagerResources())
        self.managers.append(manager_army.ManagerArmy())
        
    async def on_step(self, iteration):
        print("Current iteration: " + str(iteration))
        for manager in self.managers:
            await manager.on_step(self, iteration)


    async def on_building_construction_complete(self, unit):
        for manager in self.managers:
            await manager.on_building_construction_complete(self, unit)

    async def on_unit_created(self, unit):
        for manager in self.managers:
            await manager.on_unit_created(self, unit)

    async def on_unit_destroyed(self, unit_tag):
        for manager in self.managers:
            await manager.on_unit_destroyed(self, unit_tag)
        pass

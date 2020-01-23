from abc import ABC, abstractmethod

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

class BaseManager(ABC):

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    async def on_step(self, bot: sc2.BotAI, iteration):
        pass

    async def on_building_construction_complete(self, bot: sc2.BotAI, unit):
        pass

    async def on_unit_created(self, bot: sc2.BotAI, unit):
        pass

    async def on_unit_destroyed(self, bot: sc2.BotAI, unit_tag: int):
        pass

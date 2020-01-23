import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

from ubot import UBot


def main():

    sc2.run_game(
        sc2.maps.get("CatalystLE"),
        [Bot(Race.Protoss, UBot()), Computer(Race.Protoss, Difficulty.Easy)],
        realtime=False,
    )


if __name__ == "__main__":
    main()

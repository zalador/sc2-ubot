import random
from queue import PriorityQueue 
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
        #self.build_queue: List[UnitTypeId] = [PROBE, PROBE, PYLON, PROBE, ASSIMILATOR, GATEWAY, PROBE, PYLON, PROBE, PROBE, CYBERNETICSCORE, PROBE, STALKER]
        self.build_queue = []

    async def build_unit(self, bot : sc2.BotAI, unit_id : UnitTypeId) -> bool:
        """
        Tries to build a unit with id: unit_id
        returns True if successfull

        Currently does not handle complex buildings (warpgates, nexuses)
        """
        if not bot.can_afford(unit_id): # only tests
            return False

        build_req = self.build_info(unit_id)
        for from_id, build_dict in build_req:
            # we handle structures and probes seperately
            requires_power = "requires_power" in build_dict
            pylon = bot.structures(PYLON).ready.random_or(None)
            nexus = bot.structures(NEXUS).random

            if requires_power and not pylon:
                return False

            if "required_building" in build_dict and not \
                    bot.structures(build_dict["required_building"]).ready.amount >= 1:
                return False

            if from_id == PROBE:
                # Here we need a big switch case for all unique buildings
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
                    return True
                    

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

        return False


    def build_info(self, unit_id : UnitTypeId) -> List[Tuple[UnitTypeId, Dict]]:
        """
        Returns a list of pairs: [UnitTypeId, {"ability" : AbilityId, constraints}] 
        that specify what builds the unit and with what ability
        The constraints specify 'requires_position' and 'requires_power'
        'required_building' might be a list of buildings, should probably check this
        """
        # all units that can build the one we are looking for
        built_from = list(UNIT_TRAINED_FROM[unit_id])
        # all abilities that build what we are looking for
        ids = [TRAIN_INFO[unit][unit_id] for unit in built_from]
        return list(zip(built_from, ids))
    
    def get_buildorder_state(self, bot):
        """
        Creates a BuildorderState from the current game state

        Records resources and supply
        The state of all structures is recorded as well as the number of units
        """
        minerals = bot.minerals
        vespene = bot.vespene
        
        w_minerals, w_vespene = bot.m_resources.workers_working(bot)
        supply = bot.supply_used
        supply_cap = bot.supply_cap
        
        units = {}
        busy_units = []

        for structure in bot.structures:
            if structure.build_progress < 1:
                cost = bot.calculate_cost(structure.type_id)
                build_time_left = (1-structure.build_progress)*cost.time
                busy_units.append((structure.type_id, build_time_left))

            elif structure.is_idle:
                if not structure.type_id in units:
                    units[structure.type_id] = 1
                else:
                    units[structure.type_id] += 1


            elif structure.is_using_ability:
                order = structure.orders[0] # we can never have more than one in queue
                order_id = order.ability
                progress = order.progress
                cost_time = bot.calculate_cost(order_id).time

                # apparently difficult to get the UnitTypeId from AbilityId in a nice way, might wanna create our own dict for that
                # however, we can just disregard this as of now
                #TODO add unit being created to busy_units
                busy_units.append((structure.type_id, (1-progress) * cost_time))
            else:
                # this "should" not happen xd
                print("ERROR, PLEASE LOOK FOR THIS IN MANAGER_BUILD")

        for unit in bot.units:
            if not unit.type_id in units:
                units[unit.type_id] = 1
            else:
                units[unit.type_id] += 1

        plan = [] #TODO consider if a initial plan is required
        return BuildorderState(minerals, vespene, w_minerals, w_vespene, supply, supply_cap,
                        units, busy_units, plan, bot)
        

    def get_distance_to_goal(self, goal: Dict[UnitTypeId, int], state: BuildorderState):
        dis = 0
        for unit_id, amount in goal.items():
            state_amount = state.get_number_of_unit(unit_id)
            dis += (amount-state_amount)**2
        return dis


    def calculate_buildorder(self, goal: Dict[UnitTypeId, int], bot) -> List[UnitTypeId]:
        current_bo_state = self.get_buildorder_state(bot)

        best_plan: List[UnitTypeId] = []
        best_plan_ticks: int = 100000000
        
        states = PriorityQueue()
        iteration_major = 0
        iteration_expand = 0

        orders = [PROBE, PYLON]
        states.put(current_bo_state)

        # create a upper bound on units that are to be built
        bounds = copy(current_bo_state.units)
        max_supply = 0
        
        # add all requirements that will be needed to reach the goal
        for unit_id, amount in goal.items():
            if not unit_id in bounds:
                bounds[unit_id] = amount
            else:
                bounds[unit_id] = max(bounds[unit_id], amount)

            creators = list(UNIT_TRAINED_FROM[unit_id])
            for creator in creators:
                if creator == WARPGATE:
                    continue
                if not creator in orders:
                    orders.append(creator)

                if not creator in bounds:
                    bounds[creator] = amount
                else:
                    bounds[creator] = max(bounds[creator], amount)

            req = unit_id # TODO this is also used in buildorder_state, fix this
            while req not in orders:
                orders.append(req)
                if not req in bounds:
                    bounds[req] = 1
                else:
                    bounds[req] = max(bounds[req], 1)

                # if a requirement requires vespene, we add that to the orders
                if bot.calculate_cost(req).vespene > 0:
                    if not ASSIMILATOR in orders:
                        orders.append(ASSIMILATOR)

                if req in PROTOSS_TECH_REQUIREMENT:
                    req = PROTOSS_TECH_REQUIREMENT[req]
                else:
                    break
            
            max_supply += bot.calculate_supply_cost(req) * amount


        # special case bounds
        if NEXUS in goal:
            bounds[NEXUS] = goal[NEXUS]
        else:
            bounds[NEXUS] = current_bo_state.get_number_of_unit(NEXUS)
        bounds[PYLON] = max(bounds[PYLON], (max_supply+4-15) // 8) # round the number of pylons up
        if ASSIMILATOR in goal:
            bounds[ASSIMILATOR] = goals[ASSIMILATOR]
        else:
            bounds[ASSIMILATOR] = bounds[NEXUS] * 2 if ASSIMILATOR in orders else 0
        
        bounds[CYBERNETICSCORE] = 1
        bounds[TWILIGHTCOUNCIL] = 1
        bounds[DARKSHRINE] = 1
        bounds[TEMPLARARCHIVE] = 1
        bounds[ROBOTICSBAY] = 1
        bounds[FLEETBEACON] = 1

        print("To build: {} \nthe following orders are required: {}".format(goal, orders))
        print("Bounds: {}".format(bounds))

        max_iteration_major = 500
        while not states.empty() and iteration_major < max_iteration_major:
            iteration_major += 1
            cur = states.get()

            print("Current expand iteration: {} and plan: {}".format(iteration_major, cur))
            # check if we fullfill goal
            units_left = {}
            for unit_id, amount in goal.items():
                cur_amount = cur.get_number_of_unit(unit_id)
                if cur_amount < amount:
                    units_left[unit_id] = amount - cur_amount

            if not units_left:
                #print("Found a goal")
                # all goals fullfilled
                if cur.ticks < best_plan_ticks:
                    best_plan = cur.plan
                    best_plan_ticks = cur.ticks
                    #print(" the plan was better: {}\n".format(cur.plan))
                    continue

            if cur.ticks > best_plan_ticks:
                print()
                continue

            # go through all orders
            for order in orders:
                iteration_expand += 1

                if cur.get_number_of_unit(order) + 1 > bounds[order]:
                    continue

                # TODO we need some way of limiting what order we issue
                # in kill_kurt, there was a upper_bound map
                ticks_until = cur.when(order)
                if ticks_until < 0:
                    continue

                #print(" adding {} to plan".format(order))
                # add the new state
                new_state = deepcopy(cur)
                new_state.sim(ticks_until, bot)
                new_state.build(order, bot)
                
                heuristic = self.get_distance_to_goal(goal, new_state)
                new_state.heuristic = heuristic
                states.put(new_state)

            print()
            
        # at this point, we have a best plan hopefully
        print("major iterations: {}, minor iterations: {}, ticks: {}, seconds: {}, ".format(iteration_major, iteration_expand, best_plan_ticks, best_plan_ticks/22.4))
        print("best_plan: {}".format(best_plan))
        return best_plan
        
    async def on_step(self, bot: sc2.BotAI, iteration):
        #cur = self.get_buildorder_state(bot)
        # add the new state
        #new_state = deepcopy(cur)
        #new_state.sim(100, bot)
        #new_state.build(PROBE, bot)

        #print("cur busy_units: {}, new_state busy_units: {}".format(cur.busy_units, new_state.busy_units))

        #new_state.sim(500, bot)

        # healthy checks
        #print("cur workers: ({}, {}), cur resources: ({}, {}), cur ticks: {}".format(cur.w_minerals, cur.w_vespene, cur.minerals, cur.vespene, cur.ticks))
        #print("new_state workers: ({}, {}), new_state resources: ({}, {}), new_state ticks: {}".format(new_state.w_minerals, new_state.w_vespene, new_state.minerals, new_state.vespene, new_state.ticks))
        
        #print("cur units: {}, new_state units: {}".format(cur.units, new_state.units))
        
        if iteration == 1:
            goal = {PROBE: 20, PYLON: 1, ZEALOT: 4}#, GATEWAY: 1, STALKER: 1}
            plan = self.calculate_buildorder(goal, bot)
            print("Calculated plan: {}".format(plan))
            self.build_queue = plan
            assert(1==2)


        if len(self.build_queue) == 0:
            return

        if not bot.townhalls.ready:
            for worker in bot.workers:
                bot.do(worker.attack(self.enemy_start_locations[0]))
            return
        else:
            nexus = bot.townhalls.ready.random
        
        build_unit = self.build_queue[0]
        current_bo_state = self.get_buildorder_state(bot)
        time = current_bo_state.when(build_unit)
        print("Current build order: {}".format(self.build_queue))
        print("Current BuildorderState: {}".format(current_bo_state))
        print("Current build: {} in ({}, {}) (ticks, seconds)".format(
            build_unit, time, time/(22.4)))
        print()
        if await self.build_unit(bot, build_unit):
            del self.build_queue[0]


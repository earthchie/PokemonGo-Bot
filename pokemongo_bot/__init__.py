# -*- coding: utf-8 -*-

import logging
import googlemaps
import json
import random
import threading
import datetime
import sys
import yaml
import logger
import time
from pgoapi import PGoApi
from cell_workers import PokemonCatchWorker, SeenFortWorker
from cell_workers.utils import distance
from human_behaviour import sleep
from stepper import Stepper
from geopy.geocoders import GoogleV3
from math import radians, sqrt, sin, cos, atan2
from item_list import Item


class PokemonGoBot(object):
    def __init__(self, config):
        self.config = config
        self.pokemon_list = json.load(open('data/pokemon.json'))
        self.item_list = json.load(open('data/items.json'))

    def start(self):
        self._setup_logging()
        self._setup_api()
        self.stepper = Stepper(self)
        random.seed()

    def take_step(self):
        self.stepper.take_step()

    def work_on_cell(self, cell, position, include_fort_on_path):
        self.check_session(position)
        process_ignore = False
        try:
            with open("./data/catch-ignore.yml", 'r') as y:
                ignores = yaml.load(y)['ignore']
                if len(ignores) > 0:
                    process_ignore = True
        except Exception, e:
            pass

        if process_ignore:
            #
            # remove any wild pokemon
            try:
                for p in cell['wild_pokemons'][:]:
                    pokemon_id = p['pokemon_data']['pokemon_id']
                    pokemon_name = filter(
                        lambda x: int(x.get('Number')) == pokemon_id,
                        self.pokemon_list)[0]['Name']

                    if pokemon_name in ignores:
                        cell['wild_pokemons'].remove(p)
            except KeyError:
                pass

            #
            # remove catchable pokemon
            try:
                for p in cell['catchable_pokemons'][:]:
                    pokemon_id = p['pokemon_id']
                    pokemon_name = filter(
                        lambda x: int(x.get('Number')) == pokemon_id,
                        self.pokemon_list)[0]['Name']

                    if pokemon_name in ignores:
                        cell['catchable_pokemons'].remove(p)
            except KeyError:
                pass

        if (self.config.mode == "all" or self.config.mode ==
                "poke") and 'catchable_pokemons' in cell and len(cell[
                    'catchable_pokemons']) > 0:
            logger.log('[#] Something rustles nearby!')
            # Sort all by distance from current pos- eventually this should
            # build graph & A* it
            cell['catchable_pokemons'].sort(
                key=
                lambda x: distance(self.position[0], self.position[1], x['latitude'], x['longitude']))
            for pokemon in cell['catchable_pokemons']:
                with open('web/catchable-%s.json' %
                          (self.config.username), 'w') as outfile:
                    json.dump(pokemon, outfile)
                worker = PokemonCatchWorker(pokemon, self)
                if worker.work() == -1:
                    break
                with open('web/catchable-%s.json' %
                          (self.config.username), 'w') as outfile:
                    json.dump({}, outfile)
        if (self.config.mode == "all" or self.config.mode == "poke"
            ) and 'wild_pokemons' in cell and len(cell['wild_pokemons']) > 0:
            # Sort all by distance from current pos- eventually this should
            # build graph & A* it
            cell['wild_pokemons'].sort(
                key=
                lambda x: distance(self.position[0], self.position[1], x['latitude'], x['longitude']))
            for pokemon in cell['wild_pokemons']:
                worker = PokemonCatchWorker(pokemon, self)
                if worker.work() == -1:
                    break
        if (self.config.mode == "all" or
                self.config.mode == "farm") and include_fort_on_path:
            if 'forts' in cell:
                # Only include those with a lat/long
                forts = [fort
                         for fort in cell['forts']
                         if 'latitude' in fort and 'type' in fort]

                # Sort all by distance from current pos- eventually this should
                # build graph & A* it
                forts.sort(key=lambda x: distance(self.position[
                           0], self.position[1], x['latitude'], x['longitude']))
                for fort in cell['forts']:
                    worker = SeenFortWorker(fort, self)
                    hack_chain = worker.work()
                    if hack_chain > 10:
                        #print('need a rest')
                        break

    def _setup_logging(self):
        self.log = logging.getLogger(__name__)
        # log settings
        # log format
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')

        if self.config.debug:
            logging.getLogger("requests").setLevel(logging.DEBUG)
            logging.getLogger("pgoapi").setLevel(logging.DEBUG)
            logging.getLogger("rpc_api").setLevel(logging.DEBUG)
        else:
            logging.getLogger("requests").setLevel(logging.ERROR)
            logging.getLogger("pgoapi").setLevel(logging.ERROR)
            logging.getLogger("rpc_api").setLevel(logging.ERROR)

    def _setup_api(self):
        # instantiate pgoapi
        self.api = PGoApi()
        # provide player position on the earth

        self._set_starting_position()

        self.login()

        # chain subrequests (methods) into one RPC call

        # get player profile call
        # ----------------------
        self.api.get_player()

        response_dict = self.api.call()
        #print('Response dictionary: \n\r{}'.format(json.dumps(response_dict, indent=2)))
        currency_1 = "0"
        currency_2 = "0"

        player = response_dict['responses']['GET_PLAYER']['player_data']

        # @@@ TODO: Convert this to d/m/Y H:M:S
        creation_date = datetime.datetime.fromtimestamp(
            player['creation_timestamp_ms'] / 1e3)

        pokecoins = '0'
        stardust = '0'

        if 'amount' in player['currencies'][0]:
            pokecoins = player['currencies'][0]['amount']
        if 'amount' in player['currencies'][1]:
            stardust = player['currencies'][1]['amount']

        logger.log('[#]')
        logger.log('[#] Username: {username}'.format(**player))
        logger.log('[#] Acccount Creation: {}'.format(creation_date))
        logger.log('[#] Bag Storage: {}/{}'.format(
            self.get_inventory_count('item'), player['max_item_storage']))
        logger.log('[#] Pokemon Storage: {}/{}'.format(
            self.get_inventory_count('pokemon'), player[
                'max_pokemon_storage']))
        logger.log('[#] Stardust: {}'.format(stardust))
        logger.log('[#] Pokecoins: {}'.format(pokecoins))
        logger.log('[#] PokeBalls: ' + str(self.item_inventory_count(1)))
        logger.log('[#] GreatBalls: ' + str(self.item_inventory_count(2)))
        logger.log('[#] UltraBalls: ' + str(self.item_inventory_count(3)))
        logger.log('[#] Razz Berry: ' + str(self.item_inventory_count(701)))

        # Testing
        # self.drop_item(Item.ITEM_POTION.value,1)
        # exit(0)
        self.get_player_info()

        if self.config.initial_transfer:
            self.initial_transfer()

        logger.log('[#]')
        self.update_inventory()

    def drop_item(self, item_id, count):
        self.api.recycle_inventory_item(item_id=item_id, count=count)
        return self.api.call()

    def check_session(self, position):
        # Check session expiry
        if self.api._auth_provider and self.api._auth_provider._ticket_expire:
            remaining_time = self.api._auth_provider._ticket_expire/1000 - time.time()

            if remaining_time < 60:
                logger.log("Session stale, re-logging in", 'yellow')
                self.position = position
                self.login()

    def login(self):
        logger.log('[#] Attempting login to Pokemon Go.', 'white')
        self.api._auth_token = None
        self.api._auth_provider = None
        self.api._api_endpoint = None
        self.api.set_position(*self.position)
        
        while not self.api.login(self.config.auth_service,str(self.config.username),str(self.config.password)):
            logger.log('[X] Login Error, server busy', 'red')
            logger.log('[X] Waiting 10 seconds to try again', 'red')
            time.sleep(10)
        
        logger.log('[+] Login to Pokemon Go successful.', 'green')

    def initial_transfer(self):
        logger.log('[x] Initial Transfer.')

        if self.config.cp:
            logger.log('[x] Will NOT transfer anything above CP {}'.format(
                self.config.cp))
        else:
            logger.log(
                '[x] Preparing to transfer all Pokemon duplicates, keeping the highest CP of each one type.')

        pokemon_groups = self._initial_transfer_get_groups()

        for id in pokemon_groups:

            group_cp = pokemon_groups[id].keys()
            if len(group_cp) > 1:
                group_cp.sort()
                group_cp.reverse()

                for x in range(1, len(group_cp)):
                    if self.config.cp and group_cp[x] > self.config.cp:
                        continue

                    print('[x] Transferring {} with CP {}'.format(
                        self.pokemon_list[id - 1]['Name'], group_cp[x]))
                    self.api.release_pokemon(
                        pokemon_id=pokemon_groups[id][group_cp[x]])
                    response_dict = self.api.call()
                    sleep(2)

        logger.log('[x] Transferring Done.')

    def _initial_transfer_get_groups(self):
        pokemon_groups = {}
        self.api.get_player().get_inventory()
        inventory_req = self.api.call()
        inventory_dict = inventory_req['responses']['GET_INVENTORY'][
            'inventory_delta']['inventory_items']
        with open('web/inventory-%s.json' %
                  (self.config.username), 'w') as outfile:
            json.dump(inventory_dict, outfile)

        for pokemon in inventory_dict:
            try:
                reduce(dict.__getitem__, [
                    "inventory_item_data", "pokemon_data", "pokemon_id"
                ], pokemon)
            except KeyError:
                continue

            group_id = pokemon['inventory_item_data'][
                'pokemon_data']['pokemon_id']
            group_pokemon = pokemon['inventory_item_data'][
                'pokemon_data']['id']
            group_pokemon_cp = pokemon[
                'inventory_item_data']['pokemon_data']['cp']

            if group_id not in pokemon_groups:
                pokemon_groups[group_id] = {}

            pokemon_groups[group_id].update({group_pokemon_cp: group_pokemon})
        return pokemon_groups

    def update_inventory(self):
        self.api.get_inventory()
        response = self.api.call()
        self.inventory = list()
        if 'responses' in response:
            if 'GET_INVENTORY' in response['responses']:
                if 'inventory_delta' in response['responses']['GET_INVENTORY']:
                    if 'inventory_items' in response['responses'][
                            'GET_INVENTORY']['inventory_delta']:
                        for item in response['responses']['GET_INVENTORY'][
                                'inventory_delta']['inventory_items']:
                            if not 'inventory_item_data' in item:
                                continue
                            if not 'item' in item['inventory_item_data']:
                                continue
                            if not 'item_id' in item['inventory_item_data'][
                                    'item']:
                                continue
                            if not 'count' in item['inventory_item_data'][
                                    'item']:
                                continue
                            self.inventory.append(item['inventory_item_data'][
                                'item'])

    def pokeball_inventory(self):
        balls_stock = {
            1: self.item_inventory_count(1), 
            2: self.item_inventory_count(2), 
            3: self.item_inventory_count(3), 
            4: self.item_inventory_count(4)
        }
        return balls_stock

    def _set_starting_position(self):

        if self.config.test:
            return

        if self.config.location_cache:
            try:
                #
                # save location flag used to pull the last known location from
                # the location.json
                with open('data/last-location-%s.json' %
                          (self.config.username)) as f:
                    location_json = json.load(f)

                    self.position = (location_json['lat'],
                                     location_json['lng'], 0.0)
                    self.api.set_position(*self.position)

                    logger.log('')
                    logger.log(
                        '[x] Last location flag used. Overriding passed in location')
                    logger.log(
                        '[x] Last in-game location was set as: {}'.format(
                            self.position))
                    logger.log('')

                    return
            except:
                if not self.config.location:
                    sys.exit(
                        "No cached Location. Please specify initial location.")
                else:
                    pass

        #
        # this will fail if the location.json isn't there or not valid.
        # Still runs if location is set.
        self.position = self._get_pos_by_name(self.config.location)
        self.api.set_position(*self.position)
        logger.log('')
        logger.log(u'[x] Address found: {}'.format(self.config.location.decode(
            'utf-8')))
        logger.log('[x] Position in-game set as: {}'.format(self.position))
        logger.log('')
    
    def item_inventory_count(self, id):
        self.api.get_player().get_inventory()

        inventory_req = self.api.call()
        inventory_dict = inventory_req['responses'][
            'GET_INVENTORY']['inventory_delta']['inventory_items']

        item_count = 0

        for item in inventory_dict:
            try:
                if item['inventory_item_data']['item']['item_id'] == int(id):
                    item_count = item[
                        'inventory_item_data']['item']['count']
            except:
                continue
        return item_count

    def _get_pos_by_name(self, location_name):
        geolocator = GoogleV3(api_key=self.config.gmapkey)
        loc = geolocator.geocode(location_name, timeout=10)

        #self.log.info('Your given location: %s', loc.address.encode('utf-8'))
        #self.log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)

        return (loc.latitude, loc.longitude, loc.altitude)

    def heartbeat(self):
        self.api.get_player()
        self.api.get_hatched_eggs()
        self.api.get_inventory()
        self.api.check_awarded_badges()
        self.api.call()

    def get_inventory_count(self, what):
        self.api.get_inventory()
        response_dict = self.api.call()
        if 'responses' in response_dict:
            if 'GET_INVENTORY' in response_dict['responses']:
                if 'inventory_delta' in response_dict['responses'][
                        'GET_INVENTORY']:
                    if 'inventory_items' in response_dict['responses'][
                            'GET_INVENTORY']['inventory_delta']:
                        pokecount = 0
                        itemcount = 1
                        for item in response_dict['responses'][
                                'GET_INVENTORY']['inventory_delta'][
                                    'inventory_items']:
                            #print('item {}'.format(item))
                            if 'inventory_item_data' in item:
                                if 'pokemon_data' in item[
                                        'inventory_item_data']:
                                    pokecount = pokecount + 1
                                if 'item' in item['inventory_item_data']:
                                    if 'count' in item['inventory_item_data'][
                                            'item']:
                                        itemcount = itemcount + \
                                            item['inventory_item_data'][
                                                'item']['count']
        if 'pokemon' in what:
            return pokecount
        if 'item' in what:
            return itemcount
        return '0'

    def get_player_info(self):
        self.api.get_inventory()
        response_dict = self.api.call()
        if 'responses' in response_dict:
            if 'GET_INVENTORY' in response_dict['responses']:
                if 'inventory_delta' in response_dict['responses'][
                        'GET_INVENTORY']:
                    if 'inventory_items' in response_dict['responses'][
                            'GET_INVENTORY']['inventory_delta']:
                        pokecount = 0
                        itemcount = 1
                        for item in response_dict['responses'][
                                'GET_INVENTORY']['inventory_delta'][
                                    'inventory_items']:
                            #print('item {}'.format(item))
                            if 'inventory_item_data' in item:
                                if 'player_stats' in item[
                                        'inventory_item_data']:
                                    playerdata = item['inventory_item_data'][
                                        'player_stats']

                                    nextlvlxp = (
                                        int(playerdata['next_level_xp']) -
                                        int(playerdata['experience']))

                                    if 'level' in playerdata:
                                        logger.log(
                                            '[#] -- Level: {level}'.format(
                                                **playerdata))

                                    if 'experience' in playerdata:
                                        logger.log(
                                            '[#] -- Experience: {experience}'.format(
                                                **playerdata))
                                        logger.log(
                                            '[#] -- Experience until next level: {}'.format(
                                                nextlvlxp))

                                    if 'pokemons_captured' in playerdata:
                                        logger.log(
                                            '[#] -- Pokemon Captured: {pokemons_captured}'.format(
                                                **playerdata))

                                    if 'poke_stop_visits' in playerdata:
                                        logger.log(
                                            '[#] -- Pokestops Visited: {poke_stop_visits}'.format(
                                                **playerdata))

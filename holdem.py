import argparse
import threading
import xmlrpc.client
import sys
import time
import random

from deuces.deuces import Card, Deck, Evaluator
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

BLIND_INCREMENTS = [[10,25],[25,50],[50,100],[100,200]]

def card_parse(card_int):
    try:
        card_rank = card_int % 13
        card_suit = int(card_int/13)
    except TypeError:
        print('Trying to parse a card, was expecting Integer instead got:', type(card_int))
    return card_dict[card_rank]+suit_dict[card_suit]

class Table(object):
    def __init__(self, host, port, seats = 8, blinds = True, sb = 10, bb = 25):
        self._smallblind = sb
        self._bigblind = bb
        self._deck = Deck()
        self._evaluator = Evaluator()


        self.community = []
        self._round = 0
        self._button = 0
        self._discard = []
        self._side_pots = [0]*seats
        self._totalpot = 0
        self._current_pot = 0
        self._tocall = 0
        self._lastraise = 0
        self._last_move = None
        self._number_of_games = 0

        self._seats = [Player(-1,-1,0,"empty",0,True) for _ in range(seats)]
        self._player_dict = {}


        self._lock = threading.Lock()
        self._run_thread = threading.Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def player_bet(self, player, bet_size):
        temp_betsize = min(player.stack, bet_size)
        self._totalpot += temp_betsize - player.currentbet
        player.bet(temp_betsize)

        self._tocall = max(self._tocall, temp_betsize)
        self._lastraise = max(self._lastraise, temp_betsize  - self._lastraise)

    def resolve_sidepots(self, players_playing):
        players = [p for p in players_playing if p.currentbet != 0]
        print('current bets: ', [p.currentbet for p in players])
        if players == []:
            self._current_pot -= 1
            return
        smallest_bet = min([p.currentbet for p in players])
        self._side_pots[self._current_pot] += smallest_bet*len(players)
        for p in players:
            p.currentbet -= smallest_bet
            if p.currentbet == 0:
                p.lastsidepot = self._current_pot
        if len(players) == 1:
            players[0].refund(players[0].currentbet)
            return
        else:
            self._current_pot += 1
            self.resolve_sidepots([p for p in players if p.currentbet >0])
        # self._totalpot = sum(self._side_pots)
        print('current sidepots: ', self._side_pots)

    def run(self):
        while True:
            players = [player for player in self._seats if not player.emptyplayer]
            # print("So far ", [player.playerID for player in players], " players have joined the game.")
            # answer = input("Would you like to start?")
            # if answer[0] == 'y':
            #     self.start_game()
            # else:
            #     time.sleep(1)

            # quickstart when 2 players have joined the table
            # print(len(players))
            if len(players) == 8:
                # answer = input("Would you like to start?")
                # if not answer:
                self.start_game()
                self._number_of_games += 1
                if (self._number_of_games % 15) == 0 and self._number_of_games < 60:
                    self._smallblind = BLIND_INCREMENTS[int(self._number_of_games/15)][0]
                    self._bigblind = BLIND_INCREMENTS[int(self._number_of_games/15)][1]

            else:
                time.sleep(1)

    def start_game(self):
        with self._lock:
            players = [player for player in self._seats if player.playing_hand]
            print("players", [(p.playerID, p.stack) for p in players])
            if sum([p.stack for p in players]) != 2000*len([p for p in self._seats if not p.emptyplayer]):
                raise ValueError('stacks are not adding up')
            self.new_round()
            self._round=0

            player = self._first_to_act(players)

            self.post_smallblind(player)
            player = self._next(players, player)
            self.post_bigblind(player)
            player = self._next(players, player)

            self._tocall = self._bigblind

            # rounds
            self._round = 0
            while self._round<4 and len(players)>1:
                if self._round == 0:
                    # deal phase
                    print("Dealing")
                    self.deal()
                elif self._round == 1:
                    # floph phase
                    print("Flop")
                    self.flop()
                elif self._round == 2:
                    # turn phase
                    print("Turn")
                    self.turn()
                elif self._round ==3:
                    # river phase
                    print("River")
                    self.river()

                done_players = []
                while not player.playedthisround:
                    if player.isallin:
                        player = self._next(players, player)
                        continue
                    move = player.server.player_move(self.output_state(player))
                    print("Player ", player.playerID, "decides to ",  move)
                    self._last_move = move


                    if move[0] == 'call':
                        self.player_bet(player, self._tocall)
                        player = self._next(players, player)
                    elif move[0] == 'check':
                        self.player_bet(player, player.currentbet)
                        player = self._next(players, player)
                    elif move[0] == 'raise':
                        self.player_bet(player, move[1])
                        for p in players:
                            if p != player:
                                p.playedthisround = False
                        player = self._next(players, player)
                    elif move[0] == 'fold':
                        folded_player = player
                        player = self._next(players, player)
                        players.remove(folded_player)
                        done_players.append(folded_player)
                        # break if a single player left
                        if len(players) ==1:
                            break
                    if player.isallin:
                        done_players.append(player)

                print('potsize:', self._totalpot)
                if len(players) ==1:
                    break

                player = self._first_to_act(players)
                self.resolve_sidepots(players + done_players)
                self.new_round()

            self.resolve_game(players)
            self.reset()

    def post_smallblind(self, player):
        self.player_bet(player, self._smallblind)
        player.playedthisround = False

    def post_bigblind(self, player):
        self.player_bet(player, self._bigblind)
        player.playedthisround = False
        self._lastraise = self._bigblind

    def _first_to_act(self, players):
        if self._round == 0 and len(players) == 2:
            return self._seats[self._button]
        try:
            first = [player for player in players if player.get_seat() > self._button][0]
        except IndexError:
            first = players[0]
        return first

    def _next(self, players, current_player):
        return players[(players.index(current_player)+1) % len(players)]

    def resolve_game(self, players):
        if len(players)==1:
            print("player ", players[0].playerID, " wins the pot (", self._totalpot, ")")
            players[0].refund(self._totalpot)
            self._totalpot = 0
        else:
            # compute hand ranks
            for player in players:
                player.handrank = self._evaluator.evaluate(player.hand, self.community)

            # trim side_pots to only include the non-empty side pots
            temp_pots = [pot for pot in self._side_pots if pot>0]

            # compute who wins each side pot and pay winners
            for pot_idx in range(len([pot for pot in self._side_pots if pot>0])):
                # find players involved given side_pot, compute the winner(s)
                pot_contributors = [player for player in players if player.lastsidepot >= pot_idx]
                max_rank = min([player.handrank for player in pot_contributors])
                max_idx = [i for i, j in enumerate([player.handrank for player in pot_contributors]) if j == max_rank]

                # pay the winner(s) of side_pot[pot_idx]
                for i in max_idx:
                    print("winner(s) of sidepot ", pot_idx, " are players ", [player.playerID for player in pot_contributors if player.handrank == max_rank], " they win/split a total of ", self._side_pots[pot_idx])

                    pot_contributors[i].refund(int(self._side_pots[pot_idx]/len(max_idx)))
                    self._side_pots[pot_idx] -= int(self._side_pots[pot_idx]/len(max_idx))

                # any remaining chips after splitting go to the winner in the earliest position
                earliest = self._first_to_act([player for player in pot_contributors if player.handrank == max_rank])
                earliest.refund(self._side_pots[pot_idx])

    def deal(self):
        for player in self._seats:
            if player.playing_hand:
                player.hand = self._deck.draw(2)

    def new_round(self):
        for player in self._player_dict.values():
            player.currentbet = 0
            player.playedthisround = False
        self._round += 1
        self._tocall = 0
        self._lastraise = 0

    def flop(self):
        self._discard.append(self._deck.draw(1)) #burn
        self.community = self._deck.draw(3)

    def turn(self):
        self._discard.append(self._deck.draw(1)) #burn
        self.community.append(self._deck.draw(1))

    def river(self):
        self._discard.append(self._deck.draw(1)) #burn
        self.community.append(self._deck.draw(1))

    def add_player(self, host, port, playerID, name, stack, seat = 'any'):
        if (playerID not in self._player_dict):
            new_player = Player(host, port, playerID, name, stack)
            new_player.playing_hand = True # default to have new players start playing
            try:
                if self._seats[seat].emptyplayer:
                    self._seats[seat] = new_player
                    new_player.set_seat(seat)
            except:
                for i,player in enumerate(self._seats):
                    if player.emptyplayer:
                        self._seats[i] = new_player
                        new_player.set_seat(i)
                        break

            self._player_dict[playerID] = new_player

    def remove_player(self, playerID):
        try:
            if playerID in self._player_dict:
                self._seats.remove(self._player_dict[playerID])
                del self._player_dict[playerID]
        except ValueError:
            pass

    def reset(self):
        for player in self._seats:
            if not player.emptyplayer:
                player.reset_hand()
        self._current_pot = 0
        self._totalpot = 0
        self._side_pots = [0]*len(self._seats)
        self._deck.shuffle()
        self._button = (self._button + 1) % len(self._seats)
        while not self._seats[self._button].playing_hand:
            self._button = (self._button + 1) % len(self._seats)

    def output_state(self, current_player):
        return {'players':[player.player_state() for player in self._seats],
        'community':self.community,
        'my_seat':current_player.get_seat(),
        'pocket_cards':current_player.hand,
        'pot':self._totalpot,
        'button':self._button,
        'tocall':(self._tocall-current_player.currentbet),
        'stack':current_player.stack,
        'bigblind':self._bigblind,
        'playerID':current_player.playerID,
        'lastraise':self._lastraise}

class Player(object):
    def __init__(self, host, port, playerID, name, stack, emptyplayer = False):
        self._host = host
        self._port = port
        self.playerID = playerID
        self._name = name

        self.hand = []
        self.stack = stack
        self.currentbet = 0
        self.lastsidepot = 0

        # are all of these necessary?
        self.emptyplayer = emptyplayer
        self.betting = False
        self.isallin = False
        self.playing_hand = False
        self.playedthisround = False
        self._seat = -1

        self._address = "http://%s:%s" % (host, port)
        self.server = xmlrpc.client.ServerProxy(self._address)
        self.handrank = 0

    def get_seat(self):
        return self._seat

    def set_seat(self, value):
        self._seat = value

    def reset_hand(self):
        self._hand=[]
        self.playedthisround = False
        self.betting = False
        self.isallin = False
        self.currentbet = 0
        self.lastsidepot = 0
        if self.stack == 0:
            self.playing_hand = False

    def bet(self, bet_size):
        self.playedthisround = True
        if bet_size == 0:
            return
        self.stack -= (bet_size - self.currentbet)
        self.currentbet = bet_size
        if self.stack == 0:
            print('player', self.playerID, 'is all in with ', self.currentbet)
            self.isallin = True

    def refund(self, ammount):
        self.stack += ammount

    def player_state(self):
        return (self.get_seat(), self.stack, self.playing_hand, self.betting)

class TableProxy(object):
    def __init__(self, table):
        self._table = table
    def get_table_state(self, playerID):
        # print("inside get_table_state in tableproxy")
        return self._table.output_state(table._player_dict.get(playerID, None))

    def add_player(self, playerID, name, stack, host, port):
        self._table.add_player(playerID, name, stack, host, port)

    def start_game(self):
        self._table.start_game()

    # def player_move(self, playerID, result):

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument("num_players", type=int, default=1)
    # parser.add_argument("host", type=str, default="localhost")
    # parser.add_argument("port", type=str, default="8000")
    # args = parser.parse_args()

    print("Welcome to the Texas Holdem table, how many seats would you like at this table? (default=8)")
    # default_yesno = input("default configuration? (y/n) ")
    default_yesno = 'y'
    if default_yesno[0] == 'y':
        table = Table("0.0.0.0", 8000)
    else:
        seats = input("Number of seats: ")

        print("Would you like to play with blinds or antes? (default=blinds)")
        print("1) Blinds")
        print("2) Antes")
        blind_or_ante = input("Choose your option: ")
        if blind_or_ante == 1:
            blinds = True
            print("How large should the small-blind/big-blind be? (default = 10/25)")
            print("1) 10/25")
            print("2) 25/50")
            print("3) 50/100")
            print("4) 100/200")
            blind_size = input("Choose your option: ")
            if blind_size == 1:
                sb = 10
                bb = 25
            elif blind_size == 2:
                sb = 25
                bb = 50
            elif blind_size == 3:
                sb = 50
                bb = 100
            elif blind_size == 4:
                sb = 100
                bb = 200
            else:
                print("Invalid input, defaulting to 10/25 blinds.")
                sb = 10
                bb = 25
        elif blind_or_ante == 2:
            blinds = False
            print("How big should the antes be? (default=50)")
            print("1) 10")
            print("2) 25")
            print("3) 50")
            print("4) 100")
            ante_size = input("Choose your option: ")
            if ante_size == 1:
                ante_ammount = 10
            elif ante_size == 2:
                ante_ammount = 25
            elif ante_size == 3:
                ante_ammount = 50
            elif ante_size == 4:
                ante_ammount = 100
            else:
                print("Invalid option, defaulting to ante size = 50")
                ante_ammount = 50
        else:
            print("Invalid input, defaulting to 10/25 blinds.")
            blinds = True
            sb = 10
            bb = 25

        try:
            table = Table(seats, blinds, sb, bb, args.host, args.port)
        except TypeError:
            table = Table(blinds, sb, bb, args.host, args.port)

    table_proxy = TableProxy(table)

    server = SimpleXMLRPCServer(("localhost", 8000), logRequests=False, allow_none=True)
    server.register_instance(table_proxy, allow_dotted_names=True)

    # table.start()
    # table.join()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

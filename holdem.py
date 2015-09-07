import argparse
import threading
import xmlrpc.client
import sys
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
import time
import random

card_dict = {0:'2', 1:'3', 2:'4', 3:'5', 4:'6', 5:'7', 6:'8', 7:'9', 8:'J', 9:'Q', 10:'K', 11:'A'}
suit_dict = {0:'c', 1:'d', 2:'h', 3:'s'}


def card_parse(card_int):
    try:
        card_rank = card_int % 13
        card_suit = int(card_int/13)
    except TypeError:
        print('Trying to parse a card, was expecting Integer instead got:', type(card_int))
    return card_dict[card_rank]+suit_dict[card_suit]

class Table(object):
    def __init__(self, host, port, seats = 8, blinds = True, sb = 10, bb = 25):
        # super(Table, self).__init__()
        self._smallblind = sb
        self._bigblind = bb
        self._deck = list(range(52))

        self._round = 0
        self._button = 0
        self._discard = []
        self._community = []
        self._side_pots = [0]*(seats-1)
        self._totalpot = 0
        self._current_pot = 0
        self._tocall = 0

        self._seats = [Player(-1,-1,0,"empty",0,True) for _ in range(seats)]
        # self._seats = [None]*seats
        self._player_dict = {}

        self._lock = threading.Lock()
        self._run_thread = threading.Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def player_bet(self, player, bet_size):
        player.bet(min(player.stack, bet_size))
        self._tocall = min(player.stack, bet_size)
        self._totalpot = sum(self._side_pots)

    def resolve_sidepots(self, players_playing):
        smallest_bet = min([player.currentbet for player in players_playing])
        self._side_pots[self._current_pot] += smallest_bet*len(players_playing)
        for player in players_playing:
            player.currentbet -= smallest_bet
        if len(players_playing) == 1:
            player.refund(player.currentbet)
        elif min([player.currentbet for player in players_playing]) != 0:
            for player in players_playing:
                if player.currentbet == 0:
                    player.lastsidepot = self._current_pot
            self._current_pot += self._current_pot
            self.resolve_sidepots(self, [player for player in players_playing if player.currentbet >0])
        self._totalpot = sum(self._side_pots)

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
            if len(players) == 3:
                self.start_game()
            else:
                time.sleep(1)

    def start_game(self):
        with self._lock:
            players_playing = [player for player in self._seats if player.playing_hand]
            print("players_playing:", [player.playerID for player in players_playing])

            self.new_round()
            self._round=0

            while len(players_playing)>1:
                current_player = self._first_to_act(players_playing)

                # small blind
                self.player_bet(players_playing[current_player], self._smallblind)
                current_player = (current_player + 1) % len(players_playing)

                # big blind
                self.player_bet(players_playing[current_player], self._bigblind)
                current_player = (current_player + 1) % len(players_playing)

                # # small blind
                # if self._smallblind> players_playing[current_player].stack:
                #     self._pot += players_playing[current_player].stack
                #     players_playing[current_player].isallin = True
                #     players_playing[current_player].bet(players_playing[current_player].stack)
                # else:
                #     players_playing[current_player].bet(self._smallblind)
                #     self._pot += self._smallblind
                # print("posted small blind, pot size:", self._pot)
                # current_player = (current_player + 1) % len(players_playing)
                #
                # # big blind
                # if self._bigblind> players_playing[current_player].stack:
                #     self._pot += players_playing[current_player].stack
                #     players_playing[current_player].bet(players_playing[current_player].stack)
                # else:
                #     players_playing[current_player].bet(self._bigblind)
                #     self._pot += self._bigblind
                # print("posted big blind, pot size:", self._pot)
                # current_player = (current_player + 1) % len(players_playing)

                self._tocall = self._bigblind
                # rounds
                self._round = 0
                while self._round<4:
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


                    while not players_playing[current_player].playedthisround:
                        # if current players is all in, skip their turn and go to the next player
                        if players_playing[current_player].isallin:
                            current_player = (current_player + 1) % len(players_playing)
                            continue

                        # send player board state and ask for their response
                        state = self.output_state(players_playing[current_player])
                        move = players_playing[current_player].server.player_move(state)

                        print("Player ", players_playing[current_player].playerID, "decides to ",  move)

                        if move[0] in ['call', 'raise', 'check']:
                            self.player_bet(players_playing[current_player], move[1])
                            #if raise occurered, everybody else must respond
                            if move[0] == 'raise':
                                for player in players_playing:
                                    if player != players_playing[current_player]:
                                        player.playedthisround = False
                                self._tocall = move[1]
                            current_player = (current_player + 1) % len(players_playing)
                        elif move[0] == 'fold':
                            players_playing.pop(current_player)
                            current_player = current_player % len(players_playing)

                    # re-evaluate first to act before starting next round
                    current_player = self._first_to_act(players_playing)

                    #break if a single player left
                    if len(players_playing)==1:
                        break

                    self.resolve_sidepots(players_playing)
                    self.new_round()

                # resolve the game and move the button
                self.resolve_game(players_playing)
                self._move_button()

    def _move_button(self):
        self._button = self._button + 1 % len(self._seats)
        while self._seats[self._button].emptyplayer:
            self._button = self._button + 1 % len(self._seats)

    # make this more pythonic
    def _first_to_act(self, players_playing):
        # special rule: if heads-up play the button plays first pre-flop
        if self._round == 0 and len(players_playing) == 2:
            return players_playing.index(self._seats[self._button])

        # otherwise the first person to the left of the button acts
        try:
            first = [player.get_seat() for player in players_playing if (player.get_seat() > self._button)][0]
        except IndexError:
            first = [player.get_seat() for player in players_playing][0]
        return players_playing.index(self._seats[first])

    def resolve_game(self, players_playing):
        if len(players_playing)==1:
            print("player ", players_playing[0].playerID, " wins the pot (", self._totalpot, ")")
            players_playing[0].refund(self._totalpot)
            self._totalpot = 0
        else:
            # remaining rounds should already be played out, these 6 lines should be ok to remove
            if self._round==0:
                self.flop()
            if self._round==1:
                self.turn()
            if self._round==2:
                self.river()

            # compute hand ranks
            for player in players_playing:
                player.handrank = evalHand(player.pocket_cards + self._community)

            # trim side_pots to only include the non-empty side pots
            temp_pots = [pot for pot in self._side_pots if pot>0]

            # compute who wins each side pot and pay winners
            for pot_idx in range(len(self._side_pots)):
                # find players involved given side_pot, compute the winner(s)
                pot_contributors = [player for player in players_playing if player.lastsidepot >= pot_idx]
                max_rank = max([player.handrank for player in pot_contributors])
                max_idx = [i for i, j in enumerate([player.handrank for player in pot_contributors]) if j == max_rank]

                # pay the winner(s) of side_pot[pot_idx]
                for i in max_idx:
                    print("winner(s) of sidepot ", pot_idx, " are players ", [player.playerID for player in pot_contributors if player.handrank == max_rank], " they win/split a total of ", self._side_pots[pot_idx])

                    pot_contributors[i].refund(int(self._side_pots[pot_idx]/len(max_idx)))
                    self._side_pots[pot_idx] -= int(self._pot/len(max_idx))

                # any remaining chips after splitting go to the winner in the earliest position
                earliest = self._first_to_act([player for player in pot_contributors if player.handrank == max_rank])
                [player for player in pot_contributors if player.handrank == max_rank][earliest].refund(self._side_pots[pot_idx])

    def deal(self):
        for player in self._seats:
            if not player.emptyplayer:
                if player.playing_hand:
                    player.addtohand(self._get_card())
        for player in self._seats:
            if not player.emptyplayer:
                if player.playing_hand:
                    player.addtohand(self._get_card())

    def new_round(self):
        for player in self._player_dict.values():
            player.currentbet = 0
            player.playedthisround = False
        self._round += 1
        self._tocall = 0

    def flop(self):
        self._discard.append(self._get_card()) #burn
        for _ in range(3):
            self._community.append(self._get_card())

    def turn(self):
        self._discard.append(self._get_card()) #burn
        self._community.append(self._get_card())

    def river(self):
        self._discard.append(self._get_card()) #burn
        self._community.append(self._get_card())

    def _get_card(self):
        n = random.randint(0,len(self._deck)-1)
        card = self._deck[n]
        del self._deck[n]
        return card

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
        self._deck = range(range(52))
        self._button = (self._button + 1) % len(self._seats)
        while not self._seats[self._button].playing_hand:
            self._button = (self._button + 1) % len(self._seats)

    def output_state(self, current_player):
        # print("inside output state")
        return {'players':[player.player_state() for player in self._seats], 'community':self._community, 'my_seat': current_player.get_seat(), 'pocket_cards':current_player.pocket_cards(), 'pot':self._totalpot, 'button':self._button, 'tocall':(self._tocall-current_player.currentbet), 'stack':current_player.stack, 'bigblind':self._bigblind, 'playerID':current_player.playerID}

class Player(object):
    def __init__(self, host, port, playerID, name, stack, emptyplayer = False):
        self._host = host
        self._port = port
        self.playerID = playerID
        self._name = name

        self._hand = []
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

    def addtohand(self, card):
        self._hand.append(card)

    def reset_hand(self):
        self._hand=[]

    def pocket_cards(self):
        return self._hand

    def bet(self, bet_size):
        temp = min(bet_size, self.stack)
        self.stack -= temp
        self.currentbet += temp
        self.playedthisround = True
        if self.stack == 0:
            self.isallin = True

    def refund(self, ammount):
        self.stack += ammount

    def player_state(self):
        return (self.playerID, self.stack, self.playing_hand, self.betting)

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

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ()

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

    server = SimpleXMLRPCServer(("localhost", 8000), logRequests=False, allow_none=True, requestHandler=RequestHandler)
    server.register_instance(table_proxy, allow_dotted_names=True)


    # table.start()
    # table.join()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

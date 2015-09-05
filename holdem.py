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
        card_rank = card_int % 12
        card_suit = card_int/12
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
        self._pot = 0
        self._tocall = 0

        self._seats = [None]*seats
        self._player_dict = {}

        self._lock = threading.Lock()
        self._run_thread = threading.Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()


    def run(self):
        while True:
            players = [player for player in self._seats if player is not None]
            print("So far ", [player.threadID for player in players], " players have joined the game.")
            answer = input("Would you like to start?")
            if answer[0] == 'y':
                self.start_game()
            else:
                time.sleep(1)


    def start_game(self):
        with self._lock:
            players = [player for player in self._seats if player is not None]
            print("players:", players)
            players_playing = [player for player in players if player.playing()]
            print("players_playing:", players_playing)

            self.new_round()
            self._round=0

            while len(players_playing)>1:
                current_player = players_playing.index(self._seats[self._button])
                current_player = (current_player + 1) % len(players_playing)

                # print("players_playing", [player.threadID for player in players_playing])

                # small blind
                if self._smallblind> players_playing[current_player].stack:
                    self._pot += players_playing[current_player].stack
                    players_playing[current_player].bet(players_playing[current_player].stack)
                else:
                    players_playing[current_player].bet(self._smallblind)
                    self._pot += self._smallblind
                print("posted small blind, pot size:", self._pot)
                current_player = (current_player + 1) % len(players_playing)

                # big blind
                if self._bigblind> players_playing[current_player].stack:
                    self._pot += players_playing[current_player].stack
                    players_playing[current_player].bet(players_playing[current_player].stack)
                else:
                    players_playing[current_player].bet(self._bigblind)
                    self._pot += self._bigblind
                print("posted big blind, pot size:", self._pot)
                self._tocall = self._bigblind

                self._round = 0
                while self._round<4
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

                    current_player = (current_player + 1) % len(players_playing)
                    while not players_playing[current_player].playedthisround:

                        # if current players is all in, skip their turn and go to the next player
                        if players_playing[current_player].isallin:
                            current_player = (current_player + 1) % len(players_playing)
                            continue

                        # send player board state and ask for their response
                        state = self.output_state(players_playing[current_player].threadID)
                        # print("got state",state)
                        print("requesting move from player ", players_playing[current_player].threadID)

                        move = players_playing[current_player].server.player_move(state)

                        print("Got move from player ", players_playing[current_player].threadID)
                        print(players_playing[current_player].threadID, move)

                        if move[0] in ['call', 'raise', 'check']:
                            players_playing[current_player].bet(move[1])
                            players_playing[current_player].playedthisround = True
                            #if raise occurered, everybody else must respond
                            if move[0] == 'raise':
                                for player in players_playing:
                                    if player != players_playing[current_player]:
                                        player.playedthisround = False
                                self._tocall = move[1]
                            self._pot += move[1]


                            current_player = (current_player + 1) % len(players_playing)
                        elif move[0] == 'fold':
                            players_playing.pop(current_player)
                            current_player = current_player % len(players_playing)

                    # determine first player to act in list players_playing
                    temp = self._button
                    temp = temp + 1 % len(self._seats)
                    while not self._seats[temp].playing():
                        temp = temp +1 % len(self._seats)
                    current_player = players_playing.index(self._seats[temp])

                    #break if a single player left
                    if len(players_playing)==1:
                        break

                    self.new_round()


                # resolve the game and move the button
                resolve_game(players_playing)
                self._button = self.button + 1 % len(self._seats)

    def resolve_game(self, players_playing):
        if len(players_playing)==1:
            print("player ", players_playing[0].threadID, " wins the pot (", self._pot, ")")
            players_playing[0].refund(self._pot)
            self._pot = 0
        else:
            if self._round==0:
                self.flop()
            if self._round==1:
                self.turn()
            if self._round==2:
                self.river()
            for player in players_playing:
                player.handrank = evalHand(player.pocket_cards + self._community)
            max_rank = max([player.handrank for player in players_playing])
            max_idx = [i for i, j in enumerate([player.handrank for player in players_playing]) if j == max_rank]
            # pay the winner(s)
            for i in max_idx:
                players_playing[i].refund(self._pot/len(max_idx))
                self._pot -= self._pot/len(max_idx)

    def deal(self):
        for player in self._seats:
            if player != None:
                if player.playing():
                    player.addtohand(self._get_card())
        for player in self._seats:
            if player != None:
                if player.playing():
                    player.addtohand(self._get_card())

    def new_round(self):
        for player in self._player_dict.values():
            player.currentbet = 0
            player.playedthisround = False
        self._round += 1

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

    def add_player(self, threadID, name, stack, host, port):
        if threadID not in self._player_dict:
            player = Player(threadID, name, stack, host, port)
            idx = self._seats.index(None)
            self._seats[idx] = player
            self._player_dict[threadID] = player

    def remove_player(self, threadID):
        try:
            if threadID in self._player_dict:
                self._seats.remove(self._player_dict[threadID])
                del self._player_dict[threadID]
        except ValueError:
            pass

    def reset(self):
        for player in self._seats:
            if player != None:
                player.reset_hand()
        self._deck = range(range(52))
        self._button = (self._button + 1) % len(self._seats)
        while not self._seats[self._button].playing():
            self._button = (self._button + 1) % len(self._seats)

    def output_state(self, threadID):
        # print("inside output state")
        return {'players':[player.player_state() for player in self._player_dict.values() if player.threadID != threadID], 'community':self._community, 'pocket_cards':self._player_dict[threadID].pocket_cards(), 'pot':self._pot, 'button':self._button, 'tocall':(self._tocall-self._player_dict[threadID].currentbet), 'stack':self._player_dict[threadID].stack, 'bigblind':self._bigblind, 'threadID':threadID}

class Player(object):
    def __init__(self, threadID, name, stack, host, port):
        self._host = host
        self._port = port
        self.threadID = threadID
        self._name = name
        self._hand = []
        self.stack = stack
        self.isallin = False
        self._isplaying = True
        self._isbetting = False
        self.currentbet = 0
        self.playedthisround = False
        self.myturn = False
        # self.seat

        self._address = "http://%s:%s" % (host, port)
        self.server = xmlrpc.client.ServerProxy(self._address)
        self.handrank = 0


    def addtohand(self, card):
        self._hand.append(card)

    def reset_hand(self):
        self._hand=[]

    def pocket_cards(self):
        return self._hand

    def playing(self):
        return self._isplaying

    def bet(self, bet_size):
        temp = min(bet_size, self.stack)
        self.stack -= temp
        self.currentbet += temp
        if self.stack <= 0:
            self.isallin = True

    def refund(self, ammount):
        self.stack += ammount

    def betting(self):
        return self._isbetting

    def player_state(self):
        return (self.threadID, self.stack, self.playing(), self.betting())

class TableProxy(object):
    def __init__(self, table):
        self._table = table
    def get_table_state(self, threadID):
        # print("inside get_table_state in tableproxy")
        return self._table.output_state(threadID)

    def add_player(self, threadID, name, stack, host, port):
        self._table.add_player(threadID, name, stack, host, port)

    def start_game(self):
        self._table.start_game()

    # def player_move(self, threadID, result):

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

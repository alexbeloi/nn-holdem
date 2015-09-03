import argparse
import threading
import xmlrpc.client
import time

class Table(threading.Thread):
    def __init__(self, seats = 8, blinds = True, sb = 10, bb = 25, host, port):
        super(Table, self).__init__()
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

    def run(self):
        players = [player for player in self._seats if player not None]
        players_playing = [player for player in players if player.playing()]
        button_idx = players_playing.index(self._seats[self._button])
        while len(players_playing)>1:
            current_player = button_idx
            current_player = current_player +1 % len(players_playing)

            # small blind
            players_playing[current_player].bet(self._smallblind)
            self.pot += self._smallblind

            current_player = current_player +1 % len(players_playing)
            # big blind
            players_playing[current_player].bet(self._bigblind)
            self.pot += self._bigblind
            self._tocall = self._bigblind

            self.deal()
            current_player = current_player +1 % len(players_playing)
            while current_player != button_idx+2:
                state = get_table_state(players_playing[current_player])
                move = players_playing[current_player].server.player_move(state)
                print move
                if move[1] >= 0:
                    players_playing[current_player].bet(move[1])
                    self._pot += move[1]
                    if move[1] > tocall:
                        tocall = move[1]
                elif move[1] <0:

                current_player = current_player +1 % len(players_playing)





    def deal(self):
        for player in self._seats:
            if player not None:
                if player.playing():
                    player.addtohand(self._get_card())
        for player in self._seats:
            if player not None:
                if player.playing():
                    player.addtohand(self._get_card())

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
        if threadID in self._player_dict:
            self._seats.remove(self._player_dict[threadID])
            del self._player_dict[threadID]
        except ValueError:
            pass

    def reset(self):
        for player in self._seats:
            if player not None:
                player.reset_hand()
        self._deck = range(range(52))
        self._button = (self._button + 1) % len(self._seats)
        while not self._seats[self._button].playing():
            self._button = (self._button + 1) % len(self._seats)

    def output_state(self, threadID):
        with self._lock:

            return {'players':[player.player_state() for player in players if player.threadID != threadID], 'pocket_cards':self._player_dict[threadID].pocket_cards() 'pot':self._pot, 'button':self._button, 'tocall':self._tocall, 'stack':self._player_dict[threadID].stack 'bigblind':self._bigblind}

class Player(object):
    def __init__(self, threadID, name, stack, host, port):
        self._host
        self._port
        self._hand = []
        self.stack = stack
        self.bet = 0
        self._isallin = False
        self._isplaying = True
        self._isbetting = False
        self.myturn = False
        self.threadID = threadID
        address = "http://%s:%s" % (host, port)
        self.server = xmlrpc.client.ServerProxy(address)

    def addtohand(self, card):
        self._hand.append(card)

    def reset_hand(self):
        self._hand=[]

    def pocket_cards(self):
        return self._hand

    def playing(self):
        return self._isplaying

    def bet(self, bet_size):
        self.stack -= bet_size
        self.bet = bet_size
        if self.stack <= 0:
            self._isallin = True

    def refund(self, ammount):
        self.stack += ammount

    def betting(self):
        return self._isbetting

    def player_state(self):
        return (self.stack, self.playing(), self.betting())

class TableProxy(object):
    def __init__(self, table):
        self._table = table
    def get_table_state(self, threadID):
        return table.output_state(self, threadID):

    def player_move(self, threadID, result):

if __name__ = '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument("num_players", type=int, default=1)
    parser.add_argument("host", type=str, default="localhost")
    parser.add_argument("port", type=str, default="8000")
    args = parser.parse_args()

    print "Welcome to the Texas Holdem table, how many seats would you like at this table? (default=8)"
    print
    default_yesno = input("default configuration? (y/n) ")
    if default_yesno[0] == 'y':
        table = Table(args.host, args.port)
    else:
        seats = input("Number of seats: ")

        print "Would you like to play with blinds or antes? (default=blinds)"
        print "1) Blinds"
        print "2) Antes"
        blind_or_ante = input("Choose your option: ")
        if blind_or_ante == 1:
            blinds = True
            print "How large should the small-blind/big-blind be? (default = 10/25)"
            print "1) 10/25"
            print "2) 25/50"
            print "3) 50/100"
            print "4) 100/200"
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
            print "How big should the antes be? (default=50)"
            print "1) 10"
            print "2) 25"
            print "3) 50"
            print "4) 100"
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
                print "Invalid option, defaulting to ante size = 50"
                ante_ammount = 50
        else:
            print "Invalid input, defaulting to 10/25 blinds."
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

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

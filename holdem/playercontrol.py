import numpy as np
from threading import Thread
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

from .holdemai import HoldemAI
from deuces.deuces import Card

class PlayerControl(object):
    def __init__(self, host, port, playerID, ai_flag = False, ai_type = 0, name = "Alice", stack = 2000):
        self.server = xmlrpc.client.ServerProxy('http://0.0.0.0:8000')
        self.daemon = True

        self._ai_flag = ai_flag
        self._ai_type = ai_type
        self.playerID = playerID
        if self._ai_flag:
            self.ai = HoldemAI(np.random.randint(1,99999999999))
        self._name = name
        self.host = host
        self.port = port
        self._stack =  stack
        self._hand = []

        print("Player ", self.playerID, " Joining game")
        self.server.add_player(self.host, self.port, self.playerID, self._name, self._stack)

    def save_ai_state(self):
        if self._ai_flag and self._ai_type == 0:
            self.ai.save()
        else:
            print("AI type ", self._ai_type, "won")

    def print_table(self, table_state):
        print("Stacks:")
        players = table_state.get('players', None)
        for player in players:
            print(player[4], ": ", player[1], end="")
            if player[2] == True:
                print("(P)", end="")
            if player[3] == True:
                print("(Bet)", end="")
            if player[0] == table_state.get('button'):
                print("(Button)", end="")
            if players.index(player) == table_state.get('my_seat'):
                print("(me)", end="")
            print("")

        print("Community cards: ", end="")
        Card.print_pretty_cards(table_state.get('community', None))
        print("Pot size: ", table_state.get('pot', None))

        print("Pocket cards: ", end="")
        Card.print_pretty_cards(table_state.get('pocket_cards', None))
        print("To call: ", table_state.get('tocall', None))

    def update_localstate(self, table_state):
        self._stack = table_state.get('stack')
        self._hand = table_state.get('pocket')

    def player_move(self, table_state):
        self.update_localstate(table_state)
        tocall = min(table_state.get('tocall', None),self._stack)
        minraise = table_state.get('minraise', None)
        move_tuple = ('Exception!',-1)
        # ask this human meatbag what their move is
        if not self._ai_flag:
            self.print_table(table_state)
            if tocall == 0:
                print("1) Raise")
                print("2) Check")
                try:
                    choice = int(input("Choose your option: "))
                except:
                    choice = 0
                if choice == 1:
                    choice2 = int(input("How much would you like to raise to? (min = {}, max = {})".format(minraise,self._stack)))
                    while choice2 < minraise:
                        choice2 = int(input("(Invalid input) How much would you like to raise? (min = {}, max = {})".format(minraise,self._stack)))
                    move_tuple = ('raise',choice2)
                elif choice == 2:
                  move_tuple = ('check', 0)
                else:
                    print('doing something stupid')
                    move_tuple = ('check', 0)
            else:
                print("1) Raise")
                print("2) Call")
                print("3) Fold")
                try:
                    choice = int(input("Choose your option: "))
                except:
                    choice = 0
                if choice == 1:
                    choice2 = int(input("How much would you like to raise to? (min = {}, max = {})".format(minraise,self._stack)))
                    while choice2 < minraise:
                        choice2 = int(input("(Invalid input) How much would you like to raise to? (min = {}, max = {})".format(minraise,self._stack)))
                    move_tuple = ('raise',choice2)
                elif choice == 2:
                    move_tuple = ('call', tocall)
                elif choice == 3:
                   move_tuple = ('fold', -1)
                else:
                    move_tuple = ('call', tocall)


        # feed table state to ai and get a response
        else:
            # neural network output
            # bet_size = self.ai.act(table_state)
            # bet_size += table_state.get('bigblind') - (bet_size % table_state.get('bigblind'))

            if self._ai_type == 0:
                # neural network output
                bet_size = self.ai.act(table_state)
                bet_size += table_state.get('bigblind') - (bet_size % table_state.get('bigblind'))
            elif self._ai_type == 1:
                # check/fold bot
                bet_size = 0
            elif self._ai_type == 2:
                # check/call bot
                bet_size = tocall
            else:
                # random bot
                bet_size = np.random.randint(0,self._stack)
                bet_size += table_state.get('bigblind') - (bet_size % table_state.get('bigblind'))


            bet_size = min(bet_size, self._stack)
            # print("ai bet", bet_size, self.playerID)
            if bet_size < tocall:
                if bet_size >= self._stack:
                    move_tuple = ('call', self._stack)
                elif not tocall:
                    move_tuple = ('check', 0)
                else:
                    move_tuple = ('fold',-1)
            elif bet_size > tocall:
                if bet_size >= minraise:
                    move_tuple = ('raise', min(bet_size, self._stack))
                else:
                    move_tuple = ('call', tocall)
            elif bet_size == tocall:
                if tocall:
                    move_tuple = ('call', tocall)
                else:
                    move_tuple = ('check', 0)
        # self.print_table(table_state)
        # print("bet_size:", bet_size)
        return move_tuple

class PlayerControlProxy(object):
    def __init__(self,player):
        self._quit = False
        self._player = player
        self.server = SimpleXMLRPCServer((self._player.host, self._player.port), logRequests=False, allow_none=True)
        self.server.register_instance(self, allow_dotted_names=True)
        Thread(target = self.run).start()

    def run(self):
        while not self._quit:
            self.server.handle_request()

    def player_move(self, output_spec):
        return self._player.player_move(output_spec)

    def print_table(self, table_state):
        self._player.print_table(table_state)

    def save_ai_state(self):
        self._player.save_ai_state()

    def quit(self):
        self._player.server.remove_player(self._player.playerID)
        self._quit = True

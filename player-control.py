import argparse
import threading
import xmlrpc.client
import time
import math
import sys
import holdem
from deuces.deuces import Card, Deck, Evaluator
from xmlrpc.server import SimpleXMLRPCServer

class PlayerControl(object):
    def __init__(self, host, port, playerID, name = "Alice", stack=2000, playing=True, ai_flag=False):
        self._server = xmlrpc.client.ServerProxy('http://localhost:8000')
        self.daemon = True

        self._ai_flag = ai_flag
        self._name = name
        self._host = host
        self._port = port
        self._playerID = playerID
        self._stack =  stack
        self._hand = []

        self._run_thread = threading.Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def run(self):
        print("Player ", self._playerID, " Joining game")
        self._server.add_player(self._host, self._port, self._playerID, self._name, self._stack)
        table_state = self._server.get_table_state(self._playerID)
        # print(table_state)
        while True:
            table_state_new = self._server.get_table_state(self._playerID)
            # print(table_state)
            if table_state_new != table_state:
                table_state = table_state_new
                # self.print_table(table_state)
            time.sleep(10)
            if not table_state:
                print("not in hand... waiting")
                time.sleep(10)
                continue

    def print_table(self, table_spec):
        print("Stacks:")
        players = table_spec.get('players', None)
        for player in players:
            print(player[0], ": ", player[1], end="")
            if player[2] == True:
                print("(P)", end="")
            if player[3] == True:
                print("(B)", end="")
            if players.index(player) == table_spec.get('my_seat'):
                print("(me)", end="")
            print("")

        print("Community cards: ", end="")
        Card.print_pretty_cards(table_spec.get('community', None))
        print("Pot size: ", table_spec.get('pot', None))

        print("Pocket cards: ", end="")
        Card.print_pretty_cards(table_spec.get('pocket_cards', None))
        print("To call: ", table_spec.get('tocall', None))

    def update_localstate(self, table_state):
        self._stack = table_state.get('stack')
        self._hand = table_state.get('pocket')

    def player_move(self, table_state):
        self.update_localstate(table_state)
        self.print_table(table_state)
        tocall = table_state.get('tocall', None)
        minraise = max(table_state.get('bigblind', None), 2*table_state.get('lastraise', None))
        move_tuple = ('test', 0)

        # ask this human meatbag what their move is
        if not self._ai_flag:
            if tocall == 0:
                print("1) Raise")
                print("2) Check")
                choice = int(input("Choose your option: "))
                if choice == 1:
                    choice2 = int(input("How much would you like to raise to? (min = {}, max = {})".format(minraise,self._stack)))
                    while choice2 < minraise:
                        choice2 = int(input("(Invalid input) How much would you like to raise? (min = {}, max = {})".format(minraise,self._stack)))
                    move_tuple = ('raise',choice2)
                    self._stack -= choice2
                if choice == 2:
                  move_tuple = ('check', 0)
            else:
                print("1) Raise")
                print("2) Call")
                print("3) Fold")
                choice = int(input("Choose your option: "))
                if choice == 1:
                    choice2 = int(input("How much would you like to raise to? (min = {}, max = {})".format(minraise,self._stack)))
                    while choice2 < minraise:
                        choice2 = int(input("(Invalid input) How much would you like to raise to? (min = {}, max = {})".format(minraise,self._stack)))
                    move_tuple = ('raise',choice2)
                    self._stack -= choice2
                elif choice == 2:
                    move_tuple = ('call', tocall)
                    self._stack -= tocall
                elif choice == 3:
                   move_tuple = ('fold', -1)

        # feed table state to ai and get a response
        else:
            bet_size = nnholdem(table_state)
            if bet_size < tocall:
                if bet_size >= self._stack:
                    move_tuple = ('allin', self._stack)
                else:
                    move_tuple = ('fold',-1)
            elif bet_size > tocall:
                bet_size -= bet_size % table_state.get('bigblind')
                if bet_size >tocall:
                    self._stack -= min(bet_size, self._stack)
                    move_tuple = ('raise', min(bet_size, self._stack))
                else:
                    move_tuple = ('call', tocall)
            elif bet_size == tocall:
                self._stack -= tocall
                move_tuple = ('call', tocall)
        return move_tuple

class PlayerProxy(object):
    def __init__(self,player):
        self._player = player

    def player_move(self, output_spec):
        return self._player.player_move(output_spec)

    def print_table(self, table_state):
        self._player.print_table(table_state)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("id", type=int, default="2")
    # parser.add_argument("ai", type=bool, default=True)
    args = parser.parse_args()

    player = PlayerControl("localhost", 8001+args.id, args.id)
    player_proxy = PlayerProxy(player)

    server = SimpleXMLRPCServer(("localhost", 8001+args.id), logRequests=False, allow_none=True)
    server.register_instance(player_proxy, allow_dotted_names=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

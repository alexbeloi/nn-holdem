import argparse
import threading
import xmlrpc.client
import time
import math
import sys
import holdem
from xmlrpc.server import SimpleXMLRPCServer

# table_spec['players'][#] is tuple ((int) threadID, (int) stack, (bool) playing, (bool) betting)
# def my_state(table_spec):
#     players = table_spec.get('players', None)
#     pocket_cards = table_spec.get('pocket_cards', None)
#     pot = table_spec.get('pot', None)
#     button = table_spec.get('button', None)
#     tocall = table_spec.get('tocall', None)

class PlayerControl(object):
    def __init__(self, host, port, threadID, name, stack=2000, playing=True, ai_flag=False):
        # super(PlayerControl, self).__init__()
        self._server = xmlrpc.client.ServerProxy('http://localhost:8000')
        self.daemon = True

        self._ai_flag = ai_flag
        self._name = name
        self._host = host
        self._port = port
        self._threadID = threadID
        self._stack =  stack
        self._hand = []

        self._run_thread = threading.Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def run(self):
        print("Player ", self._threadID, " Joining game")
        self._server.add_player(self._threadID, self._name, self._stack, self._host, self._port)
        table_state = self._server.get_table_state(self._threadID)
        # print(table_state)
        while True:
            table_state_new = self._server.get_table_state(self._threadID)
            # print(table_state)
            if table_state_new != table_state:
                table_state = table_state_new
                # self.show_table(table_state)
            time.sleep(10)
            if not table_state:
                print("not in hand... waiting")
                time.sleep(10)
                continue

    def show_table(self, table_spec):
        # print player stacks and inf (playing/betting)
        # players = [player for player in table_spec.get('players', None) if player != None]
        print("Stacks:")
        for player in table_spec.get('players', None):
            print(player[0], ": ", player[1], end="")
            if player[2] == True:
                print("(P)", end="")
            if player[3] == True:
                print("(B)", end="")
            print("")
        print("Community cards: ", [holdem.card_parse(card) for card in table_spec.get('community', None)])
        print("Pot size: ", table_spec.get('pot', None))
        print("Pocket cards: ", [holdem.card_parse(card) for card in table_spec.get('pocket_cards', None)])
        print("To call: ", table_spec.get('tocall', None))

    def update_localstate(self, table_state):
        self._stack = table_state.get('stack')
        self._hand = table_state.get('pocket')

    def player_move(self, table_state):
        self.update_localstate(table_state)
        self.show_table(table_state)
        tocall = table_state.get('tocall')
        move_tuple = ('test', 0)

        if not self._ai_flag:
            if tocall == 0:
                print("1) Raise")
                print("2) Check")
                choice = int(input("Choose your option: "))
                if choice == 1:
                    choice2 = int(input("How much would you like to raise to? (min = {}, max = {})".format(tocall,self._stack)))
                    while choice2 < tocall:
                        choice2 = int(input("(Invalid input) How much would you like to raise? (min = {}, max = {})".format(max(tocall, table_state.get('bigblind')),self._stack)))
                    move_tuple = ('raise',min(choice2, self._stack))
                    self._stack -= choice2
                if choice == 2:
                  move_tuple = ('check', 0)
            else:
                print("1) Raise")
                print("2) Call")
                print("3) Fold")
                choice = int(input("Choose your option: "))
                if choice == 1:
                    choice2 = int(input("How much would you like to raise? (min = {}, max = {})".format(tocall,self._stack)))
                    while choice2 < tocall:
                        choice2 = int(input("(Invalid input) How much would you like to raise? (min = {}, max = {})".format(tocall,self._stack)))
                    move_tuple = ('raise',min(choice2, self._stack))
                    self._stack -= choice2
                elif choice == 2:
                    move_tuple = ('call', tocall)
                    self._stack -= tocall
                elif choice == 3:
                   move_tuple = ('fold', -1)

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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("id", type=int, default="2")
    parser.add_argument("ai", type=bool, default=True)
    args = parser.parse_args()

    player = PlayerControl("localhost", 8001+args.id, args.id, args.ai)
    player_proxy = PlayerProxy(player)

    server = SimpleXMLRPCServer(("localhost", 8001+args.id), logRequests=False, allow_none=True)
    server.register_instance(player_proxy, allow_dotted_names=True)

    # for player in players:
    #     player.start()
    #
    # for player in players:
    #     player.join()


    # server = SimpleXMLRPCServer(("0.0.0.0", 8000), Handler)

    # server.register_introspection_functions()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

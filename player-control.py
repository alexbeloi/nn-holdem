import argparse
import threading
import xmlrpc.client
import time
import math
import sys
import holdem
import numpy as np
from nn import NeuralNetwork

from deuces.deuces import Card, Deck, Evaluator
from xmlrpc.server import SimpleXMLRPCServer

# takes card from deuces Card class (reprsented by int) and gives its 29 digit binary representation in a list
def card_to_binlist(card):
    return [ord(b)-48 for b in bin(card)[2:].zfill(29)]

def bin_to_binlist(bin_num):
    return [ord(b)-48 for b in bin_num]

def center_bin(num):
    return list(map(lambda x: -1 if x==0 else x, num))

def rescale(num, mean, stdev):
    return int((num-mean)/(stdev*np.sqrt(2*np.pi)))

def descale(num, mean, stdev):
    return int(num*(stdev*np.sqrt(2*np.pi))+mean)

def _chip_mean(table_state):
    players = table_state.get('players', None)
    bigblind = table_state.get('bigblind', None)
    return sum([p[1]/bigblind for p in players])/len(players)

def _chip_std(table_state):
    players = table_state.get('players', None)
    bigblind = table_state.get('bigblind', None)
    return np.std([p[1]/bigblind for p in players])

# parses table_state into clean (mostly binary) data for neural network
def input_parser(table_state):
    hand = table_state.get('pocket_cards', None)
    community = table_state.get('community', None)
    players = table_state.get('players', None)
    my_seat = table_state.get('my_seat', None)
    pot = table_state.get('pot', None)
    tocall = table_state.get('tocall', None)
    bigblind = table_state.get('bigblind', None)
    lastraise = table_state.get('lastraise', None)

    players = [[i for i in j] for j in players]

    # binary data
    hand_bin = [j for i in [card_to_binlist(c) for c in hand] for j in i]
    community = community + [0]*(5-len(community))
    comm_bin = [j for i in [card_to_binlist(c) for c in community] for j in i]
    my_seat_bin = bin_to_binlist(bin(my_seat)[2:].zfill(3))

    # continuous data
    # normalize chip data by bigblind
    for p in players:
        p[1] = p[1]/bigblind
    pot = pot/bigblind
    tocall = tocall/bigblind
    lastraise = lastraise/bigblind
    bigblind = 1

    chip_mean = sum([p[1] for p in players])/len(players)
    chip_stdev = np.std([p[1] for p in players])

    # player_data = [[0]*4]*len(players)
    # print(table_state.get('players'))
    # for i,_ in enumerate(players):
    #     player_data[i][0] = bin_to_binlist(bin(players[i][0])[2:].zfill(3))
    #     player_data[i][1] = [rescale(players[i][1], chip_mean, chip_stdev)]
    #     player_data[i][2] = bin_to_binlist(bin(players[i][2])[2:])
    #     player_data[i][3] = bin_to_binlist(bin(players[i][3])[2:])
    for p in players:
        p[0] = bin_to_binlist(bin(p[0])[2:].zfill(3))
        p[1] = [rescale(p[1], chip_mean, chip_stdev)]
        p[2] = bin_to_binlist(bin(p[2])[2:])
        p[3] = bin_to_binlist(bin(p[3])[2:])

    # print(table_state.get('players'))
    # centering all chip values around the player chip_mean
    pot_centered = rescale(pot, chip_mean, chip_stdev)
    tocall_centered = rescale(tocall, chip_mean, chip_stdev)
    lastraise_centered = rescale(lastraise, chip_mean, chip_stdev)
    bigblind_centered = rescale(bigblind, chip_mean, chip_stdev)

    output_bin = hand_bin + comm_bin + my_seat_bin
    output_cont = [pot_centered, tocall_centered, lastraise_centered, bigblind_centered]
    for p in players:
        output_bin = output_bin + p[0] + p[2] + p[3]
        output_cont = output_cont + p[1]

    output = center_bin(output_bin) + output_cont
    return output

class PlayerControl(object):
    def __init__(self, host, port, playerID, ai_flag=False, name = "Alice", stack=2000, playing=True):
        self._server = xmlrpc.client.ServerProxy('http://localhost:8000')
        self.daemon = True

        self._ai_flag = ai_flag
        self._playerID = playerID
        if self._ai_flag:
            self._nn = NeuralNetwork(258, [258,200,1], playerID)
        self._name = name
        self._host = host
        self._port = port
        self._stack =  stack
        self._hand = []

        print("Player ", self._playerID, " Joining game")
        self._server.add_player(self._host, self._port, self._playerID, self._name, self._stack)

    def save_network(self):
        if self._ai_flag:
            self._nn.save()

        # self._run_thread = threading.Thread(target = self.run, args=())
        # self._run_thread.daemon = True
        # self._run_thread.start()

    # def run(self):
    #     print("Player ", self._playerID, " Joining game")
    #     self._server.add_player(self._host, self._port, self._playerID, self._name, self._stack)
        # table_state = self._server.get_table_state(self._playerID)
        # # print(table_state)
        # while True:
        #     table_state_new = self._server.get_table_state(self._playerID)
        #     # print(table_state)
        #     if table_state_new != table_state:
        #         table_state = table_state_new
        #         # self.print_table(table_state)
        #     time.sleep(10)
        #     if not table_state:
        #         print("not in hand... waiting")
        #         time.sleep(10)
        #         continue

    def print_table(self, table_state):
        print("Stacks:")
        players = table_state.get('players', None)
        for player in players:
            print(player[0], ": ", player[1], end="")
            if player[2] == True:
                print("(P)", end="")
            if player[3] == True:
                print("(B)", end="")
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
        # self.print_table(table_state)
        tocall = table_state.get('tocall', None)
        minraise = max(table_state.get('bigblind', None), 2*table_state.get('lastraise', None))

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
                elif choice == 2:
                    move_tuple = ('call', tocall)
                elif choice == 3:
                   move_tuple = ('fold', -1)

        # feed table state to ai and get a response
        else:
            # neural network output
            output = self._nn.activate(input_parser(table_state))[-1][0]
            bet_size = descale(output, _chip_mean(table_state), _chip_std(table_state))
            bet_size += table_state.get('bigblind') - (bet_size % table_state.get('bigblind'))
            # print(bet_size)
            if bet_size < tocall:
                if bet_size >= self._stack:
                    move_tuple = ('call', self._stack)
                else:
                    move_tuple = ('fold',-1)
            elif bet_size > tocall:
                if bet_size >= minraise:
                    move_tuple = ('raise', min(bet_size, self._stack))
                else:
                    move_tuple = ('call', tocall)
            elif bet_size == tocall:
                move_tuple = ('call', tocall)
        return move_tuple

class PlayerProxy(object):
    def __init__(self,player):
        self._player = player

    def player_move(self, output_spec):
        return self._player.player_move(output_spec)

    def print_table(self, table_state):
        self._player.print_table(table_state)

    def save_network(self):
        self._player.save_network()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("id", type=int, default="2")
    parser.add_argument('--ai', dest='ai', action='store_true')
    parser.add_argument('--no-ai', dest='ai', action='store_false')
    args = parser.parse_args()

    player = PlayerControl("localhost", 8001+args.id, args.id, args.ai)
    player_proxy = PlayerProxy(player)

    server = SimpleXMLRPCServer(("localhost", 8001+args.id), logRequests=False, allow_none=True)
    server.register_instance(player_proxy, allow_dotted_names=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

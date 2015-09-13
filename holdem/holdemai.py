import numpy as np
from .nn import NeuralNetwork

class HoldemAI(NeuralNetwork):
    def __init__(self, ID):
        super().__init__(258, [258,200,1], ID)
        self.chip_mean = 0
        self.chip_stdev = 0

    def act(self, table_state):
        parsed = self.input_parser(table_state)
        activated = self.activate(parsed)[-1][0]
        descaled = self.descale(activated)
        return descaled*table_state.get('bigblind')
        # return descaled

    # parses table_state from TableProxy into clean (mostly binary) data for neural network
    def input_parser(self, table_state):
        hand = table_state.get('pocket_cards', None)
        community = table_state.get('community', None)
        players = table_state.get('players', None)
        my_seat = table_state.get('my_seat', None)
        pot = table_state.get('pot', None)
        tocall = table_state.get('tocall', None)
        bigblind = table_state.get('bigblind', None)
        lastraise = table_state.get('lastraise', None)

        # need to make copy of list so that we don't edit table_state permanently
        players = [[i for i in j] for j in players]

        # binary data
        hand_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in hand] for j in i]
        community = community + [0]*(5-len(community))
        comm_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in community] for j in i]
        my_seat_bin = HoldemAI.bin_to_binlist(bin(my_seat)[2:].zfill(3))

        # continuous data
        # normalize chip data by bigblind
        for p in players:
            p[1] = p[1]/bigblind
        pot = pot/bigblind
        tocall = tocall/bigblind
        lastraise = lastraise/bigblind
        bigblind = 1

        self.chip_mean = sum([p[1] for p in players])/len(players)
        self.chip_stdev = np.std([p[1] for p in players])+0.01 #so we don't divide by zero
        # print('std: ', self.chip_stdev)

        for p in players:
            p[0] = HoldemAI.bin_to_binlist(bin(p[0])[2:].zfill(3))
            p[1] = [self.rescale(p[1])]
            p[2] = HoldemAI.bin_to_binlist(bin(p[2])[2:])
            p[3] = HoldemAI.bin_to_binlist(bin(p[3])[2:])

        # centering all chip values around the player chip_mean
        pot_centered = self.rescale(pot)
        tocall_centered = self.rescale(tocall)
        lastraise_centered = self.rescale(lastraise)
        bigblind_centered = self.rescale(bigblind)

        output_bin = hand_bin + comm_bin + my_seat_bin
        output_cont = [pot_centered, tocall_centered, lastraise_centered, bigblind_centered]
        for p in players:
            output_bin = output_bin + p[0] + p[2] + p[3]
            output_cont = output_cont + p[1]

        output = HoldemAI.center_bin(output_bin) + output_cont
        return output

    def rescale(self, num):
        # return int(num-self.chip_mean)
        # return int((num-mean)/(stdev+0.001))
        return int((num-self.chip_mean)/(self.chip_stdev*25*np.sqrt(2*np.pi)))

    def descale(self, num):
        # return int(num+self.chip_mean)
        # return int(num*(stdev)+mean)
        return int(num*(self.chip_stdev*25*np.sqrt(2*np.pi))+self.chip_mean)

    # takes card from deuces Card class (reprsented by int) and gives its 29 digit binary representation in a list, first 3 bits are unused
    @staticmethod
    def card_to_binlist(card):
        return [ord(b)-48 for b in bin(card)[2:].zfill(29)]

    @staticmethod
    def bin_to_binlist(bin_num):
        return [ord(b)-48 for b in bin_num]

    @staticmethod
    def center_bin(num):
        return list(map(lambda x: -1 if x==0 else x, num))

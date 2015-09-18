import numpy as np
from .nn import NeuralNetwork
from .analyzer import Analyzer

class HoldemAI(NeuralNetwork):
    def __init__(self, ID):
        super().__init__([31,20,5], ID)
        self.analyzer = Analyzer()

    def act(self, table_state):
        parsed = self.input_parser(table_state)
        activated = list(self.activate(parsed))
        # output vector interpreted as (raise, call, check, fold, bet_ammount)
        activated[-1] = self.rescale_output(activated[-1])
        return self.output_parser(activated, table_state)

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

        # make note of our own stack
        self.my_stack = players[my_seat][1]

        # need to make copy of list so that we don't edit table_state permanently
        players = [[i for i in j] for j in players]

        # setup analyzer
        self.analyzer.set_num_opponents(sum([1 for p in players if p[2]]))
        self.analyzer.set_pocket_cards(*hand)
        for card in community:
            self.analyzer.community_card(card)

        # computes win percentage as proxy for hand data and community data
        win_percent = self.analyzer.analyze()
        self.analyzer.reset()

        # # binary data
        # hand_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in hand] for j in i]
        # community = community + [0]*(5-len(community))
        # comm_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in community] for j in i]
        my_seat_bin = HoldemAI.bin_to_binlist(bin(my_seat)[2:].zfill(3))

        # continuous data
        # normalize chip data by bigblind
        for p in players:
            p[1] = p[1]/bigblind
        pot = pot/bigblind
        tocall = tocall/bigblind
        lastraise = lastraise/bigblind

        self.chip_mean = sum([p[1] for p in players])/len(players)
        self.chip_range = self.chip_mean*len(players)/2

        for p in players:
            p[0] = HoldemAI.bin_to_binlist(bin(p[0])[2:].zfill(3))
            p[1] = [(p[1]-self.chip_mean)/self.chip_range]
            p[2] = HoldemAI.bin_to_binlist(bin(p[2])[2:])
            p[3] = HoldemAI.bin_to_binlist(bin(p[3])[2:])


        # avg pot size in 8-person cash table No Limit Hold'em is reported to be ~6-10 big blinds
        # add: compute rolling average
        pot_centered = (pot-8)/self.chip_range

        # average to call size will be assumed to be 1/3 of average pot (educated guess)
        # add: compute rolling average
        tocall_centered = (tocall-8/3)/self.chip_range

        # treated same as tocall
        lastraise_centered = (lastraise-8/3)/self.chip_range

        # center win percentage
        win_percent_centered = (win_percent-0.5)*2

        # combine binary and continuous data into one vector

        # my_seat_bin  uses 3 inputs
        inputs_bin = my_seat_bin

        # pot_centered, tocall_centered, lastraise_centered, win_percent_centered each use 1 input
        inputs_cont = [pot_centered, tocall_centered, lastraise_centered, win_percent_centered]

        # each player addes 1 continuous input, and 2 binary inputs
        for p in players:
            inputs_bin = inputs_bin + p[2] + p[3]
            inputs_cont = inputs_cont + p[1]

        inputs = HoldemAI.center_bin(inputs_bin) + inputs_cont
        return inputs

    def rescale_output(self,num):
        # output of neural network is given from -1 to 1, we interpret this as a bet ammount as a percentage of the player's stack
        return int((num+1)*self.my_stack/2)

    # parses output for PlayerControl
    def output_parser(self, response, table_state):
        tocall = table_state.get('tocall', None)
        my_stack = table_state.get('players')[table_state.get('my_seat')][1]
        bigblind = table_state.get('bigblind', None)
        minraise = table_state.get('minraise', None)

        bet_size = response[-1]
        bet_size += bigblind -(bet_size % bigblind)
        bet_size = max(bet_size, my_stack)
        # response[0:4] = [raise_confidence, call_confidence, check_confidence, fold_confidence]
        if tocall > 0:
            # choose between raise, call, fold
            move_idx = np.argmax(response[:2] + response[3:-1])
            # 0 - Raise
            # 1 - Call
            # 3 - Fold
            if move_idx == 0:
                if bet_size < minraise:
                    return ('call', tocall)
                if tocall >= my_stack or tocall >= bet_size:
                    return ('call', tocall)
                return ('raise', min(max(bet_size, minraise), my_stack))
            elif move_idx == 1:
                return ('call', tocall)
            else:
                return ('fold', -1)
        else:
            # 0 - Raise
            # 2 - Check
            move_idx = np.argmax(response[:1] + response[2:-2])
            if move_idx == 0:
                return ('raise', bet_size)
            else:
                return ('check', 0)

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

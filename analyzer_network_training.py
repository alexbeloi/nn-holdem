import numpy as np
import random
from holdem import Analyzer, NeuralNetwork, HoldemAI
from deuces.deuces import Card, Deck, Evaluator

a = Analyzer()
a.monte_carlo_rounds = 2000

nn = NeuralNetwork([206,206,100,1], 'analyzer_network', 0.1)

deck = Deck()
hand = []
community = []
opponents = 0
game_stage = [0,3,4,5]

for i in range(1000000):
    community = []
    deck.shuffle()
    a.reset()

    hand = deck.draw(2)
    for _ in range(game_stage[random.randint(0,3)]):
        community.append(deck.draw(1))
    opponents = random.randint(1,7)

    a.set_num_opponents(opponents)
    a.set_pocket_cards(*hand)
    for card in community:
        a.community_card(card)

    mc_response = a.analyze()
    # print('mc response', mc_response)

    hand_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in hand] for j in i]
    community = community + [0]*(5-len(community))
    comm_bin = [j for i in [HoldemAI.card_to_binlist(c) for c in community] for j in i]
    opponents_bin = HoldemAI.bin_to_binlist(bin(opponents)[2:].zfill(3))

    inputs = HoldemAI.center_bin(hand_bin + comm_bin + opponents_bin)

    # print('nn response', (1+nn.activate(inputs))/2)
    print('error: ', 100*((nn.activate(inputs)+1)/2 - mc_response))
    nn.update_weights_linesearch(inputs, 2*mc_response-1)

    if (i % 100) == 0:
        print('SAVING ON ITERATION: ', i)
        nn.save()

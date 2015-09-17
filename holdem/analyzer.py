from deuces.deuces import Deck, Card, Evaluator

# hand strength estimator (same class as in https://github.com/neynt/pokertude but uses Deuces Deck, Card and Evaluator classes for the inner workings)
class Analyzer:
    def __init__(self):
        self.deck = Deck()
        self.reset()
        self._evaluator = Evaluator()
        self.monte_carlo_rounds = 1000

    def reset(self):
        self.deck.shuffle()
        self.hole_cards = []
        self.community_cards = []

    def set_num_opponents(self, n):
        self.num_opponents = n

    def set_monte_carlo_rounds(self, n):
        self.monte_carlo_rounds = n

    def set_pocket_cards(self, card1, card2):
        self.deck.remove(card1)
        self.deck.remove(card2)
        self.hole_cards.append(card1)
        self.hole_cards.append(card2)

    def community_card(self, card):
        self.deck.remove(card)
        self.community_cards.append(card)

    def analyze(self):
        wins = 0
        ties = 0
        to_flop = 5 - len(self.community_cards)
        to_draw = to_flop + 2 * self.num_opponents

        total_rounds = self.monte_carlo_rounds
        total_opponent_hands = total_rounds * self.num_opponents

        # Monte Carlo simulation
        for _ in range(self.monte_carlo_rounds):
            # Draw a uniformly random combination of unseen cards (remaining
            # community cards + 2 hole cards per opponent)
            drawn_cards = self.deck.sample(to_draw)
            all_comms = self.community_cards + drawn_cards[:to_flop]
            my_ranking = self._evaluator.evaluate(self.hole_cards, all_comms)

            # 2: win, 1: tie, 0: loss
            winner = 2
            for i in range(self.num_opponents):
                their_cards = drawn_cards[to_flop+2*i:to_flop+2*i+2]
                their_ranking =self._evaluator.evaluate(their_cards, all_comms)
                if my_ranking > their_ranking:
                    winner = 0
                elif my_ranking == their_ranking:
                    winner = min(winner, 1)
            if winner == 2:
                wins += 1
            elif winner == 1:
                ties += 1

        win_ratio = wins/total_rounds
        return win_ratio

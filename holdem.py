import argparse
import threading
import xmlrpc.client
import time

class Table(object):
    def __init__(self, blinds=True, rake=False):
        self._round = 0
        self._position = 0
        self._discard = []
        self._community = []
        self._pot = 0
        self._deck = list(range(52))
        self._players = []
        self._thread_registry = []

        self._lock = threading.Lock()

    def deal(self):
        for player in self._players:
            if player.playing():
                player.addtohand(_get_card())
        for player in self._players:
            if player.playing():
                player.addtohand(_get_card())

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

    def add_player(self, threadID, name, stack):
        if threadID not in self._thread_registry:
            player = Player(threadID, name, stack)
            self._players.append[player]
            self._thread_registry.append[threadID]

    def remove_player(self, threadID):
        if threadID in self._thread_registry:
            self._thread_registry.remove(threadID)
        except ValueError:
            pass

    def reset(self):
        for player in self._players:
            player.reset_hand()

        self._position = (self._position + 1) % len(self._players)
        while not self._players[self._position].playing():
            self._position = (self._position + 1) % len(self._players)

    def output_state(self, threadID):
        with self._lock:
            return {'players':[player.player_state() for player in players if player.threadID != threadID], 'pot' = self._pot, 'position' = self._position}

class Player(object):
    def __init__(self, threadID, name, stack):
        self._hand = []
        self._stack = stack
        self._isplaying = True
        self._isbetting = False
        self.threadID = threadID

    def addtohand(self, card):
        self._hand.append(card)

    def reset_hand(self):
        self._hand=[]

    def playing(self):
        return self._isplaying

    def betting(self):
        return self._isbetting

    def player_state(self):
        return (self._stack, self.playing(), self.betting())

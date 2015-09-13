import xmlrpc.client

class Player(object):
    def __init__(self, host, port, playerID, name, stack, emptyplayer = False):
        self._host = host
        self._port = port
        self._name = name
        self.playerID = playerID

        self.hand = []
        self.stack = stack
        self.currentbet = 0
        self.lastsidepot = 0
        self._seat = -1
        self.handrank = None

        # flags for table management
        self.emptyplayer = emptyplayer
        self.betting = False
        self.isallin = False
        self.playing_hand = False
        self.playedthisround = False
        self.sitting_out = True

        self._address = 'http://%s:%s' % (host, port)
        self.server = xmlrpc.client.ServerProxy(self._address)

    def get_seat(self):
        return self._seat

    def set_seat(self, value):
        self._seat = value

    def reset_hand(self):
        self._hand=[]
        self.playedthisround = False
        self.betting = False
        self.isallin = False
        self.currentbet = 0
        self.lastsidepot = 0
        self.playing_hand = (self.stack != 0)

    def bet(self, bet_size):
        self.playedthisround = True
        if not bet_size:
            return
        self.stack -= (bet_size - self.currentbet)
        self.currentbet = bet_size
        if self.stack == 0:
            self.isallin = True

    def refund(self, ammount):
        self.stack += ammount

    def player_state(self):
        return (self.get_seat(), self.stack, self.playing_hand, self.betting, self.playerID)

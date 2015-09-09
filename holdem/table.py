from threading import Thread, Lock
import time
from .player import Player
from xmlrpc.server import SimpleXMLRPCServer
from deuces.deuces import Card, Deck, Evaluator

class Table(object):
    BLIND_INCREMENTS = [[10,25],[25,50],[50,100],[100,200]]

    def __init__(self, seats = 8):
        self._blind_index = 0
        [self._smallblind, self._bigblind] = Table.BLIND_INCREMENTS[0]
        self._deck = Deck()
        self._evaluator = Evaluator()

        self.community = []
        self._round = 0
        self._button = 0
        self._discard = []
        self._side_pots = [0]*seats
        self._current_sidepot = 0
        self._totalpot = 0
        self._tocall = 0
        self._lastraise = 0
        self._number_of_games = 0

        # fill seats with dummy players
        self._seats = [Player(-1,-1,0,"empty",0,True) for _ in range(seats)]
        self._player_dict = {}

        self._lock = Lock()
        self._run_thread = Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def run(self):
        while True:
            players = [player for player in self._seats if not player.emptyplayer]
            if len(players) == len(self._seats):
                answer = input("Press [enter] to start a game:")
                if not answer:
                    self.start_game()
                print('starting game number: ', self._number_of_games)
                self._number_of_games += 1

                # increment blinds every 15 hands (based on avg hands/hour of 30)
                if (self._number_of_games % 15) == 0 and self._number_of_games < 60:
                    self.increment_blinds()

                if len([p for p in players if p.playing_hand]) == 1:
                    winner = [p for p in players if p.playing_hand][0]
                    print('player', winner.playerID, 'won the game')
                    winner.server.save_ai_state()
                    break
            else:
                time.sleep(1)

    def start_game(self):
        with self._lock:
            players = [player for player in self._seats if player.playing_hand]
            if sum([p.stack for p in players]) != 2000*len([p for p in self._seats if not p.emptyplayer]):
                raise ValueError('stacks are not adding up')
            self.new_round()
            self._round=0

            player = self._first_to_act(players)

            self.post_smallblind(player)
            player = self._next(players, player)
            self.post_bigblind(player)
            player = self._next(players, player)

            self._tocall = self._bigblind

            # rounds
            self._round = 0
            while self._round<4 and len(players)>1:
                if self._round == 0:
                    # deal phase
                    # print("Dealing")
                    self.deal()
                elif self._round == 1:
                    # floph phase
                    # print("Flop")
                    self.flop()
                elif self._round == 2:
                    # turn phase
                    # print("Turn")
                    self.turn()
                elif self._round ==3:
                    # river phase
                    # print("River")
                    self.river()

                done_players = []
                while not player.playedthisround:
                    if player.isallin:
                        player = self._next(players, player)
                        continue
                    move = player.server.player_move(self.output_state(player))

                    if move[0] == 'call':
                        self.player_bet(player, self._tocall)
                        print("Player", player.playerID, move)
                        player = self._next(players, player)
                    elif move[0] == 'check':
                        self.player_bet(player, player.currentbet)
                        print("Player", player.playerID, move)
                        player = self._next(players, player)
                    elif move[0] == 'raise':
                        self.player_bet(player, move[1])
                        print("Player", player.playerID, move)
                        for p in players:
                            if p != player:
                                p.playedthisround = False
                        player = self._next(players, player)
                    elif move[0] == 'fold':
                        folded_player = player
                        print("Player", player.playerID, move[0])
                        player = self._next(players, player)
                        players.remove(folded_player)
                        done_players.append(folded_player)
                        # break if a single player left
                        if len(players) ==1:
                            break


                player = self._first_to_act(players)
                self.resolve_sidepots(players + done_players)
                self.new_round()

            self.resolve_game(players)
            self.reset()

    def increment_blinds(self):
        self._blind_index = min(self._blind_index+1,3)
        [self._smallblind, self._bigblind] = Table.BLIND_INCREMENTS[self._blind_index]

    def post_smallblind(self, player):
        self.player_bet(player, self._smallblind)
        player.playedthisround = False

    def post_bigblind(self, player):
        self.player_bet(player, self._bigblind)
        player.playedthisround = False
        self._lastraise = self._bigblind

    def player_bet(self, player, total_bet):
        # relative_bet is how much _additional_ money is the player betting this turn, on top of what they have already contributed
        # total_bet is the total contribution by player to pot in this round
        relative_bet = min(player.stack, total_bet - player.currentbet)
        player.bet(relative_bet + player.currentbet)

        self._totalpot += relative_bet
        self._tocall = max(self._tocall, relative_bet)
        self._lastraise = max(self._lastraise, relative_bet  - self._lastraise)

    def _first_to_act(self, players):
        if self._round == 0 and len(players) == 2:
            return self._next(sorted(players + [self._seats[self._button]], key=lambda x:x.get_seat()), self._seats[self._button])
        try:
            first = [player for player in players if player.get_seat() > self._button][0]
        except IndexError:
            first = players[0]
        return first

    def _next(self, players, current_player):
        idx = players.index(current_player)
        return players[(idx+1) % len(players)]

    def deal(self):
        for player in self._seats:
            if player.playing_hand:
                player.hand = self._deck.draw(2)

    def flop(self):
        self._discard.append(self._deck.draw(1)) #burn
        self.community = self._deck.draw(3)

    def turn(self):
        self._discard.append(self._deck.draw(1)) #burn
        self.community.append(self._deck.draw(1))

    def river(self):
        self._discard.append(self._deck.draw(1)) #burn
        self.community.append(self._deck.draw(1))

    def add_player(self, host, port, playerID, name, stack):
        if playerID not in self._player_dict:
            new_player = Player(host, port, playerID, name, stack)
            new_player.playing_hand = True # default to have new players start playing
            for i,player in enumerate(self._seats):
                if player.emptyplayer:
                    self._seats[i] = new_player
                    new_player.set_seat(i)
                    break
            self._player_dict[playerID] = new_player

    def remove_player(self, playerID):
        try:
            if playerID in self._player_dict:
                self._seats.remove(self._player_dict[playerID])
                del self._player_dict[playerID]
        except ValueError:
            pass

    def resolve_sidepots(self, players_playing, allinflag = False):
        players = [p for p in players_playing if p.currentbet != 0]

        # catch recursion
        if not players and not allinflag:
            self._current_sidepot -= 1
            return
        elif not players:
            return

        smallest_bet = min([p.currentbet for p in players])
        smallest_players_allin = [p for p,bet in zip(players, [p.currentbet for p in players]) if bet == smallest_bet and p.isallin]

        self._side_pots[self._current_sidepot] += smallest_bet*len(players)
        for p in players:
            p.currentbet -= smallest_bet
            if not p.currentbet:
                p.lastsidepot = self._current_sidepot
        if len(players) == 1:
            players[0].refund(players[0].currentbet)
            return
        elif smallest_players_allin:
            self._current_sidepot += 1
            self.resolve_sidepots([p for p in players if p not in smallest_players_allin], bool(smallest_players_allin))
        else:
            for p in players:
                self._side_pots[self._current_sidepot] += p.currentbet

    def new_round(self):
        for player in self._player_dict.values():
            player.currentbet = 0
            player.playedthisround = False
        self._round += 1
        self._tocall = 0
        self._lastraise = 0

    def resolve_game(self, players):
        if len(players)==1:
            players[0].refund(self._totalpot)
            self._totalpot = 0
        else:
            # compute hand ranks
            for player in players:
                player.handrank = self._evaluator.evaluate(player.hand, self.community)

            # trim side_pots to only include the non-empty side pots
            temp_pots = [pot for pot in self._side_pots if pot>0]

            # compute who wins each side pot and pay winners
            for pot_idx,_ in enumerate(temp_pots):
                # find players involved in given side_pot, compute the winner(s)
                pot_contributors = [p for p in players if p.lastsidepot >= pot_idx]
                winning_rank = min([p.handrank for p in pot_contributors])
                winning_players = [p for p in pot_contributors if p.handrank == winning_rank]

                for player in winning_players:
                    split_amount = int(self._side_pots[pot_idx]/len(winning_players))
                    player.refund(split_amount)
                    self._side_pots[pot_idx] -= split_amount

                # any remaining chips after splitting go to the winner in the earliest position
                if self._side_pots[pot_idx]:
                    earliest = self._first_to_act([player for player in winning_players])
                    earliest.refund(self._side_pots[pot_idx])

    def reset(self):
        for player in self._seats:
            if not player.emptyplayer:
                player.reset_hand()
        self._current_sidepot = 0
        self._totalpot = 0
        self._side_pots = [0]*len(self._seats)
        self._deck.shuffle()
        self._button = (self._button + 1) % len(self._seats)
        while not self._seats[self._button].playing_hand:
            self._button = (self._button + 1) % len(self._seats)

    def output_state(self, current_player):
        return {'players':[player.player_state() for player in self._seats],
        'community':self.community,
        'my_seat':current_player.get_seat(),
        'pocket_cards':current_player.hand,
        'pot':self._totalpot,
        'button':self._button,
        'tocall':(self._tocall-current_player.currentbet),
        'stack':current_player.stack,
        'bigblind':self._bigblind,
        'playerID':current_player.playerID,
        'lastraise':self._lastraise,
        'minraise':max(self._bigblind, self._lastraise + self._tocall)}

class TableProxy(object):
    def __init__(self, table):
        self._table = table
        self.server = SimpleXMLRPCServer(("localhost", 8000), logRequests=False, allow_none=True)
        self.server.register_instance(self, allow_dotted_names=True)
        Thread(target=self.server.serve_forever).start()

    def get_table_state(self, playerID):
        return self._table.output_state(table._player_dict.get(playerID, None))

    def add_player(self, host, port, playerID, name, stack):
        self._table.add_player(host, port, playerID, name, stack)

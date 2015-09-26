import time
import uuid
from threading import Thread, Lock
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

from deuces.deuces import Card, Deck, Evaluator
from .player import Player

class Table(object):
    BLIND_INCREMENTS = [[10,25],[25,50],[50,100],[75,150],[100,200],[150,300],[200,400],[300,600],[400,800],[500,10000],[600,1200],[800,1600],[1000,2000]]

    def __init__(self, seats = 8, quiet = False, training = False):
        self._blind_index = 0
        [self._smallblind, self._bigblind] = Table.BLIND_INCREMENTS[0]
        self._deck = Deck()
        self._evaluator = Evaluator()

        self.community = []
        self._round = 0
        self._button = 0
        self._discard = []

        self._side_pots = [0]*seats
        self._current_sidepot = 0 # index of _side_pots
        self._totalpot = 0

        self._tocall = 0
        self._lastraise = 0
        self._number_of_hands = 0

        # fill seats with dummy players
        self._seats = [Player(-1,-1,0,'empty',0,True) for _ in range(seats)]
        self.emptyseats = seats
        self._player_dict = {}

        self.teacher = xmlrpc.client.ServerProxy('http://0.0.0.0:8080')

        self._quiet = quiet
        self._training = training
        self._run_thread = Thread(target = self.run, args=())
        self._run_thread.daemon = True

    def start(self):
        self._run_thread.start()

    def run(self):
        while True:
            self.run_game()

    def run_game(self):
        self.ready_players()
        # for p in self._seats:
        #     print('Player ',p.playerID, ' playing hand: ', p.playing_hand, 'sitting out', p.sitting_out)
        players = [player for player in self._seats if not player.emptyplayer and not player.sitting_out]

        self._number_of_hands = 1

        # start hand if table full
        # if len(players) == len(self._seats):
        [self._smallblind, self._bigblind] = Table.BLIND_INCREMENTS[0]

        # keep playing until there's a single player (shotgun style)
        while(self.emptyseats < len(self._seats)-1):
            # answer = input('Press [enter] to start a game:')
            # if not answer:
            self.start_hand(players)
            self._number_of_hands += 1
            if not self._quiet:
                print('Starting game number: ', self._number_of_hands)
                for p in self._seats:
                    if p.playing_hand:
                        print('Player ',p.playerID, ' stack size: ', p.stack)

            # increment blinds every 15 hands (based on avg hands/hour of 30)
            if (self._number_of_hands % 15) == 0 and self._number_of_hands < 60:
                self.increment_blinds()


            if len([p for p in players if p.playing_hand]) == 1:
                winner = [p for p in players if p.playing_hand][0]
                if self._training:
                    self.teacher.add_winner(winner.server.get_ai_id())
                break

            if self._number_of_hands == 200:
                print('no winner in 200 hands')
                break

    def start_hand(self, players):
        players = [p for p in players if p.playing_hand]
        assert sum([p.stack for p in players]) == 2000*len(self._seats)
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
                self.deal()
            elif self._round == 1:
                self.flop()
            elif self._round == 2:
                self.turn()
            elif self._round ==3:
                self.river()

            folded_players = []
            while not player.playedthisround and len([p for p in players if not p.isallin]) >=1:
                if player.isallin:
                    # print('player ', player.playerID, 'is all in, skipping their turn')
                    player = self._next(players, player)
                    continue
                # print('requesting move from ',player.playerID)
                move = player.server.player_move(self.output_state(player))

                if move[0] == 'call':
                    self.player_bet(player, self._tocall)
                    if not self._quiet:
                        print('Player', player.playerID, move)
                    player = self._next(players, player)
                elif move[0] == 'check':
                    self.player_bet(player, player.currentbet)
                    if not self._quiet:
                        print('Player', player.playerID, move)
                    player = self._next(players, player)
                elif move[0] == 'raise':
                    self.player_bet(player, move[1]+player.currentbet)
                    if not self._quiet:
                        print('Player', player.playerID, move)
                    for p in players:
                        if p != player:
                            p.playedthisround = False
                    player = self._next(players, player)
                elif move[0] == 'fold':
                    player.playing_hand = False
                    folded_player = player
                    if not self._quiet:
                        print('Player', player.playerID, move)
                    player = self._next(players, player)
                    players.remove(folded_player)
                    folded_players.append(folded_player)
                    # break if a single player left
                    if len(players) ==1:
                        break

            player = self._first_to_act(players)
            self.resolve_sidepots(players + folded_players)
            self.new_round()
            if not self._quiet:
                print('totalpot', self._totalpot)
            assert sum([p.stack for p in self._seats]) + self._totalpot == 2000*len(self._seats)

        self.resolve_game(players)
        self.reset()

    def increment_blinds(self):
        self._blind_index = min(self._blind_index+1,len(Table.BLIND_INCREMENTS)-1)
        [self._smallblind, self._bigblind] = Table.BLIND_INCREMENTS[self._blind_index]

    def post_smallblind(self, player):
        if not self._quiet:
            print('player ', player.playerID, 'small blind', self._smallblind)
        self.player_bet(player, self._smallblind)
        player.playedthisround = False

    def post_bigblind(self, player):
        if not self._quiet:
            print('player ', player.playerID, 'big blind', self._bigblind)
        self.player_bet(player, self._bigblind)
        player.playedthisround = False
        self._lastraise = self._bigblind

    def player_bet(self, player, total_bet):
        # relative_bet is how much _additional_ money is the player betting this turn, on top of what they have already contributed
        # total_bet is the total contribution by player to pot in this round
        relative_bet = min(player.stack, total_bet - player.currentbet)
        player.bet(relative_bet + player.currentbet)

        self._totalpot += relative_bet
        self._tocall = max(self._tocall, total_bet)
        if self._tocall >0:
            self._tocall = max(self._tocall, self._bigblind)
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
            for i,player in enumerate(self._seats):
                if player.emptyplayer:
                    self._seats[i] = new_player
                    new_player.set_seat(i)
                    break
            self._player_dict[playerID] = new_player
            self.emptyseats -= 1

    def ready_players(self):
        if len([p for p in self._seats if not p.emptyplayer and p.sitting_out]) == len(self._seats):
            for p in self._seats:
                if not p.emptyplayer:
                    p.sitting_out = False
                    p.playing_hand = True

    def remove_player(self, playerID):
        try:
            idx = self._seats.index(self._player_dict[playerID])
            self._seats[idx] = Player(-1,-1,0,'empty',0,True)
            del self._player_dict[playerID]
            self.emptyseats += 1
        except ValueError:
            pass

    def resolve_sidepots(self, players_playing):
        players = [p for p in players_playing if p.currentbet]
        if not self._quiet:
            print('current bets: ', [p.currentbet for p in players])
            print('playing hand: ', [p.playing_hand for p in players])
        if not players:
            return
        try:
            smallest_bet = min([p.currentbet for p in players if p.playing_hand])
        except ValueError:
            for p in players:
                self._side_pots[self._current_sidepot] += p.currentbet
                p.currentbet = 0
            return

        smallest_players_allin = [p for p,bet in zip(players, [p.currentbet for p in players]) if bet == smallest_bet and p.isallin]

        for p in players:
            self._side_pots[self._current_sidepot] += min(smallest_bet, p.currentbet)
            p.currentbet -= min(smallest_bet, p.currentbet)
            p.lastsidepot = self._current_sidepot

        if smallest_players_allin:
            self._current_sidepot += 1
            self.resolve_sidepots(players)
        if not self._quiet:
            print('sidepots: ', self._side_pots)

    def new_round(self):
        for player in self._player_dict.values():
            player.currentbet = 0
            player.playedthisround = False
        self._round += 1
        self._tocall = 0
        self._lastraise = 0

    def resolve_game(self, players):
        # print('Community cards: ', end='')
        # Card.print_pretty_cards(self.community)
        if len(players)==1:
            players[0].refund(sum(self._side_pots))
            # print('Player', players[0].playerID, 'wins the pot (',sum(self._side_pots),')')
            self._totalpot = 0
        else:
            # compute hand ranks
            for player in players:
                player.handrank = self._evaluator.evaluate(player.hand, self.community)

            # trim side_pots to only include the non-empty side pots
            temp_pots = [pot for pot in self._side_pots if pot>0]

            # compute who wins each side pot and pay winners
            for pot_idx,_ in enumerate(temp_pots):
                # print('players last pots', [(p.playerID, p.lastsidepot) for p in players])

                # find players involved in given side_pot, compute the winner(s)
                pot_contributors = [p for p in players if p.lastsidepot >= pot_idx]
                winning_rank = min([p.handrank for p in pot_contributors])
                winning_players = [p for p in pot_contributors if p.handrank == winning_rank]

                for player in winning_players:
                    split_amount = int(self._side_pots[pot_idx]/len(winning_players))
                    if not self._quiet:
                        print('Player', player.playerID, 'wins side pot (',int(self._side_pots[pot_idx]/len(winning_players)),')')
                    player.refund(split_amount)
                    self._side_pots[pot_idx] -= split_amount

                # any remaining chips after splitting go to the winner in the earliest position
                if self._side_pots[pot_idx]:
                    earliest = self._first_to_act([player for player in winning_players])
                    earliest.refund(self._side_pots[pot_idx])

    def reset(self):
        for player in self._seats:
            if not player.emptyplayer and not player.sitting_out:
                player.reset_hand()
        self.community = []
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
        self.server = SimpleXMLRPCServer(('0.0.0.0', 8000), logRequests=False, allow_none=True)
        self.server.register_instance(self, allow_dotted_names=True)
        Thread(target=self.server.serve_forever).start()

    def get_table_state(self, playerID):
        return self._table.output_state(table._player_dict.get(playerID, None))

    def add_player(self, host, port, playerID, name, stack):
        self._table.add_player(host, port, playerID, name, stack)

    def remove_player(self, playerID):
        self._table.remove_player(playerID)

    def run_game(self):
        self._table.run_game()

    def run_forever(self):
        self._table.start()

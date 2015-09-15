import random
import uuid

from threading import Thread, Lock
from xmlrpc.server import SimpleXMLRPCServer

from .table import Table, TableProxy
from .playercontrol import PlayerControl, PlayerControlProxy

class Teacher(object):
    def __init__(self, seats, quiet = False):
        self.table = TableProxy(Table(seats, quiet, True))
        self.players = []

        self.log_file = 'hof_id.log'

        # check/call bot
        self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+1, 1, True, 1)))
        # check/call bot
        self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+2, 2, True, 2)))
        # neural network bots
        for i in range(3,seats+1):
            self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+i, i, True, 0)))

        # populate hof
        with open(self.log_file) as f:
            self.hof = f.read().splitlines()

        self.test_pool = []
        # add 1000 random hof networks to test pool
        for _ in range(min(1000, len(self.hof))):
            self.test_pool.append(random.choice(self.hof))
        # fill up the rest of the pool (to 2000) with random networks
        for _ in range(len(self.test_pool), 2000):
            self.test_pool.append(str(uuid.uuid4()))
        random.shuffle(self.test_pool)

        # self.winners = []

        self._run_thread = Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def run(self):
        while self.test_pool:
            self.reset_game()
            self.table.run_game()

    def add_winner(self, winner_uuid):
        if winner_uuid not in [-1, None, 1,2,3]:
            self.log_id(winner_uuid)
            # self.winners.append(winner_uuid)
            for p in self.players:
                if p.get_ai_id() == winner_uuid:
                    p.save_ai_state()

    def reset_game(self):
        for p in self.players:
            if p.get_ai_id() not in [-1, None, 1,2,3]:
                p.rejoin_new(self.test_pool.pop())
            else:
                p.rejoin()

    def log_id(self, ai_id):
            with open(self.log_file, 'ab') as f:
                f.write(bytes(ai_id +'\n', 'UTF-8'))

class TeacherProxy(object):
    def __init__(self, teacher):
        self._quit = False

        self._teacher = teacher
        self.server = SimpleXMLRPCServer(('0.0.0.0', 8080), logRequests=False, allow_none=True)
        self.server.register_instance(self, allow_dotted_names=True)
        Thread(target = self.run).start()

    def run(self):
        while not self._quit:
            self.server.handle_request()

    def add_winner(self, winner_uuid):
        self._teacher.add_winner(winner_uuid)

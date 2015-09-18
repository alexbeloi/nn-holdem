import random
import uuid

from collections import OrderedDict
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
        self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+2, 2, True, 2)))
        # random bot
        self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+3, 3, True, 3)))
        # neural network bots
        for i in range(4,seats+2):
            self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+i, i, True, 0)))

        # populate hof
        with open(self.log_file) as f:
            self.hof = f.read().splitlines()

        # create test pool
        self.test_pool = []
        self.populate_pool(100,200)

        self.fitness_dic = OrderedDict([(p,0) for p in self.test_pool])


        self._run_thread = Thread(target = self.run, args=())
        self._run_thread.daemon = True
        self._run_thread.start()

    def run(self):
        print('HoF size:', len(self.hof))
        temp = self.test_pool.pop()
        while len(self.test_pool)>=6:
            self.reset_game()
            self.table.run_game()
            self.print_dic()
            print('test pool size: ', len(self.test_pool))
        print('Done with this batch of subjects, saving fitness')
        self.save_dic()

    def save_dic(self):
        self.fitness_dic = OrderedDict(sorted(self.fitness_dic.items(), key=lambda t: t[1]))
        with open(self.log_file, 'ab') as f:
            for p in self.fitness_dic:
                f.write(bytes( str(self.fitness_dic[p]) + ' ' + p + '\n', 'UTF-8'))

    def print_dic(self):
        for p in self.fitness_dic:
            print(p,':',self.fitness_dic[p])


    def populate_pool(self, n_hof, m_total):
        # add n_hof random hof networks to test pool
        for _ in range(min(n_hof, len(self.hof))):
            self.test_pool.append(random.choice(self.hof))
        # fill up the rest of the pool (to m_total) with random networks
        for _ in range(len(self.test_pool), m_total):
            self.test_pool.append(str(uuid.uuid4()))
        # shuffle test_pool
        random.shuffle(self.test_pool)

    def add_winner(self, winner_uuid):
        # if winner_uuid not in [-1, None, 1,2,3]:
        #     self.log_id(winner_uuid)
            # self.winners.append(winner_uuid)
        for p in self.players:
            if p.get_ai_id() not in [None,1,2,3,'1','2','3']:
                if p.get_ai_id() != winner_uuid:
                    self.fitness_dic[str(p.get_ai_id())] -= 1
                elif p.get_ai_id() == winner_uuid:
                    p.save_ai_state()
                    self.fitness_dic[str(p.get_ai_id())] += 2
                    self.test_pool.append(winner_uuid)
                    random.shuffle(self.test_pool)

    def reset_game(self):
        for p in self.players:
            if p.get_ai_id() not in [-1, None, 1,2,3]:
                p.rejoin_new(self.test_pool.pop())
            else:
                p.rejoin()

    def log_id(self, ai_id):
        with open(self.log_file, 'ab') as f:
            f.write(bytes( str(self.fitness_dic[ai_id]) + ' ' + ai_id + '\n', 'UTF-8'))

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

import numpy as np
import random
import uuid

from collections import OrderedDict
from threading import Thread, Lock
from xmlrpc.server import SimpleXMLRPCServer

from .table import Table, TableProxy
from .nn import NeuralNetwork
from .playercontrol import PlayerControl, PlayerControlProxy

class Teacher(Thread):
    def __init__(self, seats, n_hof, n_total, n_epochs, quiet = False):
        super(Teacher, self).__init__()

        self.seats = seats
        self.n_hof = n_hof
        self.n_total = n_total
        self.n_epochs = n_epochs
        self.table = TableProxy(Table(seats, quiet, True))
        self.players = []

        self.log_file = 'hof_id.log'
        self.fitness_log = 'fitness.log'

        self.add_checkcallbot()
        self.add_randombot()
        self.add_nncontrollers()

        # self._run_thread = Thread(target = self.run, args=())
        # self._run_thread.daemon = True
        # self._run_thread.start()

    def run(self):
        epoch = 0
        while epoch < self.n_epochs:
            # populate hall of fame
            with open(self.log_file) as f:
                self.hof = f.read().splitlines()

            # create test pool
            self.create_test_pool()
            self.winner_pool = []

            print('HoF size:', len(self.hof))
            print('Test pool size: ', len(self.test_pool))

            while len(self.test_pool)+len(self.winner_pool) >= 6:
                while len(self.test_pool) >= 6:
                    self.reset_game()
                    self.table.run_game()
                    # self.print_dic()
                    print('Test pool size: ', len(self.test_pool))
                print('Adding winners to test pool')
                self.test_pool += self.winner_pool
                self.winner_pool = []
            print('Done with this batch of subjects, saving fitness')
            self.save_dic()
            epoch += 1

        self.consolodate_fitness()
        self.print_fittest(10)

    def create_test_pool(self):
        self.test_pool = []
        self.populate_pool(self.n_hof, self.n_hof, self.n_total)
        self.fitness_dic = OrderedDict([(p,0) for p in self.test_pool])

    def consolodate_fitness(self):
        with open(self.fitness_log, 'r+') as f:
            fit_list = [line.strip().split(' ') for line in open(self.fitness_log)]
            temp_dic = dict([(item[1], 0) for item in fit_list])
            for item in fit_list:
                temp_dic[item[1]] += int(item[0])
            f.seek(0)
            for k,v in temp_dic.items():
                f.write(str(v) + ' ' + str(k) + '\n')
            f.truncate()

    def print_fittest(self, n):
        fit_list = [line.strip().split(' ') for line in open(self.fitness_log)]
        fit_sorted = sorted(fit_list, key=lambda item: int(item[0]))
        print('Top ', n, 'fittest networks:')
        for i in range(1,n+1):
            print(fit_sorted[-i])

    def save_dic(self):
        self.fitness_dic = OrderedDict(sorted(self.fitness_dic.items(), key=lambda t: t[1]))
        with open(self.log_file, 'ab') as f:
            for p in self.fitness_dic:
                if self.fitness_dic[p]>0:
                    f.write(bytes(str(p) + '\n', 'UTF-8'))
        with open(self.fitness_log, 'ab') as f:
            for p in self.fitness_dic:
                f.write(bytes( str(self.fitness_dic[p]) + ' ' + p + '\n', 'UTF-8'))

    def print_dic(self):
        for p in self.fitness_dic:
            print(p,':',self.fitness_dic[p])

    def populate_pool(self, n_hof, n_children, n_random):
        self.add_hof(n_hof)
        self.add_children(n_children)
        self.add_random(n_random)
        # shuffle test_pool
        random.shuffle(self.test_pool)

    def add_hof(self, n):
        for _ in range(min(n, len(self.hof))):
            self.test_pool.append(random.choice(self.hof))

    def add_random(self, n):
        for _ in range(n):
            self.test_pool.append(str(uuid.uuid4()))

    def add_children(self, n):
        for _ in range(n):
            p1,p2 = random.sample(self.hof, 2)
            self.test_pool.append(str(self.child(p1, p2)))

    def add_winner(self, winner_uuid):
        for p in self.players:
            if p.get_ai_id() not in [None,1,2,3,'1','2','3']:
                if p.get_ai_id() != winner_uuid:
                    self.fitness_dic[str(p.get_ai_id())] -= 1
                elif p.get_ai_id() == winner_uuid:
                    p.save_ai_state()
                    self.fitness_dic[str(p.get_ai_id())] += 2
                    self.winner_pool.append(winner_uuid)
                    random.shuffle(self.test_pool)

    def child(self, p1, p2):
        child_uuid = uuid.uuid4()

        weight1 = np.load(NeuralNetwork.SAVE_DIR + p1 + '_weights.npy')
        weight2 = np.load(NeuralNetwork.SAVE_DIR + p2 + '_weights.npy')
        biases1 = np.load(NeuralNetwork.SAVE_DIR + p1 + '_biases.npy')
        biases2 = np.load(NeuralNetwork.SAVE_DIR + p2 + '_biases.npy')

        child_weights = average_arrays(weight1, weight2)
        child_biases = average_arrays(biases1, biases2)

        np.save(NeuralNetwork.SAVE_DIR + 'children/' + str(child_uuid) + '_weights.npy', child_weights)
        np.save(NeuralNetwork.SAVE_DIR + 'children/' + str(child_uuid) + '_biases.npy', child_biases)

        return child_uuid

    def reset_game(self):
        for p in self.players:
            if p.get_ai_id() not in [-1, None, 1,2,3]:
                p.rejoin_new(self.test_pool.pop())
            else:
                p.rejoin()

    def add_checkcallbot(self):
        self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+2, 2, True, 2)))

    def add_randombot(self):
        # random bot
        self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+3, 3, True, 3)))

    def add_nncontrollers(self):
        for i in range(4,self.seats+2):
            self.players.append(PlayerControlProxy(PlayerControl('localhost', 8000+i, i, True, 0)))


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

def average_arrays(weights1, weights2):
    for w1,w2 in zip(weights1,weights2):
        assert w1.shape == w2.shape
    child = [np.zeros(w.shape) for w in weights1]
    for w1,w2,w3 in zip(weights1,weights2,child):
        for a1,a2,a3 in zip(w1,w2,w3):
            for b1,b2,b3 in zip(a1,a2,a3):
                r1 = (1+np.random.randn())/2
                r2 = (1+np.random.randn())/2
                b3 = r1*b1 + r2*b2
    return child

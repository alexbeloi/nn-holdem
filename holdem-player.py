import argparse
import threading
import xmlrpc.client
import time

# table_spec['player'][#] is tuple ((int) stack, (bool) playing, (bool) betting)
def my_state(table_spec):
    players = table_spec.get('players', None)
    pot = table_spec.get('pot', None)
    position = table_spec.get('position', None)



class PlayerControl(threading.Thread)
    def __init__(self, threadID, name, stack=100000, playing=True, host, port):
        super(Player, self).__init__()
        address = "http://%s:%s" % (host, port)
        self._server = xmlrpc.client.ServerProxy(address)
        self.daemon = True
        self._name = name
        self._threadID = threadID

        self._hand = []
        self._stack =  stack

    def run(self):
        self._server.add_player(self._threadID, self._name, self._stack)
        while True:
            table_state = self._server.get_table_state()
            if not table_state:
                print("not in hand... waiting")
                time.sleep(10)
                continue

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument("num_players", type=int, default=1)
    parser.add_argument("host", type=str, default="localhost")
    parser.add_argument("port", type=str, default="8000")
    args = parser.parse_args()

    #replace 1 with a uniquely generated id
    player = Player(1, "Alice", args.host, args.port)
    player.start()
    player.join()

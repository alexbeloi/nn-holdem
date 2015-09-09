import argparse
import threading
import xmlrpc.client
import time
import math
import sys
import holdem
import numpy as np
from nn import NeuralNetwork

from deuces.deuces import Card, Deck, Evaluator
from xmlrpc.server import SimpleXMLRPCServer



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("id", type=int, default="2")
    parser.add_argument('--ai', dest='ai', action='store_true')
    parser.add_argument('--no-ai', dest='ai', action='store_false')
    args = parser.parse_args()

    player = PlayerControl("localhost", 8001+args.id, args.id, args.ai)
    player_proxy = PlayerProxy(player)

    server = SimpleXMLRPCServer(("localhost", 8001+args.id), logRequests=False, allow_none=True)
    server.register_instance(player_proxy, allow_dotted_names=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

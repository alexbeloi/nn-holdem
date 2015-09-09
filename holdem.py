import argparse
import threading
import xmlrpc.client
import sys
import time
import random

from deuces.deuces import Card, Deck, Evaluator
from holdem import Table, TableProxy
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler


if __name__ == '__main__':

    print("Welcome to the Texas Holdem table, how many seats would you like at this table? (default=8)")
    # default_yesno = input("default configuration? (y/n) ")
    default_yesno = 'y'
    if default_yesno[0] == 'y':
        table = Table("0.0.0.0", 8000)
    else:
        seats = input("Number of seats: ")

        print("Would you like to play with blinds or antes? (default=blinds)")
        print("1) Blinds")
        print("2) Antes")
        blind_or_ante = input("Choose your option: ")
        if blind_or_ante == 1:
            blinds = True
            print("How large should the small-blind/big-blind be? (default = 10/25)")
            print("1) 10/25")
            print("2) 25/50")
            print("3) 50/100")
            print("4) 100/200")
            blind_size = input("Choose your option: ")
            if blind_size == 1:
                sb = 10
                bb = 25
            elif blind_size == 2:
                sb = 25
                bb = 50
            elif blind_size == 3:
                sb = 50
                bb = 100
            elif blind_size == 4:
                sb = 100
                bb = 200
            else:
                print("Invalid input, defaulting to 10/25 blinds.")
                sb = 10
                bb = 25
        elif blind_or_ante == 2:
            blinds = False
            print("How big should the antes be? (default=50)")
            print("1) 10")
            print("2) 25")
            print("3) 50")
            print("4) 100")
            ante_size = input("Choose your option: ")
            if ante_size == 1:
                ante_ammount = 10
            elif ante_size == 2:
                ante_ammount = 25
            elif ante_size == 3:
                ante_ammount = 50
            elif ante_size == 4:
                ante_ammount = 100
            else:
                print("Invalid option, defaulting to ante size = 50")
                ante_ammount = 50
        else:
            print("Invalid input, defaulting to 10/25 blinds.")
            blinds = True
            sb = 10
            bb = 25

        try:
            table = Table(seats, blinds, sb, bb, args.host, args.port)
        except TypeError:
            table = Table(blinds, sb, bb, args.host, args.port)

    table_proxy = TableProxy(table)

    server = SimpleXMLRPCServer(("localhost", 8000), logRequests=False, allow_none=True)
    server.register_instance(table_proxy, allow_dotted_names=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        server.server_close()
        sys.exit(0)

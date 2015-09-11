from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy
import time

seats = 8
# start an table with 8 seats in quiet mode
t = Table(seats, True)
tp = TableProxy(t)

j=0
while True:
    while t.emptyseats == seats:
        # check/fold bot
        p = PlayerControl("localhost", 8000+1+8*j, 1+8*j, True, 1)
        pp = PlayerControlProxy(p)
        # check/call bot
        p = PlayerControl("localhost", 8000+2+8*j, 2+8*j, True, 2)
        pp = PlayerControlProxy(p)
        # random bot
        p = PlayerControl("localhost", 8000+3+8*j, 3+8*j, True, 3)
        pp = PlayerControlProxy(p)

        # fill the rest of the table with neural network bots
        for i in range(4,seats+1):
            p = PlayerControl("localhost", 8000+i+8*j, i+8*j, True, 0)
            pp = PlayerControlProxy(p)

        time.sleep(1)
        j += 1
    time.sleep(1)

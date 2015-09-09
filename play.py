from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy

seats = 8
# start an table with 8 seats
t = Table(seats)
tp = TableProxy(t)

# controller for human meat bag
h = PlayerControl("localhost", 8001, 1, False)
hp = PlayerControlProxy(h)

print('starting ai players')
# fill the rest of the table with ai players
for i in range(2,seats+1):
    p = PlayerControl("localhost", 8000+i, i, True)
    pp = PlayerControlProxy(p)

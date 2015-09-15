from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy, Teacher, TeacherProxy
import time

seats = 8
# # start an table with 8 seats in quiet mode
# t = Table(seats, True)
# tp = TableProxy(t)
#
# while t.emptyseats == seats:
#     # check/fold bot
#     p = PlayerControl("localhost", 8000+1, 1, True, 1)
#     pp = PlayerControlProxy(p)
#     # check/call bot
#     p = PlayerControl("localhost", 8000+2, 2, True, 2)
#     pp = PlayerControlProxy(p)
#     # random bot
#     p = PlayerControl("localhost", 8000+3, 3, True, 3)
#     pp = PlayerControlProxy(p)
#
#     # fill the rest of the table with neural network bots
#     for i in range(4,seats+1):
#         p = PlayerControl("localhost", 8000+i, i, True, 0)
#         pp = PlayerControlProxy(p)
#
#     time.sleep(1)

teacher = Teacher(seats, True)
teacher_proxy = TeacherProxy(teacher)

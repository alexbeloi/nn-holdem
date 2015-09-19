from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy, Teacher, TeacherProxy
import time

seats = 8

teacher = Teacher(seats, 2000, 2000, True)
teacher_proxy = TeacherProxy(teacher)

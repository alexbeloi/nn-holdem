from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy, Teacher, TeacherProxy
import time

seats = 8

teacher = Teacher(seats, 2000, 1000, False)
teacher_proxy = TeacherProxy(teacher)

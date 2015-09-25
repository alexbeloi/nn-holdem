from holdem import Table, TableProxy, PlayerControl, PlayerControlProxy, Teacher, TeacherProxy
import argparse
import time

seats = 8

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pool_size', type=int, default=100)
    parser.add_argument('epochs', type=int, default=1)
    parser.add_argument('--quiet', dest='quiet', action='store_true')
    parser.set_defaults(quiet=False)
    args = parser.parse_args()

    teacher = Teacher(seats, int(args.pool_size/3), args.pool_size, args.epochs, args.quiet)
    teacher_proxy = TeacherProxy(teacher)

    teacher.start()
    teacher.join()

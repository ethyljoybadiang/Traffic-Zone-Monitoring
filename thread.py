from threading import Thread
from time import sleep
class Test(Thread):
    def run(self):
        for j in range(5):
            print("Thread 1")
            sleep(0.5)
class Test2(Thread):
    def run(self):
        for j in range(5):
            print("Thread 2")
            sleep(0.5)
t1 = Test()
t2 = Test2()
t1.start()
t2.start()
t1.join()
t2.join()
print("Both threads have finished")
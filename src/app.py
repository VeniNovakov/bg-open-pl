import bgopl

meet = bgopl.read_results("sept.xlsx")

class_lifter= meet.by_class();

for wclass, lifters in meet.by_class():
    print(wclass)
    for lifter in lifters:
        print(lifter.describe())
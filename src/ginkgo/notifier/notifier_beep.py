import os


def beep(freq=2000.7, repeat=5, delay=20, length=30):
    try:
        os.system(f"beep -f {freq} -r {repeat} -d {delay} -l {length}")
    except Exception as e:
        print(e)

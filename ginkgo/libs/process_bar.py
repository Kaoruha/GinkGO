import tqdm
import time

# for i in tqdm.tqdm(range(1000)):
#     time.sleep(.1)
#     #do something
#     pass

pbar = tqdm.tqdm(["a", "b", "c", "d"])
for char in pbar:
    time.sleep(1)
    # TODO TASK
    pbar.set_description("processing {}".format(char))

pb = tqdm.tqdm(range(100))

# TODO 用装饰器封装一层 拿来用
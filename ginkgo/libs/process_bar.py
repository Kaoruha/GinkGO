import time
    
def sleep(self, sleep_second=2):
    """
    线程等待
    :param sleep_second: 等待的时间（秒）
    :return:
    """
    for i in range(sleep_second * 10):
        t = sleep_second * 10 - (i + 1)
        rate = (i+1)/(sleep_second*10)
        _output.write(f'\r还需等待 {t / 10:.1f} 秒 ' + '|' * int(rate*20) + f' {rate*100:.1f}%')
        time.sleep(.1)
    print('\r\n')
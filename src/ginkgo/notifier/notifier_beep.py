# Upstream: GinkgoNotifier (调用beep/beep_coin方法发送系统提示音)
# Downstream: os系统调用(os.system调用beep命令)
# Role: Beep提示音模块提供系统蜂鸣器提示功能定义beep方法播放系统提示音支持交易系统功能和组件集成提供完整业务支持






import os


def beep(freq=2000.7, repeat=5, delay=20, length=30):
    try:
        os.system(f"beep -f {freq} -r {repeat} -d {delay} -l {length}")
    except Exception as e:
        print(e)

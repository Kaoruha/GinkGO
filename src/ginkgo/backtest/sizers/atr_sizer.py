from ginkgo.backtest.sizers.base_sizer import BaseSizer


class ATRSizer(BaseSizer):
    abstract = False

    def __init__(self, *args, **kwargs):
        super(ATRSizer, self).__init__(*args, **kwargs)

from ginkgo.backtest.sizers.base_sizer import BaseSizer


class ATRSizer(BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, *args, **kwargs):
        super(ATRSizer, self).__init__(*args, **kwargs)

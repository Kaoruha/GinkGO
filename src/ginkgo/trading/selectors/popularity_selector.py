import datetime
from rich.progress import Progress

from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector
from ginkgo.data import get_stockinfos, get_bars


class PopularitySelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "PopularitySelector",
        rank: int = 10,
        span: int = 30,
        *args,
        **kwargs,
    ) -> None:
        super(PopularitySelector, self).__init__(name, *args, **kwargs)
        self.rank = rank
        self.span = span
        self._interested = []
        self.interval = 10  # Interval between 2 picks.
        self._last_pick = None  # Date of last picking.

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        # TODO
        # if self.portfolio is not None:
        # self._now = self.advance_time(self.portfolio.now)

        if self.now is None:
            self.log("ERROR", "No date set. skip picking.")
            return []

        if self._last_pick is None:
            self._last_pick = self._now

        if self.now - self._last_pick < datetime.timedelta(days=self.interval):
            if len(self._interested) > 0:
                return self._interested
        else:
            self._last_pick = self.now

        if self.now is None:
            self.log("ERROR", "No date set. skip picking.")
            return self._interested

        from ginkgo.trading.time.clock import now as clock_now
        t0 = clock_now()
        df = get_stockinfos()
        df["sum_volume"] = 0
        df.reset_index(drop=True, inplace=True)
        column_index = df.columns.get_loc("sum_volume")
        date_start = self.now + datetime.timedelta(days=int(self.span * -1))
        count = 0
        self._interested = []
        with Progress() as progress:
            task = progress.add_task("Scan the data", total=df.shape[0])
            for i, r in df.iterrows():
                count += 1
                code = r.code
                tag = ":face_savoring_food:"
                if count % 4 == 0:
                    tag = ":face_with_monocle:"
                elif count % 4 == 1:
                    tag = ":face_savoring_food:"
                elif count % 4 == 2:
                    tag = ":face_with_raised_eyebrow:"
                elif count % 4 == 3:
                    tag = ":face_with_tongue:"
                progress.update(
                    task,
                    advance=1,
                    description=f"{tag} POP Scan [light_coral]{code}[/light_coral]",
                )
                daybar_df = get_bars(code=code, start_date=date_start, end_date=self.now)
                if daybar_df.shape[0] > 0:
                    df.iloc[i, column_index] = daybar_df["volume"].sum()
            t1 = clock_now()
            progress.update(
                task,
                advance=0,
                description=f"POP Scan Cost [light_coral]{t1-t0}[/light_coral]",
            )

        df = df[df["sum_volume"] > 0]
        df = df.sort_values(by="sum_volume", ascending=False)
        if abs(self.rank) > df.shape[0]:
            self.rank = df.shape[0] if self.rank > 0 else -df.shape[0]

        if self.rank > 0:
            df = df.head(abs(self.rank))
        else:
            df = df.tail(abs(self.rank))

        self._interested = df["code"].values
        t1 = clock_now()
        return self._interested

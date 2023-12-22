from ginkgo.backtest.selectors.base_selector import BaseSelector
from ginkgo.data.ginkgo_data import GDATA
import datetime
from rich.progress import Progress


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

    def pick(self) -> list:
        t0 = datetime.datetime.now()
        df = GDATA.get_stock_info_df_cached()
        df["sum_volume"] = 0
        df = df[:500]
        df.reset_index(drop=True, inplace=True)
        column_index = df.columns.get_loc("sum_volume")
        date_start = self.now + datetime.timedelta(days=int(self.span * -1))
        count = 0
        with Progress() as progress:
            task = progress.add_task("Scan the data", total=df.shape[0])
            for i, r in df.iterrows():
                count += 1
                code = r.code
                tag = ":mag:"
                if count % 3 == 0:
                    tag = ":mag:"
                elif count % 3 == 1:
                    tag = ":mag_right:"
                elif count % 3 == 2:
                    tag = ":lollipop:"
                progress.update(
                    task,
                    advance=1,
                    description=f"{tag} POP Scan [light_coral]{code}[/light_coral]",
                )
                # daybar_df = GDATA.get_daybar_df(
                #     code=code, date_start=date_start, date_end=self.now
                # )
                daybar_df = GDATA.get_daybar_df_cached(
                    code=code, date_start=date_start, date_end=self.now
                )
                if daybar_df.shape[0] > 0:
                    df.iloc[i, column_index] = daybar_df["volume"].sum()
            t1 = datetime.datetime.now()
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

        r = df["code"].values
        t1 = datetime.datetime.now()
        return r

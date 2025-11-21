import json
from typing import List, Union
from ginkgo.trading.bases.selector_base import SelectorBase as BaseSelector


class FixedSelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, codes: Union[str, List[str]], *args, **kwargs) -> None:
        super(FixedSelector, self).__init__(name, *args, **kwargs)

        self._interested = []

        # 支持多种输入格式
        if isinstance(codes, list):
            # 直接传入列表
            self._interested = codes
        elif isinstance(codes, str):
            # 传入字符串，尝试解析JSON或逗号分隔
            try:
                # 尝试解析为JSON
                parsed = json.loads(codes)
                if isinstance(parsed, list):
                    self._interested = parsed
                else:
                    self._interested = [parsed]
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，按逗号分隔处理
                self._interested = [code.strip() for code in codes.split(',') if code.strip()]
        else:
            print(f"Warning: FixedSelector received unsupported codes type: {type(codes)}")

        # 确保所有元素都是字符串
        self._interested = [str(code) for code in self._interested]

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        r = self._interested
        self.log("DEBUG", f"Selector:{self.name} pick {r}.")
        return r

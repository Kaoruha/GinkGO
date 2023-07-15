class GinkgoColor(object):
    self.HEADER = "\033[95m"
    self.OKBLUE = "\033[94m"
    self.OKCYAN = "\033[96m"
    self.OKGREEN = "\033[92m"
    self.WARNING = "\033[93m"
    self.FAIL = "\033[91m"
    self.ENDC = "\033[0m"
    self.BOLD = "\033[1m"
    self.UNDERLINE = "\033[4m"

    def red(self, msg) -> str:
        return f"{self.OKCYAN}{msg}{self.ENDC}"

import datetime
from src.libs.ginkgo_logger import GinkgoLogging

datetimenow = datetime.datetime.now().strftime("%Y-%m-%d")
GINKGOLOGGER = GinkgoLogging(
    logger_name="ginkgo_logger", file_name=datetimenow + ".log"
)

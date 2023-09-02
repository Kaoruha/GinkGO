from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MAdjustfactor

GDATA.drop_table(MAdjustfactor)
GDATA.create_table(MAdjustfactor)


GDATA.update_all_cn_adjustfactor_aysnc()

import torch.nn
import matplotlib.pyplot as plt
import sklearn
import pandas as pd
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


# Scope project (Define project)
# Collect Data
# Train model (train, error analysis, iterative improvement)
# Deply in production (deploy, monitor, maintain system)


# 0 GetData
stock_pool = []
observe_window = 4
hold_window = 4
datasets = pd.Dataframe()
# 1 CleanData
x = []
y = []

x_train = []
y_train = []

x_cv = []
y_cv = []

x_test = []
y_test = []
# 2 Choose Architecture
model = torch.nn.Sequential()
# 3 Train
# 4 Plot && Diagnostic
j_train = 0
j_crossvalidate = 0
j_expectation = 0.7

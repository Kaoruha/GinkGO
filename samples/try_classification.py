# Pytorch
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split, Subset

# Sklearn
import sklearn

# For Plotting Learning Curve
from torch.utils.tensorboard import SummaryWriter
import matplotlib.pyplot as plt

# Data
import pandas as pd
import numpy as np
import math

# StockData
from ginkgo.data.ginkgo_mongo import GinkgoMongo
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.config.secure import DATABASE, HOST, PORT, USERNAME, PASSWORD

# MultiProcessing
import threading
import multiprocessing
from multiprocessing import Manager


# utils
import os
import tqdm
import time
import datetime
from ginkgo.libs import GINKGOLOGGER as gl

# Scope project (Define project)
# This is a fucking poc project.
config = {
    "max_process": "all",
    "seed": 25601,
    "lr": 1e-2,
    "momentum": 0.9,
    "epochs": 100000,
    "early_stop": 5280,
    "save_path": "./models/easytest.ckpt",
    "batch_size": 256,
    "test_ratio": 0.4,
    "cv_ratio": 0.3,
    "log_url": "./logs/easy_try/",
}

# Get cpu or gpu device for training.
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {device} device")

# Define Datasets
class AStockDataset(Dataset):
    def __init__(self, x, y=None):
        self.x = torch.FloatTensor(x)
        self.y = torch.FloatTensor(y)

    def __getitem__(self, index):
        if self.y is None:
            return self.x[index]
        else:
            return self.x[index], self.y[index]

    def __len__(self):
        return len(self.x)


# Define model
# Modify Architecture
class NeuralNetwork(nn.Module):
    def __init__(self, input_dim):
        super(NeuralNetwork, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 6),
            nn.LeakyReLU(),
            nn.Linear(6, 12),
            nn.LeakyReLU(),
            nn.Linear(12, 4),
            nn.LeakyReLU(),
            nn.Linear(4, 1),
            nn.LeakyReLU(),
        )

    def forward(self, x):
        x = self.layers(x)
        x = x.squeeze(1)
        return x


writer = SummaryWriter(log_dir=config["log_url"])  # Writer of tensoboard
# Define Train
def train(train_loader, valid_loader, test_loader, model, config, device):
    loss_fn = nn.L1Loss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config["lr"],
    )

    # Create directory of saving models
    if not os.path.isdir("./models"):
        os.mkdir("./models")

    n_epochs = config["epochs"]
    best_loss = math.inf
    step = 0
    early_stop_count = 0

    for i in range(n_epochs):
        model.train()  # Set model to train mode

        loss_record = []

        train_pbar = tqdm.tqdm(train_loader, position=0, leave=True)

        train_pbar.set_description(f"Epoch[{i + 1}/{n_epochs}]")
        train_pbar.set_postfix({"early": early_stop_count})
        for x, y in train_pbar:
            x = x.to(device)
            y = y.to(device)

            pred = model(x)
            # y = y.unsqueeze(1)

            loss = loss_fn(pred, y)

            optimizer.zero_grad()  # Set gradient to zero

            loss.backward()  # Compute gradient(backpropagation)
            optimizer.step()
            step += 1
            loss_record.append(loss.detach().item())
            train_pbar.set_postfix({"loss": loss.detach().item()})

        mean_train_loss = sum(loss_record) / len(loss_record)

        model.eval()  # Set model to evaluation mode
        loss_record = []
        for x, y in valid_loader:
            x = x.to(device)
            y = y.to(device)
            with torch.no_grad():
                pred = model(x)
                pred = pred.unsqueeze(1)
                loss = loss_fn(pred, y)

            loss_record.append(loss.item())

        mean_valid_loss = sum(loss_record) / len(loss_record)

        test_record = []
        for x, y in test_loader:
            x = x.to(device)
            y = y.to(device)
            with torch.no_grad():
                pred = model(x)
                pred = pred.unsqueeze(1)
                loss = loss_fn(pred, y)

            test_record.append(loss.item())

        mean_test_loss = sum(test_record) / len(test_record)

        writer.add_scalars(
            "Loss",
            {
                "Train": mean_train_loss,
                "Valid": mean_valid_loss,
                "Test": mean_test_loss,
            },
            step,
        )
        print(
            f"Epoch[{i + 1}/{n_epochs}] Train: {mean_train_loss:.4f}  Valid: {mean_valid_loss:.4f} Test: {mean_test_loss:.4f}"
        )
        print("\n")

        if mean_valid_loss < best_loss:
            best_loss = mean_valid_loss
            torch.save(model.state_dict(), config["save_path"])
            print(f"Saving model with loss {best_loss:.3f}...")
            early_stop_count = 0
        else:
            early_stop_count += 1

        if early_stop_count >= config["early_stop"]:
            print("\nModel is not improving, so we halt the training session.")
            return


def same_seed(seed):
    """
    Fix random number generator
    """
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def train_valid_split(data_set, valid_ratio, seed):
    """Split provided training data into training set and validation set"""
    if isinstance(data_set, Subset):
        data_set = data_set.dataset.iloc[data_set.indices, :]

    valid_set_size = int(valid_ratio * data_set.shape[0])

    train_set_size = data_set.shape[0] - valid_set_size
    train_set, valid_set = random_split(
        data_set,
        [train_set_size, valid_set_size],
        generator=torch.Generator().manual_seed(seed),
    )
    return (
        train_set.dataset.iloc[train_set.indices, :],
        valid_set.dataset.iloc[valid_set.indices, :],
    )


def predict(test_loader, model, device):
    model.eval()  # Set model to evaluation mode.
    preds = []
    for i in tqdm.tqdm(test_loader):
        i = i.to(device)
        with torch.no_grad():
            pred = model(i)
            preds.append(pred.detach().cpu())
    preds = torch.cat(preds, dim=0).numpy()
    return preds


def split_feature(data):
    x = data.iloc[:, :-1]
    y = data.iloc[:, -1]
    return x, y


def set_pbar_desc(pbar, desc):
    if len(desc) < desc_max:
        desc += " " * (desc_max - len(desc))
    pbar.set_description(desc)


def get_data(q_stocks, q_result, q_data_):
    pid = os.getpid()
    gl.logger.warning(f"Sub Process {pid}..")
    ginkgo_mongo = GinkgoMongo(
        host=HOST, port=PORT, username=USERNAME, password=PASSWORD, database=DATABASE
    )
    drop_index = [
        "code",
        "_id",
        "date",  # TODO
        "adjust_flag",
        "is_st",
        "pre_close",
        "pct_change",
        "turn",
        # "open",
        # "high",
        # "low",
        # "close",
        # "volume",
        # "amount",
        "trade_status",
    ]
    while True:
        if q_stocks.empty():
            gl.logger.critical(f"Pid {pid} End")
            break
        else:
            code = q_stocks.get(block=False)
            q_result.put(code)
            # TODO Something wrong with this code. The number of stocks dismatch the sum.

            df_temp = ginkgo_mongo.get_dayBar_by_mongo(code=code)

            if df_temp.shape[0] <= 0:
                continue

            df_temp.replace(to_replace=r"^\s*$", value=np.nan, regex=True, inplace=True)
            df_temp.drop(labels=drop_index, axis=1, inplace=True)
            df_temp.dropna(
                axis=0,
                inplace=True,
            )
            observe_window = 20
            hold_window = 5
            dimensions = 3

            columns = df_temp.columns

            for i in range(observe_window):
                step = i + 1
                for j in columns:
                    for k in range(dimensions):
                        new_column = j + "_" + str(step) + "pow" + str(k + 1)
                        df_temp[new_column] = df_temp[j].shift(step)
                        df_temp[new_column] = df_temp[new_column].astype(float)
                        df_temp[new_column] = df_temp[new_column] ** (k + 1)
            # Type convert
            for i in df_temp.columns:
                df_temp[i] = df_temp[i].astype(float)

            df_temp["yhat"] = df_temp["close"].copy().shift(-hold_window)
            df_temp["yhat"] = (
                (df_temp["yhat"] - df_temp["high"]) / df_temp["close"] * 100
            )

            # Remove the head and tail
            df_temp = df_temp[observe_window:-observe_window]
            q_data_.put(df_temp)


# 0 Prepare Data

# Filter Code
all_stock = gm.get_all_stockcode_by_mongo()
code_filter = [""]
name_filter = [""]

code_pool = all_stock["code"]
code_pool = code_pool[1000:1010]

# Set Cores
gl.logger.critical(f"Main Process {os.getpid()}..")
start = time.time()
process_num = multiprocessing.cpu_count()
designed_count = config["max_process"]


if not isinstance(designed_count, int):
    if designed_count != "all":
        gl.logger.critical(
            'CPUCores in config is invalid. The options could be numbers or "all"'
        )
        exit()

if designed_count != "all":
    if designed_count < process_num:
        process_num = designed_count
    else:
        gl.logger.warning(
            f"CPUCores in config is {designed_count}, out of current cpu cores limit."
        )
gl.logger.warning(f"Set CPUCores >> {process_num} <<")

q_stocks = Manager().Queue(code_pool.shape[0])
q_result = Manager().Queue(code_pool.shape[0])
q_data = Manager().Queue(code_pool.shape[0])
pbar = tqdm.tqdm(total=code_pool.shape[0], colour="blue", leave=True)
p = multiprocessing.Pool(process_num)
df = pd.DataFrame()

# Define controller thread
def process_pct(q_stocks, q_result):
    count = 0
    while True:
        if q_result.empty() and q_stocks.empty():
            pbar.refresh()
            pbar.clear()
            pbar.close()
            gl.logger.critical(f"Data prepare complete.")
            break
        code = q_result.get()
        pbar.update(1)
        count += 1
        pbar.set_description(f"Geting {code}")


# # Define Process func
# for i in code_pool:
#     q_stocks.put(i)

# # Boot a controller thread
# gl.logger.info(f"Starting Controller thread.")
# controller = threading.Thread(target=process_pct, args=(q_stocks, q_result))
# controller.start()


# for i in range(process_num):
#     p.apply_async(
#         get_data,
#         args=(q_stocks, q_result, q_data),
#     )

# gl.logger.info("Waiting for all subprocesses done...")
# p.close()

# p.join()
# end = time.time()
# controller.join()
# gl.logger.critical(
#     "All Daybar subprocesses done. Tasks runs %0.2f seconds." % (end - start)
# )


# length = 0


# pbar_store = tqdm.tqdm(total=q_data.qsize(), colour="blue", leave=True)
# while True:
#     if q_data.empty():
#         gl.logger.critical(f"Data Transfer Complete.")
#         break
#     df_temp = q_data.get()
#     length += df_temp.shape[0]
#     df = pd.concat([df, df_temp], axis=0)
#     pbar_store.update(1)
#     pbar_store.set_description(f"Concat Dataframe {df.shape}")


# # 1 SplitData
# test_ratio = config["test_ratio"]
# cv_ratio = config["cv_ratio"]
# seed = config["seed"]

# train_data, test_data = train_valid_split(df, test_ratio, seed)
# train_data, valid_data = train_valid_split(train_data, cv_ratio, seed)


# # Select features
# x_train, y_train = split_feature(train_data)
# x_cv, y_cv = split_feature(valid_data)
# x_test, y_test = split_feature(test_data)


# # Normalization

# x_train = nn.functional.normalize(
#     torch.tensor(x_train.to_numpy(), dtype=torch.float32),
#     p=2,
#     dim=0,
#     eps=1e-12,
#     out=None,
# )
# x_cv = nn.functional.normalize(
#     torch.tensor(x_cv.to_numpy(), dtype=torch.float32),
#     p=2,
#     dim=0,
#     eps=1e-12,
#     out=None,
# )
# x_test = nn.functional.normalize(
#     torch.tensor(x_test.to_numpy(), dtype=torch.float32),
#     p=2,
#     dim=0,
#     eps=1e-12,
#     out=None,
# )
# y_train = torch.tensor(y_train.to_numpy(), dtype=torch.float32)
# y_cv = torch.tensor(y_test.to_numpy(), dtype=torch.float32)
# y_test = torch.tensor(y_test.to_numpy(), dtype=torch.float32)


# train_set = AStockDataset(x_train, y_train)
# valid_set = AStockDataset(x_cv, y_cv)
# test_set = AStockDataset(x_test, y_test)


# Fake Data

import random

num = 129921

df = pd.DataFrame({"x": range(num), "yhat": range(num)})
for i, r in df.iterrows():
    df.iloc[i, 1] = df.iloc[i, 0] ** 2
    writer.add_scalar("Sample/Test", df.iloc[i, 1], df.iloc[i, 0])

seed = config["seed"]
test_ratio = config["test_ratio"]
cv_ratio = config["cv_ratio"]


df[0] = nn.functional.normalize(
    torch.tensor(df[0].to_numpy(), dtype=torch.float32),
    p=2,
    dim=0,
    eps=1e-12,
    out=None,
)

train_data, test_data = train_valid_split(df, test_ratio, seed)
train_data, valid_data = train_valid_split(train_data, cv_ratio, seed)


x_train, y_train = split_feature(train_data)
x_cv, y_cv = split_feature(valid_data)
x_test, y_test = split_feature(test_data)

# x_train = nn.functional.normalize(
#     torch.tensor(x_train.to_numpy(), dtype=torch.float32),
#     p=2,
#     dim=0,
#     eps=1e-12,
#     out=None,
# )
# x_cv = nn.functional.normalize(
#     torch.tensor(x_cv.to_numpy(), dtype=torch.float32),
#     p=2,
#     dim=0,
#     eps=1e-12,
#     out=None,
# )
# x_test = nn.functional.normalize(
#     torch.tensor(x_test.to_numpy(), dtype=torch.float32),
#     p=2,
#     dim=0,
#     eps=1e-12,
#     out=None,
# )
x_train = torch.tensor(x_train.to_numpy(), dtype=torch.float32)
x_cv = torch.tensor(x_test.to_numpy(), dtype=torch.float32)
x_test = torch.tensor(x_test.to_numpy(), dtype=torch.float32)
y_train = torch.tensor(y_train.to_numpy(), dtype=torch.float32)
y_cv = torch.tensor(y_test.to_numpy(), dtype=torch.float32)
y_test = torch.tensor(y_test.to_numpy(), dtype=torch.float32)


train_set = AStockDataset(x_train, y_train)
valid_set = AStockDataset(x_cv, y_cv)
test_set = AStockDataset(x_test, y_test)


# Fake Data End.


batch_size = config["batch_size"]
# same_seed(config["seed"])

train_loader = DataLoader(
    train_set, batch_size=batch_size, shuffle=True, pin_memory=True
)
valid_loader = DataLoader(
    valid_set, batch_size=batch_size, shuffle=True, pin_memory=True
)
test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=True, pin_memory=True)


# Start Train

# input_dim = x_train.dataset.shape[1]

input_dim = x_train.size()[1]

print(f"Input: {input_dim}")
model = NeuralNetwork(input_dim=input_dim).to(device)
print("Model Construction:")
print(model)
train(train_loader, valid_loader, test_loader, model, config, device)

# # 4 Plot && Diagnostic
# j_train = 0
# j_crossvalidate = 0
# j_expectation = 0.7

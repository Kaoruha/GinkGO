# Pytorch
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

# Sklearn
import sklearn

# For Plotting Learning Curve
from torch.utils.tensorboard import SummaryWriter
import matplotlib.pyplot as plt

# Data
import pandas as pd
import numpy as np
import math
import os

# StockData
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm

import tqdm
import time

# Scope project (Define project)

# Collect Data
# Train model (train, error analysis, iterative improvement)
# Deply in production (deploy, monitor, maintain system)


# Get cpu or gpu device for training.
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {device} device")

# Define Datasets
class AStockDataset(Dataset):
    def __init__(self, x, y=None):
        if y is None:
            self.y = y
        else:
            self.y = torch.FloatTensor(y.to_numpy())
        self.x = torch.FloatTensor(x.to_numpy())

    def __getitem__(self, idx):
        if self.y is None:
            return self.x[idx]
        else:
            return self.x[idx], self.y[idx]

    def __len__(self):
        return len(self.x)


# Define model
# Modify Architecture
class NeuralNetwork(nn.Module):
    def __init__(self, input_dim):
        super(NeuralNetwork, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 24),
            nn.ReLU(),
            nn.Linear(24, 6),
            nn.ReLU(),
            nn.Linear(6, 1),
        )

    def forward(self, x):
        x = self.layers(x)
        x = x.squeeze(1)
        return x


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
    valid_set_size = int(valid_ratio * data_set.shape[0])
    train_set_size = data_set.shape[0] - valid_set_size
    print(valid_set_size)
    print(train_set_size)
    train_set, valid_set = random_split(
        data_set,
        [train_set_size, valid_set_size],
        generator=torch.Generator().manual_seed(seed),
    )
    return np.array(train_set), np.array(valid_set)


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


def set_pbar_desc(pbar, desc):
    if len(desc) < desc_max:
        desc += " " * (desc_max - len(desc))
    pbar.set_description(desc)


config = {
    "seed": 25601,
    "lr": 1e-3,
    "momentum": 0.9,
    "epochs": 500,
    "early_stop": 100,
    "save_path": "./models/easytest.ckpt",
    "batch_size": 512,
    "test_ratio": 0.4,
    "cv_ratio": 0.3,
}


# 0 GetData
all_stock = gm.get_all_stockcode_by_mongo()
code_filter = [""]
name_filter = [""]

code_pool = all_stock["code"]
code_pool = code_pool[1000:1001]

x = pd.DataFrame()
y = pd.DataFrame()
df = pd.DataFrame()
data_pbar = tqdm.tqdm(code_pool, position=0, leave=True)
time_start = time.time()
desc_max = 25
for code in code_pool:
    desc = f"Get {code}"
    set_pbar_desc(data_pbar, desc)

    df_temp = gm.get_dayBar_by_mongo(code=code)
    if df_temp.shape[0] <= 0:
        continue

    desc = f"Processing {code}"
    set_pbar_desc(data_pbar, desc)
    drop_index = [
        "code",
        "_id",
        "date",  # TODO
        "adjust_flag",
        "is_st",
        "pre_close",
        "pct_change",
        "turn",
    ]

    df_temp.drop(labels=drop_index, axis=1, inplace=True)

    observe_window = 2
    hold_window = 4

    columns = df_temp.columns

    for i in range(observe_window):
        step = i + 1
        for j in columns:
            new_column = j + "-" + str(step)
            df_temp[new_column] = df_temp[j].shift(-step)

    # Deal ""
    df_temp.replace(to_replace=r"^\s*$", value=np.nan, regex=True, inplace=True)
    df_temp.dropna(subset=df_temp.columns, inplace=True)

    # Type convert
    for i in df_temp.columns:
        try:
            df_temp[i] = df_temp[i].astype(float)
        except Exception as e:
            for j in df_temp[i]:
                if j == "":
                    print("fuckme")
                    print(i)
            print(e)

    df_temp["yhat"] = df_temp["close"] - df_temp[f"close-{observe_window}"]

    df_temp = df_temp[observe_window:-observe_window]

    x_temp = df_temp.iloc[:, :-1]
    y_temp = df_temp.iloc[:, -1]
    x = pd.concat([x, x_temp], axis=0)
    y = pd.concat([y, y_temp], axis=0)
    df = pd.concat([df, df_temp], axis=0)
    data_pbar.update(1)


# 3 Train
def split_feature(data):
    x = data.iloc[:, :-1]
    y = data.iloc[:, -1]
    return x, y


def train(train_loader, valid_loader, model, config, device):
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(
        model.parameters(), lr=config["lr"], momentum=config["momentum"]
    )
    writer = SummaryWriter()  # Writer of tensoboard

    # Create directory of saving models
    if not os.path.isdir("./models"):
        os.mkdir("./models")

    n_epochs = config["epochs"]
    best_loss = math.inf
    step = 0
    early_stop_count = 0

    for i in range(n_epochs):
        # Set model to train mode
        model.train()
        loss_record = []

        train_pbar = tqdm.tqdm(train_loader, position=0, leave=True)

        # print("=" * 30)
        # for i in train_pbar:
        #     print(len(i))
        #     print(i[0])
        #     time.sleep(0.2)
        #     print(i[1])
        #     time.sleep(0.2)

        for x, y in train_pbar:
            optimizer.zero_grad()  # Set gradient to zero
            x = x.to(device)
            y = y.to(device)
            pred = model(x)
            pred = pred.unsqueeze(1)
            loss = loss_fn(pred, y)
            print(loss.size())
            loss.backward()  # Compute gradient(backpropagation)
            optimizer.step()
            step += 1
            loss_record.append(loss.detach().item())
            # print(loss.detach().item())
            time.sleep(0.2)
            print("=" * 20)

            train_pbar.set_description(f"Epoch[{i + 1}/{n_epochs}]")
            train_pbar.set_postfix({"loss": loss.detach().item()})

        print("BLOCK")
        time.sleep(10000)
        # for k in loss_record:
        #     print(k)
        #     time.sleep(0.1)

        mean_train_loss = sum(loss_record) / len(loss_record)

        writer.add_scalar("Loss/Train", mean_train_loss, step)

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
        print(f"Epoch[{i+1}/{n_epochs}]")
        print(f"Train_loss: {mean_train_loss:.4f}  Valid_loss: {mean_valid_loss:.4f}")

        writer.add_scalar("Loss/Valid", mean_valid_loss, step)

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


# 1 SplitData
test_ratio = config["test_ratio"]
cv_ratio = config["cv_ratio"]
seed = config["seed"]


train_data, test_data = train_valid_split(df, test_ratio, seed)
train_data, valid_data = train_valid_split(train_data, cv_ratio, seed)


# Select features
x_train, y_train = split_feature(train_data)
x_cv, y_cv = split_feature(valid_data)
x_test, y_test = split_feature(test_data)


print(x_train.shape[1])
model = NeuralNetwork(x_train.shape[1]).to(device)
print(model)

train_set = AStockDataset(x_train, y_train)
valid_set = AStockDataset(x_cv, y_cv)
test_set = AStockDataset(x_test, y_test)


same_seed(config["seed"])
train_loader = DataLoader(
    train_set, batch_size=config["batch_size"], shuffle=True, pin_memory=True
)
valid_loader = DataLoader(
    valid_set, batch_size=config["batch_size"], shuffle=True, pin_memory=True
)
test_loader = DataLoader(
    test_set, batch_size=config["batch_size"], shuffle=True, pin_memory=True
)


train(train_loader, valid_loader, model, config, device)

# 4 Plot && Diagnostic
j_train = 0
j_crossvalidate = 0
j_expectation = 0.7

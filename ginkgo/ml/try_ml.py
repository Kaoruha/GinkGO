# Pytorch
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split

# Sklearn
import sklearn
from sklearn.model_selection import train_test_split

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


# Get cpu or gpu device for training.
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {device} device")


def same_seed(seed):
    """
    Fix random number generator
    """
    torch.backend.cudnn.deterministic = True
    torch.backend.cudnn.benchmark = False
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def predict(test_loader, model, device):
    model.eval() # Set model to evaluation mode.
    preds = []
    for i in tqdm(test_loader):
        i = i.to(device)
        with torch.no_grad():
            pred = model(i)
            preds.append(pred.detach().cpu())
    preds = torch.cat(preds, dim=0).numpy()
    return preds



# Scope project (Define project)
# Collect Data
# Train model (train, error analysis, iterative improvement)
# Deply in production (deploy, monitor, maintain system)


# 0 GetData
stock_pool = []
observe_window = 4
hold_window = 4
datasets = pd.DataFrame()
# 1 CleanData
x = []
y = []

test_ratio = .3
cv_ratio = .3

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_ratio, random_state=1)
x_train, x_cv, y_train, y_cv = train_test_split(x, y, test_size=cv_ratio, random_state=1)


# Define model
# 2 Choose Architecture

class NeuralNetwork(nn.Module):
    def __init__(self, input_dim):
        super(NeuralNetwork, self).__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, 10)
        )

    def forward(self, x):
        x = self.layers(x)
        x = x.squeeze(1)
        return x

model = NeuralNetwork().to(device)
print(model)

# 3 Train
config = {
        'lr':1e-3,
        'momentum':.9,
        'epochs':1000,
        'early_stop':1000,
        'save_path':"./models/easytest.ckpt",
        'batch_size':256
        }

def train(train_loader, valid_loader, model, config, device):
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=config['lr'], momentum=config['momentum'])
    writer = SummaryWriter() # Writer of tensoboard

    # Create directory of saving models
    if not os.path.isdir('./models'):
        os.mkdir('./models')

    n_epochs = config['epochs']
    best_loss = math.inf
    step = 0
    early_stop_count = 0

    for i in n_epochs:
        # Set model to train mode
        model.train()
        loss_record = []

        train_pbar = tqdm(train_loader, position=0, leave=True)
        
        for x, y in train_pbar:
            optimizer.zero_grad() # Set gradient to zero
            x = x.to(device)
            y = y.to(device)
            pred = model(x)
            loss = loss_fn(pred, y)
            loss.backward() # Compute gradient(backpropagation)
            optimizer.step()
            step += 1
            loss_record.append(loss.detach().item())

            train_pbar.set_description(f'Epoch[{i + 1}/{n_epochs}]')
            train_pbar.set_postfix({"loss":loss.detach().item()})

        mean_train_loss = sum(loss_record) / len(loss_record)

        writer.add_scalar("Loss/Train", mean_train_loss, step)


        model.eval() # Set model to evaluation mode
        loss_record = []
        for x, y in valid_loader:
            x = x.to(device)
            y = y.to(device)
            with torch.no_grad():
                pred = model(x)
                loss = loss_fn(pred, y)

            loss_record.append(loss.item())

        mean_valid_loss = sum(loss_record) / len(loss_record)
        print(f'Epoch[{i+1}/{n_epochs}]')
        print(f'Train_loss: {mean_train_loss:.4f}  Valid_loss: {mean_valid_loss:.4f}')

        writer.add_scalar('Loss/Valid', mean_valid_loss, step)


        if mean_valid_loss < best_loss:
            best_loss = mean_valid_loss
            torch.save(model.state_dict(), config['save_path'])
            print(f'Saving model with loss {best_loss:.3f}...')
            early_stop_count = 0
        else:
            early_stop_count += 1

        if early_stop_count >= config['early_stop']:
            print('\nModel is not improving, so we halt the training session.')
            return


# 4 Plot && Diagnostic
j_train = 0
j_crossvalidate = 0
j_expectation = 0.7

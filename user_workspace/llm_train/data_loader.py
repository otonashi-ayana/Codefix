import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from config import DATA_PATH

class SalesDataset(Dataset):
    def __init__(self):
        df = pd.read_csv(DATA_PATH)
        self.X = torch.tensor(df[["feature1", "feature2"]].values, dtype=torch.float32)
        self.y = torch.tensor(df["label"].values, dtype=torch.long)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def get_dataloader(batch_size=2):
    dataset = SalesDataset()
    loader = DataLoader(dataset, batch_size=batch_size)
    return loader

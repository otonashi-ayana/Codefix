import torch
import torch.nn as nn
import torch.optim as optim

from data_loader import get_dataloader
from model import model
from utils import accuracy
import config

def train():
    device = torch.device("cuda")

    dataloader = get_dataloader()
    net = model(config.INPUT_DIM, config.HIDDEN_DIM, config.OUTPUT_DIM)
    net.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=config.LR)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=0.9)
    scheduler.step()

    for epoch in range(config.EPOCHS):
        for i, (x, y) in enumerate(dataloader):
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            outputs = net(x)
            loss = criterion(outputs, y)
            loss.backward()
            optimizer.step()

        print(f"Epoch {epoch+1}, Loss: {loss.item():.4f}, Acc: {accuracy(outputs, y):.3f}")

if __name__ == "__main__":
    train()

import torch

def accuracy(pred, target):
    correct = (pred == target).sum().item()
    total = target.size(0)
    return correct / total

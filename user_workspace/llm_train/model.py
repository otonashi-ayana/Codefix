import torch
import torch.nn as nn
import torch.nn.functional as F

class model(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(model, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)
    
    def forward(self, x):
        x = F.relu(self.fc1(x))
        from torch.autograd import Variable
        x = Variable(x)
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.fc2(x)
        return x
import numpy as np
import torch
from torch import Tensor

from torchays import nn

GPU_ID = 0
device = torch.device('cuda', GPU_ID) if torch.cuda.is_available() else torch.device('cpu')
torch.manual_seed(5)
torch.cuda.manual_seed_all(5)
np.random.seed(5)


class TestNet(nn.Module):
    def __init__(self):
        super(TestNet, self).__init__()
        self.relu = nn.ReLU()
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=8, kernel_size=3, stride=2, padding=1)
        self.bn1 = nn.BatchNorm2d(num_features=8)
        self.conv2 = nn.Conv2d(in_channels=8, out_channels=16, kernel_size=3, stride=2, padding=1)
        self.avg = nn.AvgPool2d(2, 1)
        self.linear = nn.Linear(16, 2)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)

        x = self.conv2(x)
        x = self.avg(x)

        x = self._forward(lambda x: torch.flatten(x, 1), x)

        x = self.linear(x)
        return x

    def forward_graph(self, x, weight_graph: Tensor = None, bias_graph: Tensor = None):
        input_size = self._get_origin_size(x, weight_graph)
        bias_graph = bias_graph.reshape(bias_graph.size(0), -1)
        weight_graph = weight_graph.reshape(weight_graph.size(0), -1, *input_size)
        return weight_graph, bias_graph


net = TestNet().to(device)
data = torch.randn(2, 3, 8, 8).to(device)

net.eval()
print(net(data))

net.graph()
with torch.no_grad():
    output, graph = net(data)
    weight_graph, bias_graph = graph.get("weight_graph"), graph.get("bias_graph")
    print(output)
    for i in range(output.size(0)):
        output = (weight_graph[i] * data[i]).sum(dim=(1, 2, 3)) + bias_graph[i]
        print(output)

import matplotlib.pyplot as plt
import numpy as np
import polytope as pc
import torch

from torchays import nn
from torchays.cpa import CPA

GPU_ID = 0
device = torch.device('cuda', GPU_ID) if torch.cuda.is_available() else torch.device('cpu')
torch.manual_seed(5)
torch.cuda.manual_seed_all(5)
np.random.seed(5)


class TestNet(nn.Module):
    def __init__(self, input_size=(2,)):
        super(TestNet, self).__init__()
        self.relu = nn.ReLU()
        self.fc1 = nn.Linear(input_size[0], 16, bias=True)
        self.fc2 = nn.Linear(16, 16, bias=True)
        self.fc4 = nn.Linear(16, 3, bias=True)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)

        x = self.fc2(x)
        x = self.relu(x)

        x = self.fc4(x)

        return x

    def forward_layer(self, x, depth=-1):
        x = self.fc1(x)
        if depth == 0:
            return x
        x = self.relu(x)
        x = self.fc2(x)
        if depth == 1:
            return x
        x = self.relu(x)
        x = self.fc4(x)
        return x


net = TestNet((2,)).to(device)
au = CPA(device=device)

funcs, regions, points = [], [], []


def handler(point, functions, region):
    points.append(point)
    funcs.append(functions)
    regions.append(region)


num = au.start(net, 1, region_handler=handler)
ax = plt.subplot()
for i in range(num):
    #  to <= 0
    func, region, point = funcs[i], regions[i], points[i]
    # print(f"Func: {func}, area: {area}, point: {point}")
    func = -region.view(-1, 1) * func
    func = func.numpy()
    A, B = func[:, :-1], -func[:, -1]
    p = pc.Polytope(A, B)
    p.plot(
        ax,
        color=np.random.uniform(0.0, 0.95, 3),
        alpha=1.0,
        linestyle='-',
        linewidth=0.2,
        edgecolor='w',
    )

plt.xlim(-1, 1)
plt.ylim(-1, 1)
plt.axis('off')
plt.show()

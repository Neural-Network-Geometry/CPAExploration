from torchays import modules


class TestTNetLinear(modules.AysBaseModule):
    def __init__(self, in_features=2, nNum: tuple = [32, 32, 32], n_classes=2):
        super(TestTNetLinear, self).__init__()
        self.numLayers = len(nNum)
        self.reLUNum = self.numLayers-1
        self.add_module("0", modules.AysLinear(in_features, nNum[0], bias=True))
        self.relu = modules.AysReLU()
        for i in range(self.numLayers-1):
            fc = modules.AysLinear(nNum[i], nNum[i+1], bias=True)
            self.add_module(f"{i+1}", fc)
        self.add_module(f"{self.numLayers}", modules.AysLinear(nNum[-1], n_classes, bias=True))

    def forward(self, x):
        for i in range(self.numLayers):
            x = self._modules[f'{i}'](x)
            x = self.relu(x)
        x = self._modules[f"{self.numLayers}"](x)
        return x

    def forward_graph_Layer(self, x, layer=0):
        assert layer >= 0, "'layer' must be greater than 0."
        for i in range(self.numLayers):
            x = self._modules[f'{i}'](x)
            if layer == i:
                return x
            x = self.relu(x)
        x = self._modules[f"{self.numLayers}"](x)
        return x

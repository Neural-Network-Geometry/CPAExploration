NAME = "Linear-single-bn"
import os
from typing import Dict

import numpy as np
import torch

from dataset import GAUSSIAN_QUANTILES, MOON, RANDOM, simple_get_data
from experiment import Analysis, Experiment
from torchays import nn
from torchays.cpa import Model
from torchays.models import TestTNetLinear
from torchays.nn.modules.batchnorm import BatchNorm1d, BatchNormNone
from torchays.nn.modules.norm import Norm1d

import os

import numpy as np
import torch

from dataset import GAUSSIAN_QUANTILES, MNIST, MNIST_TYPE, MOON, RANDOM, simple_get_data
from experiment import Analysis, Experiment
from torchays import nn
from torchays.models import LeNet, TestResNet, TestTNetLinear

GPU_ID = 0
SEED = 5
NAME = "Linear"
# ===========================================
TYPE = MOON
# ===========================================
# Test-Net
N_LAYERS = [16, 16, 16]
# ===========================================
# Dataset
N_SAMPLES = 1000
DATASET_BIAS = 0
# only GAUSSIAN_QUANTILES
N_CLASSES = 2
# only RANDOM
IN_FEATURES = 2
# is download for mnist
DOWNLOAD = False
# ===========================================
# Training
MAX_EPOCH = 100
SAVE_EPOCH = [100]
BATCH_SIZE = 64
LR = 1e-3
# is training the network.
IS_TRAIN = False
# ===========================================
# Experiment
IS_EXPERIMENT = True
BOUND = (-1, 1)
# the depth of the NN to draw
DEPTH = -1
# the number of the workers
WORKERS = 1
# with best epoch
BEST_EPOCH = False
# ===========================================
# Drawing
# is drawing the region picture. Only for 2d input.
IS_DRAW = True
# is drawing the 3d region picture.
IS_DRAW_3D = False
# is handlering the hyperplanes arrangement.
IS_DRAW_HPAS = False
IS_STATISTIC_HPAS = False
# ===========================================
# Analysis
IS_ANALYSIS = False
# draw the dataset distribution
WITH_DATASET = True
# analysis the batch norm
WITH_BN = True
# ===========================================
# path
TAG = ""
root_dir = os.path.abspath("./")
cache_dir = os.path.join(root_dir, "cache")
if len(TAG) > 0:
    cache_dir = os.path.join(cache_dir, TAG)
save_dir = os.path.join(cache_dir, f"{TYPE}-{N_SAMPLES}-{IN_FEATURES}-{SEED}")


def init_fun():
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    np.random.seed(SEED)


def norm(num_features):
    is_norm = False
    if not is_norm:
        return BatchNormNone(num_features)
    # freeze parameters
    freeze = False
    # set init parameters
    set_parameters = None
    return Norm1d(num_features, freeze, set_parameters)


def _norm(is_bn: bool = True):
    if is_bn:
        return BatchNorm1d
    return norm


def net(n_classes: int) -> Model:
    return TestTNetLinear(
        in_features=IN_FEATURES,
        layers=N_LAYERS,
        name=NAME,
        n_classes=n_classes,
        norm_layer=_norm(WITH_BN),
    )


def dataset(
    save_dir: str,
    type: str = MOON,
    name: str = "dataset.pkl",
):
    def make_dataset():
        if type == MNIST_TYPE:
            mnist = MNIST(root=os.path.join(save_dir, "mnist"), download=DOWNLOAD)
            return mnist, len(mnist.classes)
        return simple_get_data(dataset=type, n_samples=N_SAMPLES, noise=0.2, random_state=5, data_path=os.path.join(save_dir, name), n_classes=N_CLASSES, in_features=IN_FEATURES, bias=DATASET_BIAS)

    return make_dataset


# 当前步数下的, 某一层的bn数据
batch_norm_data: Dict[str, Dict[str, Dict[str, torch.Tensor]]] = dict()


def train_handler(
    net: nn.Module,
    epoch: int,
    step: int,
    total_step: int,
    loss: torch.Tensor,
    acc: torch.Tensor,
    save_dir: str,
):
    step_name = f"{epoch}/{step}"
    current_bn_data = dict()
    for layer_name, module in net._modules.items():
        if "_norm" not in layer_name:
            continue
        # 存储每一个batch下的bn的参数
        module: nn.BatchNorm1d
        parameters: Dict[str, torch.Tensor] = module.state_dict()
        weight = parameters.get("weight").cpu()
        bias = parameters.get("bias").cpu()
        running_mean = parameters.get("running_mean").cpu()
        running_var = parameters.get("running_var").cpu()
        num_batches_tracked = parameters.get("num_batches_tracked").cpu()
        # 计算对应的A_bn和B_bn
        p = torch.sqrt(running_var + module.eps)
        # weight_bn = w/√(var)
        weight_bn = weight / p
        # bias_bn = b - w*mean/√(var)
        bias_bn = bias - weight_bn * running_mean
        save_dict = {
            "weight": weight,
            "bias": bias,
            "running_mean": running_mean,
            "running_var": running_var,
            "num_batches_tracked": num_batches_tracked,
            "weight_bn": weight_bn,
            "bias_bn": bias_bn,
        }
        current_bn_data[layer_name] = save_dict
    batch_norm_data[step_name] = current_bn_data


if __name__ == "__main__":
    root_dir = os.path.abspath("./")
    os.makedirs(save_dir, exist_ok=True)
    device = torch.device('cuda', GPU_ID) if torch.cuda.is_available() else torch.device('cpu')
    if IS_EXPERIMENT:
        exp = Experiment(
            save_dir=save_dir,
            net=net(type=TYPE),
            dataset=dataset(save_dir, type=TYPE),
            init_fun=init_fun,
            save_epoch=SAVE_EPOCH,
            device=device,
        )
        if IS_TRAIN:
            default_handler = train_handler if WITH_BN else None
            exp.train(
                max_epoch=MAX_EPOCH,
                batch_size=BATCH_SIZE,
                train_handler=default_handler,
                lr=LR,
            )
        exp.cpas(
            workers=WORKERS,
            best_epoch=BEST_EPOCH,
            bounds=BOUND,
            depth=DEPTH,
            is_draw=IS_DRAW,
            is_draw_3d=IS_DRAW_3D,
            is_draw_hpas=IS_DRAW_HPAS,
            is_statistic_hpas=IS_STATISTIC_HPAS,
        )
        exp()
        if WITH_BN:
            # batch_norm
            batch_norm_path = os.path.join(exp.get_root(), f"batch_norm.pkl")
            torch.save(batch_norm_data, batch_norm_path)
    if IS_ANALYSIS:
        analysis = Analysis(
            root_dir=save_dir,
            with_dataset=WITH_DATASET,
            with_bn=WITH_BN,
        )
        analysis()

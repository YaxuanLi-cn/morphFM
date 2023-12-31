# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the Apache License, Version 2.0
# found in the LICENSE file in the root directory of this source tree.

from enum import Enum
from typing import Union

import torch
import torch.nn as nn

from .backbones import _make_morphFM_model
from .utils import _DINOV2_BASE_URL, _make_morphFM_model_name


class Weights(Enum):
    IMAGENET1K = "IMAGENET1K"


def _make_morphFM_linear_classification_head(
    *,
    model_name: str = "morphFM_vitl14",
    embed_dim: int = 1024,
    layers: int = 4,
    pretrained: bool = True,
    weights: Union[Weights, str] = Weights.IMAGENET1K,
    **kwargs,
):
    if layers not in (1, 4):
        raise AssertionError(f"Unsupported number of layers: {layers}")
    if isinstance(weights, str):
        try:
            weights = Weights[weights]
        except KeyError:
            raise AssertionError(f"Unsupported weights: {weights}")

    linear_head = nn.Linear((1 + layers) * embed_dim, 1_000)

    if pretrained:
        layers_str = str(layers) if layers == 4 else ""
        url = _DINOV2_BASE_URL + f"/{model_name}/{model_name}_linear{layers_str}_head.pth"
        state_dict = torch.hub.load_state_dict_from_url(url, map_location="cpu")
        linear_head.load_state_dict(state_dict, strict=False)

    return linear_head


class _LinearClassifierWrapper(nn.Module):
    def __init__(self, *, backbone: nn.Module, linear_head: nn.Module, layers: int = 4):
        super().__init__()
        self.backbone = backbone
        self.linear_head = linear_head
        self.layers = layers

    def forward(self, x):
        if self.layers == 1:
            x = self.backbone.forward_features(x)
            cls_token = x["x_norm_clstoken"]
            patch_tokens = x["x_norm_patchtokens"]
            # fmt: off
            linear_input = torch.cat([
                cls_token,
                patch_tokens.mean(dim=1),
            ], dim=1)
            # fmt: on
        elif self.layers == 4:
            x = self.backbone.get_intermediate_layers(x, n=4, return_class_token=True)
            # fmt: off
            linear_input = torch.cat([
                x[0][1],
                x[1][1],
                x[2][1],
                x[3][1],
                x[3][0].mean(dim=1),
            ], dim=1)
            # fmt: on
        else:
            assert False, f"Unsupported number of layers: {self.layers}"
        return self.linear_head(linear_input)


def _make_morphFM_linear_classifier(
    *,
    arch_name: str = "vit_large",
    layers: int = 4,
    pretrained: bool = True,
    weights: Union[Weights, str] = Weights.IMAGENET1K,
    **kwargs,
):
    backbone = _make_morphFM_model(arch_name=arch_name, pretrained=pretrained, **kwargs)

    embed_dim = backbone.embed_dim
    patch_size = backbone.patch_size
    model_name = _make_morphFM_model_name(arch_name, patch_size)
    linear_head = _make_morphFM_linear_classification_head(
        model_name=model_name,
        embed_dim=embed_dim,
        layers=layers,
        pretrained=pretrained,
        weights=weights,
    )

    return _LinearClassifierWrapper(backbone=backbone, linear_head=linear_head, layers=layers)


def morphFM_vits14_lc(
    *, layers: int = 4, pretrained: bool = True, weights: Union[Weights, str] = Weights.IMAGENET1K, **kwargs
):
    """
    Linear classifier (1 or 4 layers) on top of a DINOv2 ViT-S/14 backbone (optionally) pretrained on the LVD-142M dataset and trained on ImageNet-1k.
    """
    return _make_morphFM_linear_classifier(
        arch_name="vit_small", layers=layers, pretrained=pretrained, weights=weights, **kwargs
    )


def morphFM_vitb14_lc(
    *, layers: int = 4, pretrained: bool = True, weights: Union[Weights, str] = Weights.IMAGENET1K, **kwargs
):
    """
    Linear classifier (1 or 4 layers) on top of a DINOv2 ViT-B/14 backbone (optionally) pretrained on the LVD-142M dataset and trained on ImageNet-1k.
    """
    return _make_morphFM_linear_classifier(
        arch_name="vit_base", layers=layers, pretrained=pretrained, weights=weights, **kwargs
    )


def morphFM_vitl14_lc(
    *, layers: int = 4, pretrained: bool = True, weights: Union[Weights, str] = Weights.IMAGENET1K, **kwargs
):
    """
    Linear classifier (1 or 4 layers) on top of a DINOv2 ViT-L/14 backbone (optionally) pretrained on the LVD-142M dataset and trained on ImageNet-1k.
    """
    return _make_morphFM_linear_classifier(
        arch_name="vit_large", layers=layers, pretrained=pretrained, weights=weights, **kwargs
    )


def morphFM_vitg14_lc(
    *, layers: int = 4, pretrained: bool = True, weights: Union[Weights, str] = Weights.IMAGENET1K, **kwargs
):
    """
    Linear classifier (1 or 4 layers) on top of a DINOv2 ViT-g/14 backbone (optionally) pretrained on the LVD-142M dataset and trained on ImageNet-1k.
    """
    return _make_morphFM_linear_classifier(
        arch_name="vit_giant2", layers=layers, ffn_layer="swiglufused", pretrained=pretrained, weights=weights, **kwargs
    )

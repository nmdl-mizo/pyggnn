from typing import Literal, Optional, Union, Any

import torch
from torch import Tensor
import torch.nn as nn
from torch_scatter import scatter

from pyggnn.nn.base import Dense
from pyggnn.utils.resolve import activation_resolver


__all__ = ["Node2Prop1", "Node2Prop2"]


class Node2Prop1(nn.Module):
    """
    The block to compute the global graph proptery from node embeddings.
    In this block, after aggregation, two more Dense layers are calculated.
    This block is used in EGNN.
    """

    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 128,
        out_dim: int = 1,
        activation: Union[Any, str] = "swish",
        aggr: Literal["add", "mean"] = "add",
        **kwargs,
    ):
        """
        Args:
            in_dim (int): number of input dim.
            hidden_dim (int, optional): number of hidden layers dim. Defaults to `128`.
            out_dim (int, optional): number of output dim. Defaults to `1`.
            activation: (str or nn.Module, optional): activation function class or name.
                Defaults to `Swish`.
            aggr (`"add"` or `"mean"`): aggregation method. Defaults to `"add"`.
        """
        super().__init__()

        act = activation_resolver(activation, **kwargs)

        assert aggr == "add" or aggr == "mean"
        self.aggr = aggr
        self.node_transform = nn.Sequential(
            Dense(in_dim, hidden_dim, bias=True, activation_name=activation, **kwargs),
            act,
            Dense(hidden_dim, hidden_dim, bias=True),
        )
        self.output = nn.Sequential(
            Dense(
                hidden_dim,
                hidden_dim,
                bias=True,
                activation_name=activation,
                **kwargs,
            ),
            act,
            Dense(hidden_dim, out_dim, bias=False),
        )

        self.reset_parameters()

    def reset_parameters(self):
        for layer in self.node_transform:
            if hasattr(layer, "reset_parameters"):
                layer.reset_parameters()
        for layer in self.output:
            if hasattr(layer, "reset_parameters"):
                layer.reset_parameters()

    def forward(self, x: Tensor, batch: Optional[Tensor] = None) -> Tensor:
        """
        Compute global property from node embeddings.

        Args:
            x (Tensor): node embeddings shape of (n_node x in_dim).
            batch (Tensor, optional): batch index. Defaults to `None`.

        Returns:
            Tensor: shape of (n_batch x out_dim).
        """
        out = self.node_transform(x)
        out = scatter(out, index=batch, dim=0, reduce=self.aggr)
        return self.output(out)


class Node2Prop2(nn.Module):
    """
    The block to compute the global graph proptery from node embeddings.
    This block contains two Dense layers and aggregation block.
    If set `scaler`, scaling process before aggregation.
    This block is used in SchNet.
    """

    def __init__(
        self,
        in_dim: int,
        hidden_dim: int = 128,
        out_dim: int = 1,
        activation: Union[Any, str] = "shifted_softplus",
        aggr: Literal["add", "mean"] = "add",
        scaler: Optional[nn.Module] = None,
        mean: Optional[Tensor] = None,
        stddev: Optional[Tensor] = None,
        **kwargs,
    ):
        """
        Args:
            in_dim (int): number of input dim.
            hidden_dim (int, optional): number of hidden layers dim. Defaults to `128`.
            out_dim (int, optional): number of output dim. Defaults to `1`.
            activation: (str or nn.Module, optional): activation function class or name.
                Defaults to `shifted_softplus`.
            aggr (`"add"` or `"mean"`): aggregation method. Defaults to `"add"`.
            scaler: (nn.Module, optional): scaler layer. Defaults to `None`.
            mean: (Tensor, optional): mean of the input tensor. Defaults to `None`.
            stddev: (Tensor, optional): stddev of the input tensor. Defaults to `None`.
        """
        super().__init__()
        act = activation_resolver(activation, **kwargs)

        assert aggr == "add" or aggr == "mean"
        self.aggr = aggr
        self.output = nn.Sequential(
            Dense(in_dim, hidden_dim, bias=True, activation_name=activation, **kwargs),
            act,
            Dense(hidden_dim, out_dim, bias=False),
        )
        if scaler is None:
            self.scaler = None
        else:
            if mean is None:
                mean = torch.FloatTensor([0.0])
            if stddev is None:
                stddev = torch.FloatTensor([1.0])
            self.scaler = scaler(mean, stddev)

        self.reset_parameters()

    def reset_parameters(self):
        for layer in self.output:
            if hasattr(layer, "reset_parameters"):
                layer.reset_parameters()

    def forward(self, x: Tensor, batch: Optional[Tensor] = None) -> Tensor:
        """
        Compute global property from node embeddings.

        Args:
            x (Tensor): node embeddings shape of (n_node x in_dim).
            batch (Tensor, optional): batch index. Defaults to `None`.

        Returns:
            Tensor: shape of (n_batch x out_dim).
        """
        out = self.output(x)
        if self.scaler is not None:
            out = self.scaler(out)
        return scatter(out, index=batch, dim=0, reduce=self.aggr)

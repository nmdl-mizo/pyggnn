from typing import Optional

import numpy as np
import torch
from torch import Tensor
import torch.nn as nn


class BaseCutoff(nn.Module):
    """BaseCutoff Network"""

    def __init__(self, cutoff_radi: Optional[float] = None):
        """
        Args:
            cutoff_radi (float, optional): cutoff radious.
        """
        super().__init__()
        self.cutoff_radi = cutoff_radi

    def forward(self, dist: Tensor) -> Tensor:
        """
        forward calculation of CosineNetwork.

        Args:
            dist (Tensor): inter atomic distances shape of (n_edge)

        Returns:
            Tensor: Cutoff values shape of (n_edge)
        """
        raise NotImplementedError


class CosineCutoff(BaseCutoff):
    """CosineCutoff Network"""

    def __init__(self, cutoff_radi: float):
        """
        Args:
            cutoff_radi (float): cutoff radious.
        """
        super().__init__(cutoff_radi)

    def forward(self, dist: Tensor) -> Tensor:
        """
        forward calculation of CosineNetwork.

        Args:
            dist (Tensor): inter atomic distances shape of (n_edge)

        Returns:
            Tensor: Cutoff values shape of (n_edge)
        """
        # Compute values of cutoff function
        cutoffs = 0.5 * (torch.cos(dist * np.pi / self.cutoff_radi) + 1.0)
        # Remove contributions beyond the cutoff radius
        return cutoffs * (dist < self.cutoff_radi).to(dist.dtype)


class EnvelopeCutoff(BaseCutoff):
    """EnvelopeCutoff Network"""

    def __init__(self, cutoff_radi: float, exponent: int = 5):
        """
        Args:
            exponent (int, optional): Order of the envelope function.
                Defaults to `5`.

        Notes:
            reference:
            [1] J. Klicpera et al., arXiv [cs.LG] (2020),
                (available at http://arxiv.org/abs/2003.03123).
        """
        super().__init__(cutoff_radi)
        self.p = exponent + 1

    def forward(self, dist: Tensor) -> Tensor:
        """
        forward calculation of EnvelopeCutoffNetwork.

        Args:
            dist (Tensor): inter atomic distances normalized by cutoff radius
                shape of (n_edge).

        Returns:
            Tensor: Cutoff values shape of (n_edge).
        """
        p = self.p
        # coeffs
        a = -(p + 1) * (p + 2) / 2
        b = p * (p + 2)
        c = -p * (p + 1) / 2
        # calc polynomial
        dist_pow_p0 = dist.pow(p - 1)
        dist_pow_p1 = dist_pow_p0 * dist
        dist_pow_p2 = dist_pow_p1 * dist
        # Remove contributions beyond the cutoff radius
        return (
            1.0 / (dist + 1e-8) + a * dist_pow_p0 + b * dist_pow_p1 + c * dist_pow_p2
        ) * (dist < 1.0).to(dist.dtype)

import torch
import torch.nn.functional as F

class GaussianSmoothedCrossEntropyLoss(torch.nn.Module):
    """Cross entropy with labels smoothed over neighbouring classes using a Gaussian."""

    indices: torch.Tensor

    def __init__(self, num_classes: int, sigma: float):
        """sigma is the standard deviation of the smoothing, in classes."""

        super().__init__()

        self.num_classes = num_classes
        self.sigma = sigma

        self.register_buffer("indices", torch.arange(num_classes, dtype=torch.float32))

    def extra_repr(self) -> str:
        return f"num_classes={self.num_classes}, sigma={self.sigma}"

    def _make_soft_labels(self, target: torch.Tensor) -> torch.Tensor:
        """Builds a normalized Gaussian over the classes, centred on each target."""

        centers = target.float().unsqueeze(1)
        weights = torch.exp(-0.5 * ((self.indices - centers) / self.sigma) ** 2)
        return weights / weights.sum(dim=1, keepdim=True)

    def forward(
            self,
            logits: torch.Tensor,
            target: torch.Tensor,
            ) -> torch.Tensor:
        soft_labels = self._make_soft_labels(target)
        log_probs = F.log_softmax(logits, dim=1)

        return -(soft_labels * log_probs).sum(dim=1).mean()

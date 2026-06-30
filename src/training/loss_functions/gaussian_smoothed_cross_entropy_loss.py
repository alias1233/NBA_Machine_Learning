import torch
import torch.nn.functional as F

class GaussianSmoothedCrossEntropyLoss(torch.nn.Module):
    """
    Cross-entropy loss with Gaussian soft labels.
    Predicting a classification near the true classification is penalized less than predicting one far away.
    """

    indices: torch.Tensor

    def __init__(self, num_classes: int, sigma: float):
        """
        Args:
            num_classes: Total number of classes.
            sigma: Std dev of the Gaussian in class-index units.
        """
        
        super().__init__()

        self.num_classes = num_classes
        self.sigma = sigma

        self.register_buffer("indices", torch.arange(num_classes, dtype=torch.float32))

    def _make_soft_labels(self, target: torch.Tensor) -> torch.Tensor:
        """
        Build a normalized Gaussian distribution over classes for each target.
        """

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
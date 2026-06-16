import torch
from torchvision.models import resnet50, ResNet50_Weights
import torch.nn.functional as F

class Classifier:
    def __init__(self, weights=ResNet50_Weights.DEFAULT, device: str | None = None):
        self.device = torch.device(device) if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.weights = weights
        self.model = resnet50(weights=weights)
        self.model.to(self.device)
        self.model.eval()
        self.preprocess = weights.transforms()

    def predict(self, image, topk: int = 5):
        x = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            probs = F.softmax(logits, dim=1)
            values, indices = torch.topk(probs, k=topk, dim=1)
        return {"probs": probs.cpu(), "topk": {"values": values.cpu(), "indices": indices.cpu()}}
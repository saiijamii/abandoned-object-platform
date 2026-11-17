import hashlib
import math
from typing import Protocol


class ImageEmbedder(Protocol):
    dimension: int

    def embed(self, image_bytes: bytes) -> list[float]: ...


class FakeEmbedder:
    dimension = 32

    def embed(self, image_bytes: bytes) -> list[float]:
        digest = hashlib.sha256(image_bytes).digest()
        values = [((digest[index % len(digest)] / 255) * 2) - 1 for index in range(self.dimension)]
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class ClipEmbedder:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: str = "cpu") -> None:
        try:
            import torch
            from PIL import Image
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as exc:
            raise RuntimeError("Install Phase Six model dependencies: pip install torch transformers pillow") from exc
        self.torch, self.Image = torch, Image
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model = CLIPModel.from_pretrained(model_name).to(device)
        self.model.eval()
        self.device = device
        self.dimension = int(self.model.config.projection_dim)

    def embed(self, image_bytes: bytes) -> list[float]:
        import io
        image = self.Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            values = self.model.get_image_features(**inputs)[0]
        values = values / values.norm()
        return values.detach().cpu().tolist()

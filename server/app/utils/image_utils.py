from PIL import Image
import numpy as np


def preprocess_image(image: Image.Image) -> np.ndarray:
    image = image.convert("RGB")
    image = image.resize((128, 128))
    image = np.array(image)
    image = image.astype("float32")
    image = image / 255
    image = np.expand_dims(image, 0)
    return image

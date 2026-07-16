from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)


def preprocess_image(image: Image.Image) -> np.ndarray:
    logger.debug(f"Original image size: {image.size}, mode: {image.mode}")
    
    image = image.convert("RGB")
    logger.debug(f"After RGB conversion: {image.size}")
    
    image = image.resize((128, 128), Image.Resampling.BILINEAR)
    logger.debug(f"After resize: {image.size}")
    
    image = np.array(image)
    logger.debug(f"After np.array: shape={image.shape}, dtype={image.dtype}")
    
    image = image.astype("float32")
    logger.debug(f"After float32 cast: dtype={image.dtype}")
    
    logger.debug(f"Pixel range: min={image.min()}, max={image.max()}")
    
    image = np.expand_dims(image, 0)
    logger.debug(f"After expand_dims: shape={image.shape}")
    
    return image

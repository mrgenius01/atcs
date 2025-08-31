from src.anpr.preprocess import preprocess_image
import numpy as np


def test_preprocess_handles_bytes():
    # create a dummy black image
    import cv2
    img = np.zeros((10,10,3), dtype=np.uint8)
    _, buff = cv2.imencode('.png', img)
    out = preprocess_image(buff.tobytes())
    assert out.shape[:2] == (10,10)

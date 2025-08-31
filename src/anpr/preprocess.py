import cv2
import numpy as np

# Simple preprocess stub: grayscale -> blur -> threshold

def preprocess_image(img_bytes: bytes) -> np.ndarray:
    image = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(image, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    return th

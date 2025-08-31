import cv2
import numpy as np
import base64


def preprocess_image(img_data):
    """
    Preprocess image for license plate detection
    Args:
        img_data: Base64 encoded image or raw bytes
    Returns:
        Preprocessed image ready for plate detection
    """
    try:
        # Handle base64 encoded images
        if isinstance(img_data, str):
            if img_data.startswith('data:image'):
                # Remove data URL prefix
                img_data = img_data.split(',')[1]
            img_bytes = base64.b64decode(img_data)
        else:
            img_bytes = img_data
            
        # Convert bytes to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Could not decode image")
        
        # Resize if too large
        height, width = img.shape[:2]
        if width > 1200:
            scale = 1200 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to clean up the image
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return {
            'original': img,
            'gray': gray,
            'processed': cleaned,
            'width': img.shape[1],
            'height': img.shape[0]
        }
        
    except Exception as e:
        return {
            'error': f"Preprocessing failed: {str(e)}",
            'processed': None
        }

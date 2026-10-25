"""
src/extractors/image_preprocessor.py - OpenCV preprocessing pipeline for scanned document images.
Includes grayscale conversion, noise reduction, CLAHE contrast enhancement, and deskewing.
"""

from typing import Tuple
import cv2
import numpy as np


def preprocess_image_for_ocr(
    image: np.ndarray,
    enhance_contrast: bool = True,
    apply_deskew: bool = True,
) -> Tuple[np.ndarray, float]:
    """
    Preprocess an input BGR or RGB image for optimal OCR extraction.
    Returns: (preprocessed_image_bgr, detected_skew_angle_degrees)
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    detected_angle = 0.0

    # 1. Deskew detection
    if apply_deskew:
        detected_angle = detect_skew_angle(gray)
        if abs(detected_angle) > 0.5 and abs(detected_angle) < 45.0:
            gray = rotate_image(gray, detected_angle)

    # 2. Contrast enhancement via CLAHE (Contrast Limited Adaptive Histogram Equalization)
    if enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
    else:
        enhanced = gray

    # 3. Light denoising using fast Gaussian blur or bilateral filter
    denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=50, sigmaSpace=50)

    # Convert back to 3-channel for OCR engines expecting 3 channels
    processed_bgr = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
    return processed_bgr, detected_angle


def detect_skew_angle(gray_image: np.ndarray) -> float:
    """
    Estimate skew angle in degrees using Otsu binarization and minAreaRect on foreground pixels.
    """
    # Invert binary threshold to identify text regions as white pixels
    _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Filter out small noise
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # OpenCV minAreaRect returns angle in [-90, 0)
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    return round(float(angle), 2)


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image around its center by angle degrees with border reflection/padding."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated

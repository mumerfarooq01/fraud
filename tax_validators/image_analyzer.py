"""
Basic Image Quality Analyzer
Performs simple blur detection on PDF pages converted to images.
"""

import cv2
import numpy as np
from pdf2image import convert_from_bytes
from PIL import Image
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_pdf_to_images(pdf_bytes) -> List[Image.Image]:
	"""
	Convert PDF pages to PIL images
	
	Args:
		pdf_bytes: Bytes of the PDF file (e.g., from Streamlit upload)
	
	Returns:
		List of PIL Image objects
	"""
	try:
		if hasattr(pdf_bytes, 'read'):
			# BytesIO-like object
			pdf_bytes.seek(0)
			data = pdf_bytes.read()
		else:
			# Raw bytes
			data = pdf_bytes
		
		# Convert PDF to images at reasonable DPI for quality analysis
		images = convert_from_bytes(data, dpi=200)
		logger.info(f"Converted PDF to {len(images)} image(s)")
		return images
	except Exception as e:
		logger.error(f"Failed to convert PDF to images: {e}")
		return []

def _pil_to_cv2(image: Image.Image) -> np.ndarray:
	"""
	Convert a PIL Image to an OpenCV BGR image array
	"""
	return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

def calculate_blur_score(image) -> float:
	"""
	Calculate Laplacian blur score
	
	Args:
		image: PIL Image or OpenCV image
	
	Returns:
		Laplacian variance (lower = more blurry)
	"""
	try:
		# Ensure we have a cv2 image
		if isinstance(image, Image.Image):
			cv_img = _pil_to_cv2(image)
		else:
			cv_img = image
		
		# Convert to grayscale
		gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
		# Laplacian variance as blur metric
		blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
		return blur_score
	except Exception as e:
		logger.error(f"Failed to calculate blur score: {e}")
		return 0.0

def analyze_image_quality(pdf_bytes) -> Dict[str, Any]:
	"""
	Analyze all pages for quality issues (blur only for POC)
	
	Args:
		pdf_bytes: Bytes of the PDF file (e.g., from Streamlit upload)
	
	Returns:
		Dictionary with average blur score, list of blurry pages, and flags
	"""
	images = convert_pdf_to_images(pdf_bytes)
	results = {
		"avg_blur_score": 0.0,
		"blurry_pages": [],
		"quality_flags": []
	}
	
	if not images:
		results["quality_flags"].append("No pages could be processed from the PDF")
		return results
	
	blur_scores: List[float] = []
	for idx, img in enumerate(images):
		blur = calculate_blur_score(img)
		blur_scores.append(blur)
		# Threshold: <100 is potentially blurry (heuristic for POC)
		if blur < 100:
			results["blurry_pages"].append(idx + 1)
	
	# Calculate average blur score
	results["avg_blur_score"] = float(np.mean(blur_scores)) if blur_scores else 0.0
	
	if results["blurry_pages"]:
		results["quality_flags"].append(f"Blurry pages detected: {results['blurry_pages']}")
	
	logger.info(
		f"Image quality analysis complete. Avg blur: {results['avg_blur_score']:.2f}, "
		f"Blurry pages: {results['blurry_pages']}"
	)
	return results

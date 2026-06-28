"""
API-friendly forensic visualizations
Returns base64-encoded images instead of displaying them
"""

import io
import base64
import pdfplumber
from pdf2image import convert_from_bytes
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for API
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np


def create_forensic_visualizations_api(pdf_file, pdf_bytes, forensic_results, max_pages=2):
    """
    Generate annotated images showing forensic issues
    Returns base64-encoded images for API response
    
    Args:
        pdf_file: File path
        pdf_bytes: PDF bytes for image conversion
        forensic_results: Results from forensic_analyzer
        max_pages: Number of pages to visualize
        
    Returns:
        list: List of dicts with page_num and base64_image
    """
    
    visualizations = []
    
    try:
        images = convert_from_bytes(pdf_bytes, dpi=200)
    except Exception as e:
        return {"error": f"Could not generate visualizations: {str(e)}"}
    
    with pdfplumber.open(pdf_file) as pdf:
        for page_num in range(min(max_pages, len(pdf.pages))):
            page = pdf.pages[page_num]
            img = images[page_num]
            
            # Create 2x2 grid
            fig, axes = plt.subplots(2, 2, figsize=(16, 20))
            
            scale = img.size[1] / page.height
            
            # 1. Original
            axes[0, 0].imshow(img)
            axes[0, 0].set_title('Original Document', fontweight='bold', fontsize=12)
            axes[0, 0].axis('off')
            
            # 2. Font highlighting
            axes[0, 1].imshow(img)
            font_data = forensic_results.get('fonts', {})
            
            if font_data and font_data.get('dominant_font'):
                dominant = font_data['dominant_font']
                
                for char in page.chars:
                    if char.get('fontname', '') != dominant:
                        x0 = char['x0'] * scale
                        y0 = char['top'] * scale
                        w = (char['x1'] - char['x0']) * scale
                        h = (char['bottom'] - char['top']) * scale
                        rect = Rectangle((x0, y0), w, h,
                                        linewidth=0.5, edgecolor='red',
                                        facecolor='red', alpha=0.3)
                        axes[0, 1].add_patch(rect)
            
            axes[0, 1].set_title('Font Inconsistencies (Red)', fontweight='bold', fontsize=12)
            axes[0, 1].axis('off')
            
            # 3. Number patterns
            axes[1, 0].imshow(img)
            words = page.extract_words()
            
            for word in words:
                if any(c.isdigit() for c in word['text']):
                    if '.' in word['text']:
                        decimals = len(word['text'].split('.')[-1])
                        color = 'green' if decimals == 2 else 'orange'
                        alpha = 0.2 if decimals == 2 else 0.4
                    else:
                        color = 'blue'
                        alpha = 0.15
                    
                    x0 = word['x0'] * scale
                    y0 = word['top'] * scale
                    w = (word['x1'] - word['x0']) * scale
                    h = (word['bottom'] - word['top']) * scale
                    rect = Rectangle((x0, y0), w, h,
                                    linewidth=1, edgecolor=color,
                                    facecolor=color, alpha=alpha)
                    axes[1, 0].add_patch(rect)
            
            axes[1, 0].set_title('Numbers (Green=2dp, Orange=Other)', fontweight='bold', fontsize=12)
            axes[1, 0].axis('off')
            
            # 4. Alignment issues
            axes[1, 1].imshow(img)
            alignment_data = forensic_results.get('alignment', {})
            
            if alignment_data and alignment_data.get('issues'):
                for issue in alignment_data['issues']:
                    if issue['page'] == page_num + 1:
                        for word in issue.get('words', []):
                            x0 = word['x0'] * scale
                            y0 = word['top'] * scale
                            w = (word['x1'] - word['x0']) * scale
                            h = (word['bottom'] - word['top']) * scale
                            rect = Rectangle((x0, y0), w, h,
                                            linewidth=2, edgecolor='red',
                                            facecolor='yellow', alpha=0.4)
                            axes[1, 1].add_patch(rect)
            
            axes[1, 1].set_title('Alignment Issues (Red/Yellow)', fontweight='bold', fontsize=12)
            axes[1, 1].axis('off')
            
            plt.tight_layout()
            
            # Save to bytes and convert to base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            plt.close(fig)
            
            visualizations.append({
                "page": str(page_num + 1),
                "image_base64": img_base64,
                "format": "png"
            })
    
    return visualizations
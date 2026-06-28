from .checks import (
    check_text_alignment,
    check_font_consistency,
    check_metadata,
    check_number_patterns,
    check_image_quality,
    check_page_numbers,
    extract_and_check_noa_id
)
from PIL import Image
import io
import tempfile
import os


def preprocess_uploaded_file(uploaded_file):
    """
    Convert uploaded file to PDF-compatible format
    Supports: PDF, JPEG, JPG, PNG
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        tuple: (pdf_bytes, file_type, temp_path)
    """
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()
    
    # Check file type
    if file_name.endswith('.pdf'):
        return file_bytes, 'pdf', None
    
    elif file_name.endswith(('.jpg', '.jpeg', '.png')):
        # Convert image to PDF
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # Open image
            img = Image.open(io.BytesIO(file_bytes))
            
            # Create PDF in memory
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)
            
            # Get page dimensions
            page_width, page_height = letter
            
            # Get image dimensions
            img_width, img_height = img.size
            
            # Scale image to fit page while maintaining aspect ratio
            aspect = img_height / float(img_width)
            
            if aspect > 1:  # Portrait
                display_width = page_width * 0.9
                display_height = display_width * aspect
            else:  # Landscape
                display_height = page_height * 0.9
                display_width = display_height / aspect
            
            # Center image on page
            x = (page_width - display_width) / 2
            y = (page_height - display_height) / 2
            
            # Save image temporarily
            temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            img.save(temp_img_path, 'PNG')
            
            # Draw image on PDF
            c.drawImage(temp_img_path, x, y, width=display_width, height=display_height)
            c.save()
            
            # Get PDF bytes
            pdf_bytes = pdf_buffer.getvalue()
            
            return pdf_bytes, 'image_converted', temp_img_path
            
        except Exception as e:
            raise ValueError(f"Could not convert image to PDF: {str(e)}")
    
    else:
        raise ValueError(f"Unsupported file format: {file_name}")


def analyze_document_forensics(pdf_file, pdf_bytes=None, file_name='unknown', doc_type='unknown'):
    """
    Complete forensic analysis of a PDF document with new NOA-specific checks
    Now supports JPEG/PNG via conversion
    
    Args:
        pdf_file: File path or uploaded file object
        pdf_bytes: Optional bytes for image analysis
        file_name: Original file name for tracking
        doc_type: Document type ('noa', 't1', or 'unknown')
        
    Returns:
        dict with all forensic results and overall score
    """
    
    results = {
        'alignment': None,
        'fonts': None,
        'metadata': None,
        'numbers': None,
        'image': None,
        'page_numbers': None,      # NEW
        'noa_id_check': None,      # NEW
        'overall_score': 0,
        'risk_level': 'LOW'
    }
    
    # Run existing checks
    try:
        results['alignment'] = check_text_alignment(pdf_file)
    except Exception as e:
        results['alignment'] = {'risk_score': 0, 'error': str(e)}
    
    try:
        results['fonts'] = check_font_consistency(pdf_file)
    except Exception as e:
        results['fonts'] = {'risk_score': 0, 'error': str(e)}
    
    try:
        results['metadata'] = check_metadata(pdf_file)
    except Exception as e:
        results['metadata'] = {'risk_score': 0, 'error': str(e)}
    
    try:
        results['numbers'] = check_number_patterns(pdf_file)
    except Exception as e:
        results['numbers'] = {'risk_score': 0, 'error': str(e)}
    
    try:
        if pdf_bytes:
            results['image'] = check_image_quality(pdf_bytes)
        else:
            results['image'] = {'risk_score': 0, 'flags': ['Image analysis skipped']}
    except Exception as e:
        results['image'] = {'risk_score': 0, 'error': str(e)}
    
    # NEW CHECK 1: Page number consistency (NOA only)
    try:
        if pdf_bytes:
            results['page_numbers'] = check_page_numbers(pdf_bytes, doc_type)
        else:
            results['page_numbers'] = {'risk_score': 0, 'applicable': False}
    except Exception as e:
        results['page_numbers'] = {'risk_score': 0, 'error': str(e), 'applicable': False}
    
    # NEW CHECK 2: NOA ID duplicate detection (NOA only)
    try:
        if pdf_bytes:
            results['noa_id_check'] = extract_and_check_noa_id(pdf_bytes, file_name, doc_type)
        else:
            results['noa_id_check'] = {'risk_score': 0, 'applicable': False}
    except Exception as e:
        results['noa_id_check'] = {'risk_score': 0, 'error': str(e), 'applicable': False}
    
    # Calculate overall score including new checks
    scores = [
        results['alignment'].get('risk_score', 0),
        results['fonts'].get('risk_score', 0),
        results['metadata'].get('risk_score', 0),
        results['numbers'].get('risk_score', 0),
        results['image'].get('risk_score', 0),
        results['page_numbers'].get('risk_score', 0),       # NEW
        results['noa_id_check'].get('risk_score', 0)        # NEW
    ]
    
    results['overall_score'] = sum(scores) / len(scores)
    
    # Risk level calculation
    if results['overall_score'] < 30:
        results['risk_level'] = 'LOW'
    elif results['overall_score'] < 60:
        results['risk_level'] = 'MEDIUM'
    else:
        results['risk_level'] = 'HIGH'
    
    return results


import pdfplumber
import PyPDF2
import cv2
import numpy as np
from pdf2image import convert_from_bytes
from PIL import Image
from collections import Counter
import re
import io

# Check if pytesseract is available
TESSERACT_AVAILABLE = False
try:
    import pytesseract
    # Only check version if tesseract binary is actually available
    try:
        pytesseract.get_tesseract_version()
        TESSERACT_AVAILABLE = True
        print("[INFO] Tesseract OCR is available")
    except Exception as e:
        print(f"[WARNING] Tesseract binary not found: {e}")
        TESSERACT_AVAILABLE = False
except ImportError:
    print("[WARNING] pytesseract package not available")
    TESSERACT_AVAILABLE = False

def check_text_alignment(pdf_path):
    """
    Detect misaligned text rows
    Returns: {
        'risk_score': 0-100,
        'issues': [list of alignment issues],
        'count': int
    }
    """
    alignment_issues = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            if not words:
                continue
            
            # Group words by y-coordinate (rows)
            rows = {}
            for word in words:
                y_coord = round(word['top'], 1)
                if y_coord not in rows:
                    rows[y_coord] = []
                rows[y_coord].append(word)
            
            # Check alignment within each row
            for y, words_in_row in rows.items():
                if len(words_in_row) < 2:
                    continue
                
                tops = [w['top'] for w in words_in_row]
                deviation = max(tops) - min(tops)
                
                if deviation > 1.5:  # Misalignment threshold
                    alignment_issues.append({
                        'page': page_num,
                        'row_y': round(y, 1),
                        'deviation': round(deviation, 2),
                        'num_words': len(words_in_row),
                        'words': words_in_row
                    })
    
    # Calculate risk score
    if len(alignment_issues) > 10:
        risk_score = 80
    elif len(alignment_issues) > 5:
        risk_score = 50
    elif len(alignment_issues) > 0:
        risk_score = 20
    else:
        risk_score = 0
    
    return {
        'risk_score': risk_score,
        'issues': alignment_issues,
        'count': len(alignment_issues)
    }


def check_font_consistency(pdf_path):
    """
    Analyze font usage consistency
    Returns: {
        'risk_score': 0-100,
        'total_unique_fonts': int,
        'font_counts': Counter object,
        'flags': [list of issues]
    }
    """
    all_fonts = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            chars = page.chars
            if not chars:
                continue
            
            for char in chars:
                font_name = char.get('fontname', 'Unknown')
                all_fonts.append(font_name)
    
    font_counts = Counter(all_fonts)
    total_unique = len(font_counts)
    
    # Calculate risk
    flags = []
    if total_unique > 15:
        flags.append(f"Very high font variation ({total_unique} fonts)")
        risk_score = 80
    elif total_unique > 10:
        flags.append(f"High font variation ({total_unique} fonts)")
        risk_score = 60
    elif total_unique > 6:
        flags.append(f"Moderate font variation ({total_unique} fonts)")
        risk_score = 30
    else:
        risk_score = 0
    
    return {
        'risk_score': risk_score,
        'total_unique_fonts': total_unique,
        'font_counts': font_counts,
        'flags': flags,
        'dominant_font': font_counts.most_common(1)[0][0] if font_counts else None
    }


def check_metadata(pdf_path):
    """
    Check PDF metadata for suspicious signs
    Returns: {
        'risk_score': 0-100,
        'flags': [list of issues],
        'metadata': dict
    }
    """
    flags = []
    risk_score = 0
    metadata_info = {}
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            metadata = pdf.metadata
            
            if not metadata:
                flags.append("No metadata found")
                risk_score = 30
                return {'risk_score': risk_score, 'flags': flags, 'metadata': {}}
            
            producer = str(metadata.get('/Producer', 'Unknown'))
            creator = str(metadata.get('/Creator', 'Unknown'))
            
            metadata_info = {
                'producer': producer,
                'creator': creator,
                'creation_date': str(metadata.get('/CreationDate', 'Unknown')),
                'mod_date': str(metadata.get('/ModDate', 'Unknown')),
                'pages': len(pdf.pages)
            }
            
            # Check for consumer editing tools
            suspicious_tools = [
                'Word', 'LibreOffice', 'Google Docs', 
                'Smallpdf', 'iLovePDF', 'CorelDRAW',
                'Photoshop', 'Illustrator', 'Canva', 'Inkscape'
            ]
            
            for tool in suspicious_tools:
                if tool.lower() in producer.lower() or tool.lower() in creator.lower():
                    flags.append(f"Created with consumer tool: {tool}")
                    risk_score += 35
            
            # Check modification
            creation = metadata.get('/CreationDate', '')
            modified = metadata.get('/ModDate', '')
            if creation and modified and creation != modified:
                flags.append("Document modified after creation")
                risk_score += 15
    
    except Exception as e:
        flags.append(f"Metadata read error: {str(e)}")
        risk_score = 50
    
    return {
        'risk_score': min(risk_score, 100),
        'flags': flags,
        'metadata': metadata_info
    }


def check_number_patterns(pdf_path):
    """
    Analyze number formatting consistency
    Returns: {
        'risk_score': 0-100,
        'precision_map': dict,
        'flags': [list of issues],
        'total_numbers': int
    }
    """
    with pdfplumber.open(pdf_path) as pdf:
        full_text = '\n'.join([page.extract_text() for page in pdf.pages if page.extract_text()])
    
    decimals = re.findall(r'\d+\.\d+', full_text)
    
    precision_map = {}
    for num in decimals:
        precision = len(num.split('.')[-1])
        if precision not in precision_map:
            precision_map[precision] = []
        precision_map[precision].append(num)
    
    flags = []
    if len(precision_map) > 3:
        flags.append(f"High precision variation ({len(precision_map)} types)")
        risk_score = 40
    elif len(precision_map) > 2:
        flags.append(f"Moderate precision variation ({len(precision_map)} types)")
        risk_score = 20
    else:
        risk_score = 0
    
    return {
        'risk_score': risk_score,
        'precision_map': precision_map,
        'flags': flags,
        'total_numbers': len(decimals)
    }


def check_image_quality(pdf_bytes, max_pages=3):
    """
    Analyze image quality (blur detection)
    Takes pdf_bytes (from uploaded file) instead of path
    Returns: {
        'risk_score': 0-100,
        'blur_scores': [list of scores],
        'avg_blur': float,
        'flags': [list of issues]
    }
    """
    try:
        from pdf2image import convert_from_bytes
        
        images = convert_from_bytes(pdf_bytes, dpi=150)
        blur_scores = []
        
        for idx, img in enumerate(images[:max_pages], 1):
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            blur = cv2.Laplacian(gray, cv2.CV_64F).var()
            blur_scores.append(blur)
        
        avg_blur = np.mean(blur_scores) if blur_scores else 0
        
        flags = []
        risk_score = 0
        
        if avg_blur < 100:
            flags.append(f"Low blur score ({avg_blur:.1f})")
            risk_score = 30
        
        if len(blur_scores) > 1:
            variance = max(blur_scores) / min(blur_scores) if min(blur_scores) > 0 else 1
            if variance > 3:
                flags.append(f"Inconsistent blur ({variance:.1f}x)")
                risk_score += 25
        
        return {
            'risk_score': min(risk_score, 100),
            'blur_scores': blur_scores,
            'avg_blur': avg_blur,
            'flags': flags
        }
        
    except Exception as e:
        return {
            'risk_score': 0,
            'blur_scores': [],
            'avg_blur': 0,
            'flags': [f'Image analysis unavailable: {str(e)}']
        }


def check_page_numbers(pdf_bytes, doc_type='unknown'):
    """
    Check if page numbers on odd pages are sequential and consistent
    Only applicable to NOA documents
    
    Args:
        pdf_bytes: PDF file as bytes
        doc_type: Document type ('noa', 't1', or 'unknown')
    
    Returns:
        dict with risk_score, issues, and page_numbers found
    """
    
    # Skip if not NOA
    if doc_type.lower() != 'noa':
        return {
            'risk_score': 0,
            'applicable': False,
            'message': 'Page number check only applies to NOA documents'
        }
    
    # Check if Tesseract is available
    if not TESSERACT_AVAILABLE:
        return {
            'risk_score': 0,
            'applicable': True,
            'error': 'Tesseract OCR not installed - required for page number extraction',
            'issues': []
        }
    
    try:
        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes, dpi=200)
        
        page_numbers_found = []
        issues = []
        
        # Check odd pages only (0-indexed: 0, 2, 4...)
        for idx, img in enumerate(images):
            page_num = idx + 1  # 1-indexed page number
            
            # Only check odd pages
            if page_num % 2 == 1:
                # Crop top-right corner (approx coordinates)
                width, height = img.size
                top_right = img.crop((width * 0.8, 0, width, height * 0.1))
                
                # OCR to extract text
                text = pytesseract.image_to_string(top_right, config='--psm 6')
                
                # Look for "Page X" pattern
                match = re.search(r'Page\s*(\d+)', text, re.IGNORECASE)
                
                if match:
                    extracted_num = int(match.group(1))
                    page_numbers_found.append({
                        'physical_page': page_num,
                        'extracted_number': extracted_num,
                        'expected': page_num
                    })
                    
                    # Check if matches expected
                    if extracted_num != page_num:
                        issues.append({
                            'page': page_num,
                            'expected': page_num,
                            'found': extracted_num,
                            'issue': f'Page number mismatch: expected {page_num}, found {extracted_num}'
                        })
                else:
                    # Page number not found where expected
                    issues.append({
                        'page': page_num,
                        'issue': f'Page number not found on page {page_num}'
                    })
        
        # Check for sequence gaps
        extracted_nums = [p['extracted_number'] for p in page_numbers_found if 'extracted_number' in p]
        if extracted_nums:
            # Should be: 1, 3, 5, 7...
            expected_sequence = list(range(1, len(images) + 1, 2))
            
            if sorted(extracted_nums) != expected_sequence[:len(extracted_nums)]:
                issues.append({
                    'issue': 'Page numbering sequence is not consistent',
                    'expected': expected_sequence[:len(extracted_nums)],
                    'found': sorted(extracted_nums)
                })
        
        # Calculate risk score
        if len(issues) > 3:
            risk_score = 80
        elif len(issues) > 1:
            risk_score = 50
        elif len(issues) == 1:
            risk_score = 25
        else:
            risk_score = 0
        
        return {
            'risk_score': risk_score,
            'applicable': True,
            'page_numbers_found': page_numbers_found,
            'issues': issues,
            'total_pages': len(images)
        }
        
    except Exception as e:
        return {
            'risk_score': 0,
            'applicable': True,
            'error': str(e),
            'issues': []
        }


def extract_and_check_noa_id(pdf_bytes, file_name='unknown.pdf', doc_type='unknown'):
    """
    Extract identification number from NOA and check for duplicates
    
    Args:
        pdf_bytes: PDF file as bytes
        file_name: Original file name
        doc_type: Document type
    
    Returns:
        dict with risk_score, id_number, is_duplicate, and details
    """
    
    # Only applicable to NOA
    if doc_type.lower() != 'noa':
        return {
            'risk_score': 0,
            'applicable': False,
            'message': 'ID number check only applies to NOA documents'
        }
    
    # Check if Tesseract is available
    if not TESSERACT_AVAILABLE:
        return {
            'risk_score': 0,
            'applicable': True,
            'error': 'Tesseract OCR not installed - required for ID extraction',
            'id_number': None,
            'is_duplicate': False
        }
    
    try:
        # Convert first page to image with higher DPI for better OCR quality
        images = convert_from_bytes(pdf_bytes, dpi=300)
        first_page = images[0]
        
        # Crop center-right area where the ID is located
        # This region includes the Notice details box and the ID below "Date issued"
        width, height = first_page.size
        # Best results: center-right area (40-80% width, 10-30% height)
        id_region = first_page.crop((width * 0.4, height * 0.1, width * 0.8, height * 0.3))
        
        # OCR with PSM 11 (sparse text) for better accuracy on individual fields
        text = pytesseract.image_to_string(id_region, config='--psm 11')
        
        # Try multiple strategies to find the ID
        id_match = None
        
        # Strategy 1: Look for 8-9 character alphanumeric pattern (most common)
        # Pattern like: 5X4YR5JX or 5SX4YR5JX (OCR might add extra chars)
        matches = re.findall(r'\b([A-Z0-9]{8,10})\b', text, re.IGNORECASE)
        
        # Filter matches that look like IDs (not other numbers/text)
        for match in matches:
            match_upper = match.upper()
            # Look for patterns like X4YR or X5J (typical ID patterns)
            if re.search(r'[A-Z0-9]*[XY][0-9][A-Z]{2}', match_upper):
                id_match = match_upper
                break
        
        # Strategy 2: Look specifically after "Date issued"
        if not id_match and 'date issued' in text.lower():
            idx = text.lower().find('date issued')
            text_after_date = text[idx+50:]
            pattern_match = re.search(r'\b([A-Z0-9]{8,10})\b', text_after_date, re.IGNORECASE)
            if pattern_match:
                id_match = pattern_match.group(1).upper()
        
        # Strategy 3: Fallback - any 8-10 char alphanumeric
        if not id_match and matches:
            id_match = matches[0].upper()
        
        if not id_match:
            return {
                'risk_score': 30,
                'applicable': True,
                'id_number': None,
                'issue': 'Could not extract identification number from NOA',
                'is_duplicate': False,
                'debug_ocr_text': text[:300] if text else 'No text extracted'  # Debug info
            }
        
        # Clean up OCR errors: "5SX" -> "5X", "0" -> "O" in certain positions
        id_number = id_match
        if id_number.startswith('5SX') and len(id_number) == 9:
            id_number = '5X' + id_number[3:]  # Remove extra S
        elif id_number.startswith('5S') and len(id_number) >= 8:
            id_number = '5' + id_number[2:]  # Remove S completely
        
        # Check for duplicates in database
        from .database import ForensicDatabase
        db = ForensicDatabase()
        duplicate_check = db.check_duplicate_id(id_number)
        
        if duplicate_check['is_duplicate']:
            # CRITICAL: This document uses a previously seen ID!
            db.record_duplicate_detection(id_number, file_name)
            
            return {
                'risk_score': 100,  # Maximum risk!
                'applicable': True,
                'id_number': id_number,
                'is_duplicate': True,
                'duplicate_details': duplicate_check['original_record'],
                'flags': [
                    f'🚨 DUPLICATE ID DETECTED!',
                    f'This ID was previously used in: {duplicate_check["original_record"]["file_name"]}',
                    f'Original upload date: {duplicate_check["original_record"]["uploaded_timestamp"]}',
                    f'This indicates DOCUMENT FORGERY - same NOA used twice'
                ]
            }
        else:
            # New ID - store it
            # Try to extract additional info for better tracking
            
            sin_last_4 = None
            full_name = None
            date_issued = None
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                first_page_text = pdf.pages[0].extract_text()
                
                # Extract SIN (XXX XX3 241 format)
                sin_match = re.search(r'XXX XX(\d) (\d{3})', first_page_text)
                if sin_match:
                    sin_last_4 = sin_match.group(1) + sin_match.group(2)
                
                # Extract name (line after "Notice details" or before address)
                name_match = re.search(r'([A-Z\s]+)\n\d+\s+[A-Z]', first_page_text)
                if name_match:
                    full_name = name_match.group(1).strip()
                
                # Extract date issued
                date_match = re.search(r'Date issued\s+([A-Za-z]+\s+\d+,\s+\d{4})', first_page_text)
                if date_match:
                    date_issued = date_match.group(1)
            
            # Calculate document hash for integrity
            import hashlib
            doc_hash = hashlib.sha256(pdf_bytes).hexdigest()[:16]
            
            # Store in database
            stored = db.store_id_number(
                identification_number=id_number,
                sin_last_4=sin_last_4,
                full_name=full_name,
                date_issued=date_issued,
                document_hash=doc_hash,
                file_name=file_name
            )
            
            return {
                'risk_score': 0,
                'applicable': True,
                'id_number': id_number,
                'is_duplicate': False,
                'stored': stored,
                'extracted_info': {
                    'sin_last_4': sin_last_4,
                    'full_name': full_name,
                    'date_issued': date_issued
                },
                'flags': [
                    f'✅ New ID recorded: {id_number}',
                    'ID stored in forensic database for future duplicate detection'
                ]
            }
    
    except Exception as e:
        return {
            'risk_score': 0,
            'applicable': True,
            'error': str(e),
            'id_number': None,
            'is_duplicate': False
        }


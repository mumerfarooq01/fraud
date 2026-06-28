# Document Forensics Module

## Overview

Independent forensic analysis module for detecting visual forgery indicators in PDF documents. This module operates separately from the main tax document validation system.

## Features

### 1. Text Alignment Analysis
- Detects misaligned text rows that may indicate manual editing
- Flags rows with excessive vertical deviation
- **Risk Thresholds:**
  - 0-5 issues: Low risk (20)
  - 6-10 issues: Medium risk (50)
  - 10+ issues: High risk (80)

### 2. Font Consistency Analysis
- Analyzes font usage patterns across the document
- Identifies unusual font variations
- **Risk Thresholds:**
  - 1-6 unique fonts: Low risk (0)
  - 7-10 fonts: Medium risk (30)
  - 11-15 fonts: High risk (60)
  - 15+ fonts: Very high risk (80)

### 3. Metadata Analysis
- Checks PDF metadata for suspicious indicators
- Detects consumer editing tools (Word, Photoshop, etc.)
- Identifies modification history
- **Suspicious Tools Detected:**
  - Word, LibreOffice, Google Docs
  - Smallpdf, iLovePDF
  - Photoshop, Illustrator, Canva, Inkscape

### 4. Number Pattern Analysis
- Analyzes decimal precision consistency
- Detects formatting irregularities
- **Risk Thresholds:**
  - 1-2 precision types: Low risk (0)
  - 3 precision types: Medium risk (20)
  - 4+ precision types: High risk (40)

### 5. Image Quality Analysis
- Performs blur detection using Laplacian variance
- Checks consistency across pages
- **Risk Indicators:**
  - Blur score < 100: Potentially blurry (30)
  - Variance > 3x: Inconsistent quality (+25)

## Usage

### Standalone Analysis

```python
from forensics import analyze_document_forensics

# Analyze a PDF
with open('document.pdf', 'rb') as f:
    pdf_bytes = f.read()

results = analyze_document_forensics('document.pdf', pdf_bytes)

print(f"Overall Risk: {results['overall_score']}/100")
print(f"Risk Level: {results['risk_level']}")
```

### Streamlit Integration

The module is integrated into the main app with a dedicated forensics section:

1. Upload any PDF document
2. View overall risk score and risk level
3. Examine detailed scores for each check
4. Review visual annotations showing issues

### Visual Annotations

The module generates 4-panel visualizations:
- **Panel 1:** Original document
- **Panel 2:** Font inconsistencies (highlighted in red)
- **Panel 3:** Number patterns (green=2dp, orange=other, blue=integers)
- **Panel 4:** Alignment issues (red/yellow highlights)

## API Reference

### `analyze_document_forensics(pdf_file, pdf_bytes=None)`

Performs complete forensic analysis.

**Parameters:**
- `pdf_file` (str): Path to PDF file
- `pdf_bytes` (bytes, optional): PDF bytes for image analysis

**Returns:**
```python
{
    'alignment': {...},      # Text alignment results
    'fonts': {...},          # Font consistency results
    'metadata': {...},       # Metadata analysis results
    'numbers': {...},        # Number pattern results
    'image': {...},          # Image quality results
    'overall_score': float,  # 0-100
    'risk_level': str        # 'LOW', 'MEDIUM', or 'HIGH'
}
```

### Individual Check Functions

- `check_text_alignment(pdf_path)`
- `check_font_consistency(pdf_path)`
- `check_metadata(pdf_path)`
- `check_number_patterns(pdf_path)`
- `check_image_quality(pdf_bytes)`

### `create_forensic_visualizations(pdf_file, pdf_bytes, forensic_results, max_pages=2)`

Generates annotated visualizations for Streamlit display.

## Risk Score Calculation

Overall risk score is the **average** of all 5 individual check scores:

```
Overall Score = (Alignment + Fonts + Metadata + Numbers + Image) / 5
```

**Risk Levels:**
- **LOW:** Overall score < 30
- **MEDIUM:** Overall score 30-59
- **HIGH:** Overall score ≥ 60

## Error Handling

All checks are wrapped in try-except blocks. If one check fails:
- Error is logged to the result
- Risk score defaults to 0 for that check
- Other checks continue normally
- Overall analysis completes successfully

## Dependencies

- `pdfplumber`: Text and layout extraction
- `PyPDF2`: Metadata extraction
- `opencv-python`: Image quality analysis
- `pdf2image`: PDF to image conversion
- `matplotlib`: Visualization generation
- `numpy`: Numerical operations

## Limitations

1. **Image Quality Analysis:** Limited to first 3 pages (performance)
2. **Visual Annotations:** Shows first 2 pages only
3. **Alignment Detection:** May flag legitimate design variations
4. **Font Detection:** Character-level analysis (can be slow for large docs)

## Best Practices

1. **Interpretation:** Use as one signal among many, not definitive proof
2. **Context:** Government documents typically have:
   - Low font variation (1-3 fonts)
   - High alignment consistency
   - Professional metadata (Adobe, official tools)
   - Consistent number formatting
3. **False Positives:** Some legitimate PDFs may score medium risk

## Future Enhancements

- [ ] OCR text layer analysis
- [ ] Digital signature verification
- [ ] Color consistency checking
- [ ] Page layout anomaly detection
- [ ] Timestamp forensics
- [ ] Cross-reference validation

## Testing

Tested with:
- ✅ T1 Tax Return (2024)
- ✅ Notice of Assessment (2024)
- ✅ Various consumer-generated PDFs

## License

Part of the Fraud Detection POC system.


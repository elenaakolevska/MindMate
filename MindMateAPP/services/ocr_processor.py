import logging
from typing import Tuple

try:
    from .text_chunker import process_text_with_chunks
except ImportError:
    # Fallback for direct execution
    from text_chunker import process_text_with_chunks

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None

logger = logging.getLogger(__name__)


class OCRProcessor:
    
    def __init__(self, language='mkd+eng+deu'):
        self.language = language
        
    def extract_from_image(self, file) -> Tuple[str, str]:
        if not pytesseract or not Image:
            return "", "error: OCR dependencies not installed"
        try:
            image = Image.open(file)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            text = pytesseract.image_to_string(image, lang=self.language)
            cleaned_text = text.strip()
            
            if not cleaned_text:
                return "", "warning: No text detected"
            chunks = process_text_with_chunks(cleaned_text)
            return chunks, "success"
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return "", f"error: {str(e)}"
    

if __name__ == "__main__":
    import sys
    import os
    
    # Use hardcoded path or command line argument
    if len(sys.argv) >= 2:
        image_path = sys.argv[1]
    else:
        image_path = "/Users/snezhanakoleva/MindMate/Screenshot 2025-11-27 at 14.10.06.png"
    
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found")
        print("Usage: python ocr_processor.py <image_path>")
        print("Example: python ocr_processor.py /path/to/homework_screenshot.png")
        sys.exit(1)
    
    # Initialize OCR processor
    processor = OCRProcessor()
    
    print(f"Processing image: {image_path}")
    print("-" * 50)
    
    try:
        with open(image_path, 'rb') as file:
            result, status = processor.extract_from_image(file)
            
            print(f"Status: {status}")
            
            if status == "success" and result:
                chunks = result
                print(f"Created {len(chunks)} chunks from extracted text")
                print("-" * 50)
                
                # Print the first chunk
                if chunks:
                    print("First chunk:")
                    print(chunks[0])
                    print("-" * 50)
                    
                    # Print all chunks with numbers
                    print("All chunks:")
                    for i, chunk in enumerate(chunks, 1):
                        print(f"\nChunk {i} ({len(chunk)} chars):")
                        print(chunk)
                else:
                    print("No chunks created")
            else:
                print(f"Error or warning: {status}")
                
    except Exception as e:
        print(f"Error opening file: {e}")

import logging
import sys
import os
from typing import Tuple
import time

try:
    from .ocr_processor import OCRProcessor
    from .preprocess_pdf_files import preprocess_pdf
    from .preprocess_doc_files import preprocess_doc
    from .text_chunker import process_text_with_chunks
except ImportError:
    # Fallback for direct execution
    from ocr_processor import OCRProcessor
    from preprocess_pdf_files import preprocess_pdf
    from preprocess_doc_files import preprocess_doc
    from text_chunker import process_text_with_chunks

logger = logging.getLogger(__name__)


def process_document(file_path: str):
    """
    Process any document type (image, PDF, Word) and return chunks.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found")
        return None
    
    print(f"Processing document: {file_path}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp')):
            # Process image with OCR
            processor = OCRProcessor()
            with open(file_path, 'rb') as f:
                chunks, status = processor.extract_from_image(f)
            
            print(f"OCR Status: {status}")
            if status == "success" and chunks:
                print(f"Created {len(chunks)} chunks from OCR")
                print("-" * 40)
                print("First chunk:")
                print(chunks[0])
                return chunks
            else:
                print(f"OCR failed: {status}")
                return None
                
        elif file_path.lower().endswith('.pdf'):
            # Process PDF
            print("Processing PDF document...")
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_dict = {"name": file_path, "content": file_content}
            result = preprocess_pdf(file_dict)
            
            chunks = result['result']['chunks']
            metadata = result['result']['metadata']
            
            print(f"PDF processed successfully!")
            print(f"Number of chunks: {metadata['num_chunks']}")
            print(f"Total characters: {metadata['total_chars']}")
            print("-" * 40)
            print("First chunk:")
            print(chunks[0])
            return chunks
            
        elif file_path.lower().endswith('.docx'):
            # Process Word document
            print("Processing Word document...")
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            file_dict = {"name": file_path, "content": file_content}
            result = preprocess_doc(file_dict, blob_metadata=None)
            
            chunks = result['result']['chunks']
            metadata = result['result']['metadata']
            
            print(f"Word document processed successfully!")
            print(f"Number of chunks: {metadata['num_chunks']}")
            print(f"Total characters: {metadata['total_chars']}")
            print("-" * 40)
            print("First chunk:")
            print(chunks[0])
            return chunks
            
        else:
            print(f"Unsupported file type. Supported: PDF, DOCX, PNG, JPG, JPEG, TIFF, BMP")
            return None
            
    except Exception as e:
        print(f"Error processing document: {e}")
        return None
    
    finally:
        processing_time = time.time() - start_time
        print(f"\nProcessing completed in {processing_time:.2f} seconds")


if __name__ == "__main__":
    # Get file path from command line or use default
    if len(sys.argv) >= 2:
        file_path = sys.argv[1]
    else:
        # Default test file path - update this to test with your files
        file_path = "/Users/snezhanakoleva/MindMate/Screenshot 2025-11-27 at 14.10.06.png"
        print(f"No file specified, using default: {file_path}")
        print("Usage: python document_preprocessing.py <file_path>")
        print("-" * 60)
    
    chunks = process_document(file_path)
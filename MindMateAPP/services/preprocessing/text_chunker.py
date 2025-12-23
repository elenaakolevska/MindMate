"""
Text Chunking Utility for MindMate
Extracts the chunking functionality from PDF and Word preprocessing scripts
"""

import re
from typing import List


def split_text_into_chunks(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks of specified size.
    Handles tables intelligently and finds good sentence boundaries.
    """
    chunks = []
    text_length = len(text)
    start = 0

    min_overlap = max(50, int(overlap * 0.5))
    max_overlap = min(overlap * 1.5, chunk_size - 50)

    # Find all tables
    table_matches = list(re.finditer(r"(Table Content:.*?End of table content\.)", text, re.DOTALL))
    table_spans = [m.span() for m in table_matches]

    while start < text_length:
        # Find the next table that starts after 'start'
        next_table = None
        for t_start, t_end in table_spans:
            if t_start >= start:
                next_table = (t_start, t_end)
                break

        end = start + chunk_size
        if end > text_length:
            end = text_length

        if next_table and next_table[0] < end:
            t_start, t_end = next_table
            # If the table fits entirely within the chunk, include it
            if t_end <= end:
                best_end = end
                if end < text_length:
                    # Find sentence boundary
                    for i in range(end, max(start + chunk_size // 2, start), -1):
                        if i < text_length and text[i-1] in '.!?' and (i == text_length or text[i].isspace() or text[i].isupper()):
                            best_end = i
                            break
                
                chunk = text[start:best_end]
                chunks.append(chunk)
                
                if best_end >= text_length:
                    break
                
                # Find where to start the next chunk
                next_start = best_end
                while next_start < text_length and text[next_start].isspace():
                    next_start += 1
                
                start = next_start
            else:
                # Table would be split, so move it to the next chunk
                if t_start > start:
                    pre_table_text = text[start:t_start]
                    if pre_table_text.strip():
                        pre_chunks = _simple_chunking(pre_table_text, chunk_size, overlap)
                        chunks.extend(pre_chunks)
                
                # Handle large tables by splitting them
                if t_end - t_start > chunk_size:
                    table_text = text[t_start:t_end]
                    table_lines = table_text.split('\n')
                    header = table_lines[1] if len(table_lines) > 1 else ''
                    rows = table_lines[2:-1]
                    current_chunk = f"Table Content:\n{header}"
                    
                    for row in rows:
                        if len(current_chunk) + len(row) + 1 > chunk_size:
                            chunks.append(current_chunk + "\nEnd of table content.")
                            current_chunk = f"Table Content:\n{header}\n{row}"
                        else:
                            current_chunk += f"\n{row}"
                    
                    if current_chunk:
                        chunks.append(current_chunk + "\nEnd of table content.")
                else:
                    # Table fits as whole
                    chunks.append(text[t_start:t_end])
                
                start = t_end
        else:
            # No table in this chunk
            end = start + chunk_size
            if end >= text_length:
                end = text_length
                chunks.append(text[start:end])
                break
            else:
                # Find sentence boundary
                best_end = end
                for i in range(end, max(start + chunk_size // 2, start), -1):
                    if i < text_length and text[i-1] in '.!?' and (i == text_length or text[i].isspace() or text[i].isupper()):
                        best_end = i
                        break
                
                chunks.append(text[start:best_end])
                
                next_start = best_end
                while next_start < text_length and text[next_start].isspace():
                    next_start += 1
                
                start = next_start

    return chunks


def _simple_chunking(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple fallback chunking without table handling."""
    chunks = []
    text_length = len(text)
    start = 0
    min_overlap = max(50, int(overlap * 0.5))
    
    while start < text_length:
        end = start + chunk_size
        if end < text_length:
            # Find sentence boundary
            for i in range(end, start, -1):
                if text[i-1] in '.!?' and i < len(text) and (text[i].isspace() or text[i].isupper()):
                    end = i
                    break
        else:
            end = text_length
        
        chunks.append(text[start:end])
        
        if end == text_length:
            break
        
        start = end - max(min_overlap, min(overlap, chunk_size - 50))
    
    return chunks


def normalize_chunk(chunk: str) -> str:
    """Clean and normalize a text chunk."""
    normalized = re.sub(r"\[\[\d+\]\],?\s*", "", chunk)
    normalized = re.sub(r"\n\s*#{1,6}\s*([^\n]+)", r". \1:", normalized)
    normalized = re.sub(r"\n\s*-\s*", ". ", normalized)
    normalized = re.sub(r"\*\*([^*]+)\*\*", r"\1", normalized)
    normalized = re.sub(r"\*([^*]+)\*", r"\1", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"\n\n", ". ", normalized)
    normalized = re.sub(r"\n", " ", normalized)
    
    # Fix broken words and punctuation
    normalized = re.sub(r"(\w)-\s+(\w)", r"\1\2", normalized)
    normalized = re.sub(r"--+", "—", normalized)
    normalized = re.sub(r"\s*\|\s*", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*([.,:;!?])", r"\1", normalized)
    normalized = re.sub(r"([.,:;!?])\s*", r"\1 ", normalized)
    normalized = re.sub(r"\.\s*([a-z])", lambda m: ". " + m.group(1).upper(), normalized)
    
    normalized = normalized.strip()
    if normalized and not normalized[0].isupper():
        normalized = normalized[0].upper() + normalized[1:]
    if normalized and normalized[-1] not in '.!?':
        normalized += "."
    
    return normalized


def process_text_with_chunks(text: str, chunk_size: int = 1500, overlap: int = 200) -> List[str]:
    """
    Main function to process text into normalized chunks.
    Can be used with OCR extracted text from images, PDFs, or Word docs.
    """
    chunks = split_text_into_chunks(text, chunk_size, overlap)
    normalized_chunks = [normalize_chunk(chunk) for chunk in chunks]
    return normalized_chunks

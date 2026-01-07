"""
IndiQuant - Con-Call Analyst Module
Inspired by NotebookLM for earnings call analysis

Provides:
- PDF text extraction
- Gemini-powered earnings call analysis
- Structured summary: Growth Drivers, Headwinds, Red Flags
"""

import io
import logging
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF file bytes.
    Uses PyPDF2 for extraction.
    """
    try:
        import PyPDF2
        
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        
        return text.strip()
        
    except ImportError:
        logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
        return ""
    except Exception as e:
        logger.error(f"Failed to extract PDF text: {e}")
        return ""


def chunk_text(text: str, max_chunk_size: int = 8000) -> list:
    """
    Split text into chunks for processing.
    Respects paragraph boundaries.
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


async def analyze_with_gemini(text: str, api_key: str, model: str = "gemini-2.0-flash") -> Dict:
    """
    Analyze earnings call transcript using Gemini API.
    
    Returns structured analysis with:
    - Growth Drivers
    - Headwinds
    - Management Integrity Check
    - Key Financial Highlights
    """
    
    system_prompt = """You are an expert financial analyst specializing in Indian equity markets. 
Analyze the following earnings call transcript or annual report excerpt and provide a structured analysis.

Your analysis must include:

1. **Growth Drivers** (3-5 bullet points)
   - Key revenue growth catalysts mentioned
   - New products, markets, or expansion plans
   - Competitive advantages highlighted

2. **Headwinds & Risks** (3-5 bullet points)
   - Challenges or concerns raised
   - Market/regulatory risks
   - Cost pressures or margin concerns

3. **Management Integrity Check** (2-3 bullet points)
   - Any red flags (auditor comments, unusual transactions, key resignations)
   - Guidance vs. actual performance history
   - Capital allocation quality

4. **Key Financial Highlights**
   - Revenue/profit growth mentioned
   - Margin trends
   - Capex/investment plans

5. **Analyst Summary**
   - One paragraph summary of the overall tone and key takeaways

Format your response as a structured JSON object with these sections."""

    # Truncate text if too long (Gemini limit)
    if len(text) > 30000:
        text = text[:30000] + "\n\n[Text truncated due to length...]"
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt},
                        {"text": f"\n\nTranscript/Report to analyze:\n\n{text}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096
            }
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                params={"key": api_key},
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Gemini API error: {error_msg}")
                return {"error": f"API Error: {response.status_code}"}
            
            data = response.json()
            
            # Extract generated text
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    analysis_text = parts[0].get("text", "")
                    
                    # Try to parse as JSON, otherwise return as text
                    try:
                        import json
                        # Find JSON in the response
                        start = analysis_text.find('{')
                        end = analysis_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = analysis_text[start:end]
                            return {"analysis": json.loads(json_str), "raw": analysis_text}
                    except:
                        pass
                    
                    return {"analysis": analysis_text, "raw": analysis_text}
            
            return {"error": "No response from Gemini"}
            
    except Exception as e:
        logger.error(f"Gemini analysis failed: {e}")
        return {"error": str(e)}


async def analyze_earnings_call(file_content: bytes, api_key: str, model: str = "gemini-2.0-flash") -> Dict:
    """
    Complete earnings call analysis pipeline.
    
    1. Extract text from PDF
    2. Analyze with Gemini
    3. Return structured results
    """
    # Step 1: Extract text
    text = extract_text_from_pdf(file_content)
    
    if not text:
        return {"error": "Could not extract text from PDF. Ensure it's a valid PDF file."}
    
    if len(text) < 100:
        return {"error": "PDF has insufficient text content for analysis."}
    
    # Step 2: Analyze with AI
    result = await analyze_with_gemini(text, api_key, model)
    
    if "error" in result:
        return result
    
    return {
        "success": True,
        "text_length": len(text),
        "analysis": result.get("analysis", {}),
        "raw_response": result.get("raw", ""),
        "summary": "Earnings call analysis complete. Review the structured breakdown above."
    }


def create_sample_analysis() -> Dict:
    """
    Create a sample analysis structure for demonstration.
    """
    return {
        "growth_drivers": [
            "Strong demand in consumer electronics segment, up 23% YoY",
            "New product launches in Q3 expected to contribute ₹500Cr revenue",
            "Capacity expansion in Gujarat plant by 40%",
            "Export revenue growing at 35% CAGR"
        ],
        "headwinds": [
            "Raw material cost inflation of 8-10%",
            "Supply chain challenges in semiconductor components",
            "Increased competition from Chinese imports"
        ],
        "management_integrity": [
            "No auditor qualifications observed",
            "Consistent dividend payout maintained",
            "Key management team stable for 5+ years"
        ],
        "financial_highlights": {
            "revenue_growth": "18% YoY",
            "ebitda_margin": "22.5%",
            "net_profit_growth": "25% YoY",
            "capex_guidance": "₹800Cr for FY25"
        },
        "analyst_summary": "Management delivered a confident outlook with strong execution on growth initiatives. "
                         "The company maintains healthy margins despite cost pressures, suggesting pricing power. "
                         "Key focus areas are capacity expansion and export market penetration. "
                         "No material governance concerns noted."
    }

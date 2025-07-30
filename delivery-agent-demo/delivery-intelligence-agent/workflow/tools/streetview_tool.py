from loguru import logger
import requests
from typing import Any, Dict, List
from workflow.services.street_image_analysis import analyze_streetview_from_url
import asyncio
from workflow.mcp.mcp_server import mcp
import time

@mcp.tool()
def street_view_(url: str) -> str:
    """
    Analyze street view from URL with proper error handling and timeout management
    """
    logger.info(f"Analyzing street view for delivery")
    try:
        # Custom prompt focusing on road width
        road_prompt = """
        Look at this street and tell me:
        1. How wide is this road? (narrow/medium/wide)
        2. How many lanes?
        3. Can delivery trucks navigate easily?
        4. Any width restrictions or obstacles?
        5. Parking availability on sides?
        
        Give me practical details for delivery planning.
        """
        
        # Set a longer timeout for the analysis
        start_time = time.time()
        
        # Analyze with timeout handling
        try:
            result = analyze_streetview_from_url(url, road_prompt)
            
            elapsed_time = time.time() - start_time
            print(f"Street view analysis completed in {elapsed_time:.2f} seconds")
            
            if result and result.get('success'):
                return f"AI analysis: {result['analysis']}, Location: {result['coordinates']}"
            else:
                error_msg = result.get('error', 'Unknown error occurred') if result else 'No result returned'
                return f"Street view analysis failed: {error_msg}"
                
        except Exception as analysis_error:
            return f"Street view analysis error: {str(analysis_error)}"
            
    except Exception as e:
        # Return a clean error string without disrupting the flow
        return f"Street view tool error: {str(e)}"

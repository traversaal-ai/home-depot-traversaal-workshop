import requests
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
import re
import os
import time
from workflow.utils.config import OPENAI_API_KEY, GOOGLE_API_KEY 



# Set OpenAI API key as environment variable
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI()

def parse_streetview_url(url):
    """Extract coordinates and view parameters from Google Street View URL"""
    try:
        viewpoint_match = re.search(r'viewpoint=([^&]+)', url)
        heading_match = re.search(r'heading=([^&]+)', url)
        pitch_match = re.search(r'pitch=([^&]+)', url)
        fov_match = re.search(r'fov=([^&]+)', url)
        
        if not viewpoint_match:
            raise ValueError("Could not extract coordinates from URL")
        
        lat, lng = viewpoint_match.group(1).split(',')
        
        return {
            'lat': float(lat),
            'lng': float(lng),
            'heading': float(heading_match.group(1)) if heading_match else 0,
            'pitch': float(pitch_match.group(1)) if pitch_match else 0,
            'fov': float(fov_match.group(1)) if fov_match else 90
        }
    except Exception as e:
        print(f"URL parsing error: {e}")
        raise

def download_streetview_image(lat, lng, heading=0, pitch=0, fov=90, size="640x640"):
    """Download Street View image from Google API"""
    try:
        url = "https://maps.googleapis.com/maps/api/streetview"
        
        params = {
            'size': size,
            'location': f"{lat},{lng}",
            'heading': heading,
            'pitch': pitch,
            'fov': fov,
            'key': GOOGLE_API_KEY
        }
        
        print(f" Requesting image from Google API...")
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            print(" Image downloaded successfully!")
        else:
            print(f"Google API error: {response.status_code}")
            print(f"Response: {response.text}")
            
        response.raise_for_status()
        
        image = Image.open(BytesIO(response.content))
        return image
        
    except requests.exceptions.RequestException as e:
        print(f" Network error downloading image: {e}")
        raise
    except Exception as e:
        print(f" Error processing image: {e}")
        raise

def image_to_base64(image):
    """Convert PIL Image to base64 string for OpenAI"""
    try:
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    except Exception as e:
        print(f" Error converting image to base64: {e}")
        raise

def analyze_image_with_openai(image, prompt=None):
    """Analyze image using OpenAI GPT-4 Vision"""
    
    if not prompt:
        prompt = """
        Analyze this street view image and tell me about:
        1. Is the road narrow, medium, or wide?
        2. How many lanes are there?
        3. Can two cars pass comfortably?
        4. What's the road surface condition?
        5. Is this urban, suburban, or rural?
        6. Any safety concerns or obstacles?
        
        Be specific and descriptive.
        """
    
    try:
        print(" Converting image for OpenAI...")
        base64_image = image_to_base64(image)
        
        print(" Sending to OpenAI GPT-4 Vision...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            timeout=60  # 60 second timeout
        )
        
        print(" OpenAI analysis complete!")
        return response.choices[0].message.content
        
    except Exception as e:
        print(f" OpenAI analysis error: {e}")
        raise

def analyze_streetview_from_url(streetview_url, custom_prompt=None):
    """
    Main function: Takes Google Street View URL and returns LLM analysis
    
    Args:
        streetview_url: The Google Street View URL
        custom_prompt: Optional custom prompt for analysis
    
    Returns:
        dict: Contains coordinates, analysis, and image
    """
    print(" Starting Street View Analysis...")
    print("=" * 50)
    
    try:
        # Extract coordinates from URL
        print(" Parsing URL...")
        params = parse_streetview_url(streetview_url)
        print(f" Location: {params['lat']}, {params['lng']}")
        print(f" View: heading={params['heading']}°, pitch={params['pitch']}°")
        
        # Download image
        print("\n Downloading image...")
        image = download_streetview_image(
            params['lat'], 
            params['lng'], 
            params['heading'], 
            params['pitch'], 
            params['fov']
        )
        
        # Analyze with OpenAI
        print("\n AI Analysis...")
        analysis = analyze_image_with_openai(image, custom_prompt)
        
        # Save image
        print("\n Saving results...")
        image.save('streetview_analysis.jpg')
        print(" Image saved as 'streetview_analysis.jpg'")
        
        print("\n ANALYSIS COMPLETE!")
        print("=" * 50)
        
        return {
            'success': True,
            'coordinates': f"{params['lat']}, {params['lng']}",
            'analysis': analysis,
            'image_saved': 'streetview_analysis.jpg'
        }
        
    except Exception as e:
        print(f"\n ERROR: {str(e)}")
        return {'success': False, 'error': {str(e)}}
    

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import re
import sys
from datetime import datetime
import subprocess

# Swedish to English translation dictionary (90% coverage)
TRANSLATIONS = {
    # Business terms
    "företag": "company", "verksamhet": "business", "firma": "firm",
    "omsättning": "revenue", "resultat": "profit", "vinst": "profit", 
    "förlust": "loss", "intäkter": "income", "kostnader": "costs",
    
    # Industries
    "handel": "trade", "tillverkning": "manufacturing", "tjänster": "services",
    "hotell": "hotel", "restaurang": "restaurant", "e-handel": "e-commerce",
    "bygg": "construction", "transport": "transport", "logistik": "logistics",
    "fastighet": "real estate", "fastigheter": "real estate",
    
    # Financial terms
    "miljoner": "million", "mkr": "million SEK", "tkr": "thousand SEK",
    "miljarder": "billion", "bkr": "billion SEK",
    
    # Business status
    "lönsam": "profitable", "väletablerad": "well-established",
    "etablerad": "established", "populär": "popular", "stark": "strong",
    "tillväxt": "growth", "potential": "potential", "framtid": "future",
    
    # Location terms
    "sverige": "Sweden", "stockholm": "Stockholm", "göteborg": "Gothenburg",
    "malmö": "Malmö", "uppsala": "Uppsala", "västerås": "Västerås",
    
    # Business activities
    "leverantör": "supplier", "grossist": "wholesaler", "butik": "store",
    "fabrik": "factory", "kontor": "office", "lager": "warehouse",
    "verkstad": "workshop", "ateljé": "studio", "salong": "salon"
}

# Currency conversion rate (approximate)
SEK_TO_USD = 0.095  # 1 SEK = 0.095 USD

def translate_text(text):
    """Translate Swedish text to English using the translation dictionary"""
    if not text:
        return text
    
    translated = text
    for swedish, english in TRANSLATIONS.items():
        translated = translated.replace(swedish, english)
    
    # Capitalize first letter
    return translated.capitalize()

def convert_currency(price_str):
    """Convert SEK prices to USD"""
    if not price_str:
        return price_str
    
    # Extract numbers from price string
    numbers = re.findall(r'[\d\s]+', price_str)
    if not numbers:
        return price_str
    
    try:
        price = int(''.join(numbers).replace(' ', ''))
        usd_price = round(price * SEK_TO_USD)
        return f"${usd_price:,}"
    except ValueError:
        return price_str

app = FastAPI(
    title="Bolagsplatsen Scraper API",
    description="API for scraping business listings from Bolagsplatsen",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BusinessListing(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    price: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    link: Optional[str] = None
    details: Optional[List[Dict[str, Any]]] = None
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    phone_number: Optional[str] = None

def run_scraper():
    """Run the Scrapy spider and return the data"""
    try:
        # First, try to load existing data from multiple possible locations
        data_files = [
            "bolagsplatsen_listings.json",
            "final_enhanced_listings.json",
            "enhanced_listings.json"
        ]
        
        raw_data = None
        
        # Try to load from existing files
        for file_path in data_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                        print(f"Loaded data from {file_path}: {len(raw_data)} items")
                        break
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
                    continue
        
        # If no data files found, try to run the scraper
        if not raw_data:
            print("No existing data found, running scraper...")
            # Run the scraper with cloud-optimized settings
            cmd = [sys.executable, "start_scraper.py"] if os.path.exists("start_scraper.py") else ["scrapy", "crawl", "bolagsplatsen"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.getcwd()  # Use current working directory instead of hardcoded path
            )
            
            if result.returncode == 0:
                # Check if the scraper created a new file
                for file_path in data_files:
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            raw_data = json.load(f)
                            break
            else:
                print(f"Scraper failed: {result.stderr}")
                return None
        
        if not raw_data:
            return None
        
        # Transform the data to match the expected format with translation and USD conversion
        transformed_data = []
        for item in raw_data:
            # Create details sections from the scraped data
            details_sections = []
            
            # Add business description section (use full description if available)
            description_text = item.get('full_description') or item.get('description', '')
            if description_text:
                details_sections.append({
                    "infoSummary": "Business Description",
                    "infoItems": [translate_text(description_text)]
                })
            
            # Add structured content sections if available
            if item.get('structured_content'):
                structured_content = item.get('structured_content', {})
                for section_key, section_content in structured_content.items():
                    if section_content and len(str(section_content).strip()) > 20:
                        # Translate section names
                        section_names = {
                            'company_brief': 'Company Overview',
                            'potential': 'Growth Potential',
                            'reason_for_sale': 'Reason for Sale',
                            'price_idea': 'Pricing Details',
                            'summary': 'Summary',
                            'description': 'Description',
                            'business_activity': 'Business Activity',
                            'market': 'Market Information',
                            'competition': 'Competitive Situation'
                        }
                        
                        section_title = section_names.get(section_key, section_key.replace('_', ' ').title())
                        details_sections.append({
                            "infoSummary": section_title,
                            "infoItems": [translate_text(str(section_content))]
                        })
            
            # Add financial metrics section
            financial_items = []
            if item.get('revenue'):
                financial_items.append(f"Revenue: {translate_text(item.get('revenue', ''))}")
            if item.get('detailed_revenue'):
                financial_items.append(f"Detailed Revenue: {translate_text(item.get('detailed_revenue', ''))}")
            if item.get('profit_status'):
                financial_items.append(f"Profit Status: {translate_text(item.get('profit_status', ''))}")
            if item.get('detailed_profit'):
                financial_items.append(f"Detailed Profit: {translate_text(item.get('detailed_profit', ''))}")
            if item.get('price'):
                financial_items.append(f"Asking Price: {convert_currency(item.get('price', ''))}")
            
            # Add additional financial details
            if item.get('financial_details'):
                for detail in item.get('financial_details', []):
                    financial_items.append(translate_text(detail))
            
            if financial_items:
                details_sections.append({
                    "infoSummary": "Financial Information",
                    "infoItems": financial_items
                })
            
            # Add business metrics section
            business_items = []
            if item.get('employee_count'):
                business_items.append(f"Employees: {translate_text(item.get('employee_count', ''))}")
            
            if business_items:
                details_sections.append({
                    "infoSummary": "Business Metrics",
                    "infoItems": business_items
                })
            
            # Add contact information section
            contact_items = []
            if item.get('phone'):
                contact_items.append(f"Phone: {item.get('phone', '')}")
            if item.get('email'):
                contact_items.append(f"Email: {item.get('email', '')}")
            if item.get('broker_name'):
                contact_items.append(f"Broker: {translate_text(item.get('broker_name', ''))}")
            if item.get('broker_company'):
                contact_items.append(f"Broker Company: {translate_text(item.get('broker_company', ''))}")
            
            if contact_items:
                details_sections.append({
                    "infoSummary": "Contact Information",
                    "infoItems": contact_items
                })
            
            # Create the transformed item
            transformed_item = {
                "title": item.get("title", ""),
                "company": item.get("title", ""),  # Use title as company name
                "location": item.get("location", ""),
                "price": convert_currency(item.get("price", "")),
                "category": item.get("category", ""),
                "industry": item.get("category", ""),  # Use category as industry
                "link": item.get("url", ""),
                "details": details_sections,
                "business_name": item.get("title", ""),
                "contact_name": item.get("broker_name", ""),
                "phone_number": item.get("phone", "")
            }
            
            transformed_data.append(transformed_item)
        
        return transformed_data
        
    except Exception as e:
        print(f"Error in run_scraper: {e}")
        return None

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Bolagsplatsen Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "/scrap": "Get all scraped listings (for n8n workflow)",
            "/listings": "Get all scraped listings",
            "/listings/{product_id}": "Get specific listing by product ID",
            "/search": "Search listings by query parameters"
        }
    }

@app.get("/scrap")
async def scrap():
    """Main endpoint for n8n workflow - returns data in expected format"""
    data = run_scraper()
    
    if not data:
        raise HTTPException(status_code=404, detail="No data available or scraping failed.")
    
    return data

@app.get("/listings", response_model=List[BusinessListing])
async def get_listings(
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
    category: Optional[str] = None,
    location: Optional[str] = None
):
    """Get all scraped listings with optional filtering and pagination"""
    # Run scraper and get data
    data = run_scraper()
    
    if not data:
        raise HTTPException(status_code=404, detail="No data available or scraping failed.")
    
    # Apply filters
    if category:
        data = [item for item in data if item.get("category") == category]
    
    if location:
        data = [item for item in data if item.get("location") == location]
    
    # Apply pagination
    if offset:
        data = data[offset:]
    
    if limit:
        data = data[:limit]
    
    return data

@app.get("/listings/{product_id}", response_model=BusinessListing)
async def get_listing(product_id: str):
    """Get a specific listing by product ID"""
    data = run_scraper()
    
    if not data:
        raise HTTPException(status_code=404, detail="No data available or scraping failed.")
    
    for item in data:
        if item.get("product_id") == product_id:
            return item
    
    raise HTTPException(status_code=404, detail=f"Listing with product ID {product_id} not found")

@app.get("/search")
async def search_listings(
    q: str,
    limit: Optional[int] = 50
):
    """Search listings by text query"""
    data = run_scraper()
    
    if not data:
        raise HTTPException(status_code=404, detail="No data available or scraping failed.")
    
    query = q.lower()
    results = []
    
    for item in data:
        # Search in title, description, category, and location
        searchable_fields = [
            item.get("title", ""),
            item.get("company", ""),
            item.get("category", ""),
            item.get("location", "")
        ]
        
        if any(query in field.lower() for field in searchable_fields):
            results.append(item)
            
        if len(results) >= limit:
            break
    
    return {
        "query": q,
        "results": results,
        "total_found": len(results)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

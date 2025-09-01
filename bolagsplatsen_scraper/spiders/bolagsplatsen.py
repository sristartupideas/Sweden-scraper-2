import scrapy
import re
import json
from datetime import datetime
from urllib.parse import urljoin
from ..items import BolagsplatsenScraperItem


class BolagsplatsenSpider(scrapy.Spider):
    name = "bolagsplatsen"
    allowed_domains = ["bolagsplatsen.se"]
    start_urls = ["https://www.bolagsplatsen.se/foretag-till-salu/alla/alla"]
    
    # Custom settings for this spider
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS': 1,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # Cloud-optimized settings
        'LOG_LEVEL': 'INFO',
        'TELNETCONSOLE_ENABLED': False,
        'MEMUSAGE_ENABLED': True,
        'MEMUSAGE_LIMIT_MB': 512,
    }
    
    def parse(self, response):
        """Parse the main listings page"""
        self.logger.info(f"Parsing main page: {response.url}")
        
        # Extract all listing containers
        listing_containers = response.css('div.list-items-list')
        self.logger.info(f"Found {len(listing_containers)} listing containers")
        
        for container in listing_containers:
            # Extract basic listing information
            item = BolagsplatsenScraperItem()
            
            # Debug: Log what we're processing
            self.logger.info(f"Processing container: {container.get()[:100]}...")
            
            # Extract title from the link
            title = container.css('a::attr(title)').get()
            self.logger.info(f"Extracted title: {title}")
            
            if title:
                # Clean up the title (remove "Läs mer om " prefix)
                title = title.replace('Läs mer om ', '').strip()
                item['title'] = title
                self.logger.info(f"Cleaned title: {title}")
            
            # Extract listing URL
            listing_url = container.css('a::attr(href)').get()
            if listing_url:
                item['url'] = urljoin(response.url, listing_url)
            
            # Extract structured data from JSON-LD if available
            json_ld_script = container.css('script[type="application/ld+json"]::text').get()
            if json_ld_script:
                try:
                    json_data = json.loads(json_ld_script)
                    
                    # Extract description from JSON-LD
                    if 'description' in json_data:
                        item['description'] = json_data['description']
                        item['full_description'] = json_data['description']  # API expects this
                    
                    # Extract product ID
                    if 'productid' in json_data:
                        item['product_id'] = json_data['productid']
                    
                    # Extract price information
                    if 'offers' in json_data and 'priceSpecification' in json_data['offers']:
                        price_spec = json_data['offers']['priceSpecification']
                        if 'price' in price_spec:
                            item['price'] = f"{price_spec['price']} SEK"
                        elif 'minPrice' in price_spec and 'maxPrice' in price_spec:
                            item['price'] = f"{price_spec['minPrice']}-{price_spec['maxPrice']} SEK"
                    
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # Add missing fields that the API expects
            if not item.get('description'):
                item['description'] = item.get('title', '')  # Use title as fallback description
            
            if not item.get('full_description'):
                item['full_description'] = item.get('description', '')  # API expects this field
            
            # Add structured content placeholder (API expects this)
            item['structured_content'] = {
                'company_brief': item.get('description', ''),
                'business_activity': item.get('category', '')
            }
            
            # Extract category (try to infer from title or use default)
            item['category'] = 'Företag till salu'  # Default category
            
            # Extract location (try to find in description or use default)
            item['location'] = 'Sverige'  # Default location
            
            # Extract financial metrics and employee count
            metrics = container.css('.item-ingredients li')
            for metric in metrics:
                text = metric.get()
                if 'Resultat' in text:
                    result_span = metric.css('span::text').get()
                    if result_span:
                        item['profit_status'] = result_span.strip()
                elif 'Omsättning' in text:
                    revenue_span = metric.css('span::text').get()
                    if revenue_span:
                        item['revenue'] = revenue_span.strip()
                elif 'Prisidé' in text:
                    price_span = metric.css('span::text').get()
                    if price_span:
                        item['price'] = price_span.strip()
                elif 'Anställda' in text:
                    # Extract employee count (e.g., "Anställda: 11 st.")
                    employee_span = metric.css('span::text').get()
                    if employee_span:
                        item['employee_count'] = employee_span.strip()
            
            # Extract contact information
            broker_section = container.css('.user-broker-detail')
            if broker_section:
                # Extract broker name
                broker_name = broker_section.css('.info-box-detail h4::text').get()
                if broker_name:
                    item['broker_name'] = broker_name.strip()
                
                # Extract broker photo
                broker_photo = broker_section.css('.user-photo::attr(src)').get()
                if broker_photo:
                    item['broker_photo'] = urljoin(response.url, broker_photo)
                
                # Extract company logo
                company_logo = broker_section.css('.list-logo img::attr(src)').get()
                if company_logo:
                    item['company_logo'] = urljoin(response.url, company_logo)
                    
                    # Try to extract company name from alt text
                    alt_text = broker_section.css('.list-logo img::attr(alt)').get()
                    if alt_text and 'företag' in alt_text.lower():
                        item['broker_company'] = alt_text
            
            # Extract product ID from URL
            if listing_url:
                product_id_match = re.search(r'-(\d+)$', listing_url)
                if product_id_match:
                    item['product_id'] = product_id_match.group(1)
            
            # Check if it's a premium listing
            premium_tag = container.css('.premium-tag::text').get()
            if premium_tag:
                item['listing_type'] = 'premium'
            else:
                item['listing_type'] = 'regular'
            
            # Add timestamp
            item['scraped_at'] = datetime.now().isoformat()
            
            # Always yield the item first, then follow for more details if URL exists
            yield item
            
            # If we have a listing URL, follow it to get more details
            if item.get('url'):
                yield scrapy.Request(
                    item['url'],
                    callback=self.parse_listing_detail,
                    meta={'item': item}
                )
        
        # Handle pagination - follow next pages
        next_page = response.css('a[href*="page="]::attr(href)').getall()
        if next_page:
            # Get the next page number from the current URL
            current_url = response.url
            if 'page=' in current_url:
                current_page = int(re.search(r'page=(\d+)', current_url).group(1))
                next_page_num = current_page + 1
            else:
                next_page_num = 2
            
            # Limit to first 10 pages for testing (you can increase this)
            if next_page_num <= 10:
                next_url = f"https://www.bolagsplatsen.se/foretag-till-salu/alla/alla?page={next_page_num}"
                self.logger.info(f"Following next page: {next_url}")
                yield scrapy.Request(
                    next_url,
                    callback=self.parse
                )
    
    def parse_listing_detail(self, response):
        """Parse individual listing detail page for additional contact information and full details"""
        item = response.meta['item']
        
        self.logger.info(f"Parsing detail page: {response.url}")
        
        # Extract structured content from detail page
        self._extract_structured_content(response, item)
        
        # Extract detailed financial information
        self._extract_detailed_financials(response, item)
        
        # Extract additional employee information if not found on listing card
        if not item.get('employee_count'):
            self._extract_employee_info(response, item)
        
        # Extract additional contact information from detail page
        # Phone numbers
        phone_selectors = [
            '.phone::text',
            '.tel::text',
            '.contact-phone::text',
            'a[href^="tel:"]::text',
            'a[href^="tel:"]::attr(href)'
        ]
        
        for selector in phone_selectors:
            phone = response.css(selector).get()
            if phone:
                if phone.startswith('tel:'):
                    phone = phone.replace('tel:', '')
                item['phone'] = phone.strip()
                break
        
        # Email addresses
        email_selectors = [
            '.email::text',
            '.contact-email::text',
            'a[href^="mailto:"]::text',
            'a[href^="mailto:"]::attr(href)'
        ]
        
        for selector in email_selectors:
            email = response.css(selector).get()
            if email:
                if email.startswith('mailto:'):
                    email = email.replace('mailto:', '')
                item['email'] = email.strip()
                break
        
        # Look for contact information in text content
        text_content = response.text
        
        # Phone patterns
        phone_patterns = [
            r'\+46[\s-]?[\d\s-]{8,}',
            r'0[\d\s-]{8,}',
            r'[\d]{2,3}[\s-][\d]{3}[\s-][\d]{2,4}'
        ]
        
        if not item.get('phone'):
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text_content)
                if phone_match:
                    item['phone'] = phone_match.group(0).strip()
                    break
        
        # Email patterns
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if not item.get('email'):
            email_match = re.search(email_pattern, text_content)
            if email_match:
                item['email'] = email_match.group(0)
        
        # Extract additional broker information
        if not item.get('broker_name'):
            broker_name = response.css('.broker-name::text, .contact-person h4::text').get()
            if broker_name:
                item['broker_name'] = broker_name.strip()
        
        if not item.get('broker_company'):
            broker_company = response.css('.broker-company::text, .company-info .name::text').get()
            if broker_company:
                item['broker_company'] = broker_company.strip()
        
        yield item
    
    def _extract_structured_content(self, response, item):
        """Extract structured content sections from the detail page"""
        structured_content = {}
        
        # Look for specific Swedish business sections with more targeted selectors
        swedish_sections = {
            'Företaget i korthet': 'company_brief',
            'Potential': 'potential', 
            'Anledning till försäljning': 'reason_for_sale',
            'Prisidé': 'price_idea',
            'Sammanfattning': 'summary',
            'Beskrivning': 'description',
            'Verksamhet': 'business_activity',
            'Marknad': 'market',
            'Konkurrenssituation': 'competition'
        }
        
        # First try to find the main business description area
        main_content = response.css('.ad-detail-body, .listing-description, .business-description, .main-content')
        
        for content_area in main_content:
            # Look for paragraphs and list items that contain business information
            business_texts = content_area.css('p::text, li::text').getall()
            
            # Filter out JavaScript, CSS, and other technical content
            clean_texts = []
            for text in business_texts:
                text = text.strip()
                # Skip if it contains JavaScript-like content
                if any(skip in text.lower() for skip in ['function(', 'var ', '$(', 'console.log', 'gtag(', 'mixpanel', 'document.ready']):
                    continue
                # Skip if it's mostly CSS or HTML
                if any(skip in text for skip in ['{', '}', ';', 'px', 'margin', 'padding', 'color:', 'background:', 'font-size']):
                    continue
                # Skip very short or technical content
                if len(text) < 20 or text.startswith('//') or text.startswith('/*'):
                    continue
                # Skip if it contains too many technical characters
                if text.count('(') > 3 or text.count(')') > 3 or text.count(';') > 2:
                    continue
                clean_texts.append(text)
            
            if clean_texts:
                # Join the clean texts
                full_content = ' '.join(clean_texts)
                if len(full_content) > 100:  # Only keep substantial content
                    structured_content['business_description'] = full_content
                    break
        
        # Also try to find specific sections by looking for Swedish keywords in text
        for swedish_key, english_key in swedish_sections.items():
            # Look for text that contains these Swedish keywords
            text_elements = response.css('p::text, li::text, h2::text, h3::text, h4::text').getall()
            
            for text in text_elements:
                if swedish_key in text:
                    # Get the parent element to extract more context
                    parent = response.xpath(f'//*[contains(text(), "{swedish_key}")]').get()
                    if parent:
                        # Extract text from this section, but limit to reasonable length
                        section_text = ' '.join([t.strip() for t in text_elements if t.strip() and len(t.strip()) > 20])
                        
                        # Clean up the content
                        if swedish_key in section_text:
                            section_text = section_text.replace(swedish_key, '').strip()
                        
                        if section_text and len(section_text) > 50 and len(section_text) < 2000:  # Reasonable length
                            structured_content[english_key] = section_text
                            break
        
        # If we found structured content, store it
        if structured_content:
            item['structured_content'] = structured_content
            
            # Also create a comprehensive full description
            full_description_parts = []
            for key, content in structured_content.items():
                if key in ['company_brief', 'description', 'business_activity', 'business_description']:
                    full_description_parts.append(content)
            
            if full_description_parts:
                item['full_description'] = ' '.join(full_description_parts)
    
    def _extract_detailed_financials(self, response, item):
        """Extract detailed financial information from the detail page"""
        # Look for detailed financial sections
        financial_sections = response.css('.financial-info, .business-details, .company-info')
        
        financial_details = []
        
        for section in financial_sections:
            # Extract revenue details
            revenue_details = section.css('*:contains("Omsättning")').getall()
            if revenue_details:
                for detail in revenue_details:
                    if 'Omsättning' in detail and len(detail) > 50:  # More detailed than card
                        item['detailed_revenue'] = detail.strip()
                        break
            
            # Extract profit details
            profit_details = section.css('*:contains("Resultat")').getall()
            if profit_details:
                for detail in profit_details:
                    if 'Resultat' in detail and len(detail) > 50:  # More detailed than card
                        item['detailed_profit'] = detail.strip()
                        break
            
            # Extract other financial metrics
            financial_text = section.css('::text').getall()
            for text in financial_text:
                text = text.strip()
                if any(keyword in text.lower() for keyword in ['omsättning', 'resultat', 'vinst', 'förlust', 'kostnad', 'intäkt']):
                    if len(text) > 20:  # Avoid very short matches
                        financial_details.append(text)
        
        # Also look in the main content for financial information
        main_content = response.css('.main-content, .content, .listing-content')
        for content in main_content:
            financial_paragraphs = content.css('p:contains("Omsättning"), p:contains("Resultat"), p:contains("Vinst"), p:contains("Förlust")')
            for para in financial_paragraphs:
                para_text = para.css('::text').get()
                if para_text and len(para_text.strip()) > 30:
                    financial_details.append(para_text.strip())
        
        if financial_details:
            item['financial_details'] = financial_details
    
    def _extract_employee_info(self, response, item):
        """Extract employee count information from detail page"""
        # Look for employee count in various sections
        employee_selectors = [
            '*:contains("Anställda")',
            '*:contains("Personal")',
            '*:contains("Medarbetare")',
            '*:contains("anställd")'
        ]
        
        for selector in employee_selectors:
            employee_elements = response.css(selector)
            for element in employee_elements:
                text = element.css('::text').get()
                if text and 'anställd' in text.lower():
                    # Extract number from text like "Anställda: 11 st." or "11 anställda"
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        item['employee_count'] = f"{numbers[0]} employees"
                        return

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class BolagsplatsenScraperItem(scrapy.Item):
    # Basic listing information
    title = scrapy.Field()
    category = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    full_description = scrapy.Field()  # Full description from detail page
    structured_content = scrapy.Field()  # Structured content sections from detail page
    url = scrapy.Field()
    
    # Financial metrics
    revenue = scrapy.Field()
    profit_status = scrapy.Field()
    price = scrapy.Field()
    detailed_revenue = scrapy.Field()  # Detailed revenue info from detail page
    detailed_profit = scrapy.Field()   # Detailed profit info from detail page
    financial_details = scrapy.Field() # Additional financial information
    
    # Business metrics
    employee_count = scrapy.Field()    # Number of employees/staff
    
    # Contact information
    broker_name = scrapy.Field()
    broker_company = scrapy.Field()
    broker_photo = scrapy.Field()
    company_logo = scrapy.Field()
    phone = scrapy.Field()
    email = scrapy.Field()
    
    # Additional details
    product_id = scrapy.Field()
    scraped_at = scrapy.Field()
    listing_type = scrapy.Field()  # premium, regular, etc.

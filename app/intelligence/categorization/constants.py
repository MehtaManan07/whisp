"""
Constants for the Category Classification System
Contains standardized category taxonomy and merchant rule patterns
"""

# Standardized category taxonomy
CATEGORIES = {
    "Food & Dining": ["Groceries", "Restaurants", "Cafe/Coffee", "Fast Food", "Alcohol/Bars"],
    "Transportation": ["Fuel", "Public Transit", "Ride Share", "Taxi", "Parking", "Vehicle Maintenance"],
    "Shopping": ["Clothing", "Electronics", "Home & Garden", "Online Shopping", "General Merchandise"],
    "Bills & Utilities": ["Electricity", "Water", "Gas", "Internet", "Phone", "Rent/Mortgage"],
    "Entertainment": ["Movies", "Streaming", "Games", "Events", "Hobbies"],
    "Healthcare": ["Doctor", "Pharmacy", "Hospital", "Dental", "Vision"],
    "Education": ["Tuition", "Books", "Courses", "Supplies"],
    "Travel": ["Hotels", "Flights", "Tours", "Travel Insurance"],
    "Personal Care": ["Salon", "Spa", "Gym", "Beauty Products"],
    "Other": ["Miscellaneous"]
}

# Rule-based merchant patterns (expand based on usage)
MERCHANT_RULES = {
    # Food & Dining
    r'starbucks|cafe coffee day|ccd|dunkin|barista|costa|coffee|cafe': 
        ("Food & Dining", "Cafe/Coffee"),
    r'mcdonald|mcdonalds|burger king|kfc|domino|pizza hut|subway|taco bell|wendy': 
        ("Food & Dining", "Fast Food"),
    r'zomato|swiggy|ubereats|doordash|foodpanda|restaurant|dining|eatery': 
        ("Food & Dining", "Restaurants"),
    r'dmart|bigbasket|grofers|blinkit|instamart|zepto|grocery|groceries|supermarket|walmart|target|whole foods|kroger|safeway': 
        ("Food & Dining", "Groceries"),
    r'bar|pub|brewery|wine|liquor|beer': 
        ("Food & Dining", "Alcohol/Bars"),
    
    # Transportation
    r'uber|ola|lyft|rapido|grab|taxi|cab': 
        ("Transportation", "Ride Share"),
    r'shell|bp|indian oil|iocl|bharat petroleum|bpcl|hpcl|petrol|gas station|fuel': 
        ("Transportation", "Fuel"),
    r'metro|railway|irctc|train|bus|public transport': 
        ("Transportation", "Public Transit"),
    r'parking|toll': 
        ("Transportation", "Parking"),
    
    # Shopping
    r'amazon|flipkart|myntra|ajio|nykaa|meesho|ebay|etsy': 
        ("Shopping", "Online Shopping"),
    r'nike|adidas|zara|h&m|uniqlo|gap|clothing|fashion|apparel': 
        ("Shopping", "Clothing"),
    r'apple store|best buy|croma|reliance digital|electronics|laptop|phone': 
        ("Shopping", "Electronics"),
    
    # Bills & Utilities
    r'electricity|power|utility|bescom|tata power': 
        ("Bills & Utilities", "Electricity"),
    r'internet|wifi|broadband|jio fiber|airtel fiber': 
        ("Bills & Utilities", "Internet"),
    r'jio|airtel|vodafone|verizon|att|tmobile|phone bill|mobile': 
        ("Bills & Utilities", "Phone"),
    r'rent|lease|mortgage': 
        ("Bills & Utilities", "Rent/Mortgage"),
    
    # Entertainment
    r'netflix|prime video|hotstar|disney|hbo|spotify|apple music|youtube premium|subscription': 
        ("Entertainment", "Streaming"),
    r'movie|cinema|theatre|pvr|inox|amc': 
        ("Entertainment", "Movies"),
    r'steam|playstation|xbox|nintendo|gaming': 
        ("Entertainment", "Games"),
    
    # Healthcare
    r'apollo|fortis|max hospital|hospital|clinic|doctor|physician': 
        ("Healthcare", "Doctor"),
    r'pharmacy|medical|medicine|drug store|cvs|walgreens|apollo pharmacy': 
        ("Healthcare", "Pharmacy"),
    r'dentist|dental': 
        ("Healthcare", "Dental"),
    
    # Personal Care
    r'gym|fitness|workout|yoga|crossfit|planet fitness': 
        ("Personal Care", "Gym"),
    r'salon|barber|haircut|spa|massage': 
        ("Personal Care", "Salon"),
}

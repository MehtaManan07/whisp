"""
Constants for the Category Classification System
Contains standardized category taxonomy and known merchant mappings
"""

# Standardized category taxonomy (expanded)
CATEGORIES = {
    "Food & Dining": ["Groceries", "Restaurants", "Cafe/Coffee", "Fast Food", "Alcohol/Bars", "Food Delivery"],
    "Transportation": ["Fuel", "Public Transit", "Ride Share", "Taxi", "Parking", "Vehicle Maintenance", "Tolls"],
    "Shopping": ["Clothing", "Electronics", "Home & Garden", "Online Shopping", "General Merchandise"],
    "Bills & Utilities": ["Electricity", "Water", "Gas", "Internet", "Phone", "Rent/Mortgage", "Insurance"],
    "Entertainment": ["Movies", "Streaming", "Games", "Events", "Hobbies", "Sports"],
    "Healthcare": ["Doctor", "Pharmacy", "Hospital", "Dental", "Vision", "Mental Health"],
    "Education": ["Tuition", "Books", "Courses", "Supplies", "Training"],
    "Travel": ["Hotels", "Flights", "Tours", "Travel Insurance", "Car Rental"],
    "Personal Care": ["Salon", "Spa", "Gym", "Beauty Products", "Grooming"],
    "Business": ["Office Supplies", "Professional Services", "Business Travel", "Client Entertainment", "Software/Tools", "Coworking"],
    "Investments": ["Stocks", "Mutual Funds", "Fixed Deposits", "Crypto", "Gold"],
    "Gifts & Donations": ["Gifts", "Charity", "Donations", "Tips"],
    "Other": ["Miscellaneous", "Uncategorized"],
}

# Known merchants - EXACT MATCH only (no regex patterns)
# These are verified merchant/vendor names that map to specific categories
# For descriptions/notes, we use LLM classification instead
KNOWN_MERCHANTS = {
    # Food & Dining - Cafe/Coffee
    "starbucks": ("Food & Dining", "Cafe/Coffee"),
    "cafe coffee day": ("Food & Dining", "Cafe/Coffee"),
    "ccd": ("Food & Dining", "Cafe/Coffee"),
    "dunkin": ("Food & Dining", "Cafe/Coffee"),
    "dunkin donuts": ("Food & Dining", "Cafe/Coffee"),
    "costa": ("Food & Dining", "Cafe/Coffee"),
    "costa coffee": ("Food & Dining", "Cafe/Coffee"),
    "barista": ("Food & Dining", "Cafe/Coffee"),
    "blue tokai": ("Food & Dining", "Cafe/Coffee"),
    "third wave": ("Food & Dining", "Cafe/Coffee"),
    "tim hortons": ("Food & Dining", "Cafe/Coffee"),
    
    # Food & Dining - Fast Food
    "mcdonalds": ("Food & Dining", "Fast Food"),
    "mcdonald's": ("Food & Dining", "Fast Food"),
    "burger king": ("Food & Dining", "Fast Food"),
    "kfc": ("Food & Dining", "Fast Food"),
    "dominos": ("Food & Dining", "Fast Food"),
    "domino's": ("Food & Dining", "Fast Food"),
    "pizza hut": ("Food & Dining", "Fast Food"),
    "subway": ("Food & Dining", "Fast Food"),
    "taco bell": ("Food & Dining", "Fast Food"),
    "wendys": ("Food & Dining", "Fast Food"),
    "wendy's": ("Food & Dining", "Fast Food"),
    "popeyes": ("Food & Dining", "Fast Food"),
    "chick-fil-a": ("Food & Dining", "Fast Food"),
    
    # Food & Dining - Food Delivery
    "zomato": ("Food & Dining", "Food Delivery"),
    "swiggy": ("Food & Dining", "Food Delivery"),
    "ubereats": ("Food & Dining", "Food Delivery"),
    "uber eats": ("Food & Dining", "Food Delivery"),
    "doordash": ("Food & Dining", "Food Delivery"),
    "foodpanda": ("Food & Dining", "Food Delivery"),
    "grubhub": ("Food & Dining", "Food Delivery"),
    "deliveroo": ("Food & Dining", "Food Delivery"),
    
    # Food & Dining - Groceries
    "dmart": ("Food & Dining", "Groceries"),
    "d-mart": ("Food & Dining", "Groceries"),
    "bigbasket": ("Food & Dining", "Groceries"),
    "big basket": ("Food & Dining", "Groceries"),
    "grofers": ("Food & Dining", "Groceries"),
    "blinkit": ("Food & Dining", "Groceries"),
    "instamart": ("Food & Dining", "Groceries"),
    "zepto": ("Food & Dining", "Groceries"),
    "walmart": ("Food & Dining", "Groceries"),
    "target": ("Food & Dining", "Groceries"),
    "whole foods": ("Food & Dining", "Groceries"),
    "kroger": ("Food & Dining", "Groceries"),
    "safeway": ("Food & Dining", "Groceries"),
    "costco": ("Food & Dining", "Groceries"),
    "trader joes": ("Food & Dining", "Groceries"),
    "trader joe's": ("Food & Dining", "Groceries"),
    "aldi": ("Food & Dining", "Groceries"),
    "reliance fresh": ("Food & Dining", "Groceries"),
    "more supermarket": ("Food & Dining", "Groceries"),
    "nature's basket": ("Food & Dining", "Groceries"),
    
    # Transportation - Ride Share
    "uber": ("Transportation", "Ride Share"),
    "ola": ("Transportation", "Ride Share"),
    "lyft": ("Transportation", "Ride Share"),
    "rapido": ("Transportation", "Ride Share"),
    "grab": ("Transportation", "Ride Share"),
    "didi": ("Transportation", "Ride Share"),
    "bolt": ("Transportation", "Ride Share"),
    
    # Transportation - Fuel
    "shell": ("Transportation", "Fuel"),
    "bp": ("Transportation", "Fuel"),
    "indian oil": ("Transportation", "Fuel"),
    "iocl": ("Transportation", "Fuel"),
    "bharat petroleum": ("Transportation", "Fuel"),
    "bpcl": ("Transportation", "Fuel"),
    "hpcl": ("Transportation", "Fuel"),
    "hp petrol": ("Transportation", "Fuel"),
    "chevron": ("Transportation", "Fuel"),
    "exxon": ("Transportation", "Fuel"),
    "mobil": ("Transportation", "Fuel"),
    
    # Transportation - Public Transit
    "irctc": ("Transportation", "Public Transit"),
    "indian railways": ("Transportation", "Public Transit"),
    "metro card": ("Transportation", "Public Transit"),
    "dmrc": ("Transportation", "Public Transit"),
    "bmtc": ("Transportation", "Public Transit"),
    "best bus": ("Transportation", "Public Transit"),
    "mta": ("Transportation", "Public Transit"),
    "amtrak": ("Transportation", "Public Transit"),
    
    # Shopping - Online
    "amazon": ("Shopping", "Online Shopping"),
    "flipkart": ("Shopping", "Online Shopping"),
    "myntra": ("Shopping", "Online Shopping"),
    "ajio": ("Shopping", "Online Shopping"),
    "nykaa": ("Shopping", "Online Shopping"),
    "meesho": ("Shopping", "Online Shopping"),
    "ebay": ("Shopping", "Online Shopping"),
    "etsy": ("Shopping", "Online Shopping"),
    "alibaba": ("Shopping", "Online Shopping"),
    "aliexpress": ("Shopping", "Online Shopping"),
    "shopify": ("Shopping", "Online Shopping"),
    
    # Shopping - Clothing
    "nike": ("Shopping", "Clothing"),
    "adidas": ("Shopping", "Clothing"),
    "zara": ("Shopping", "Clothing"),
    "h&m": ("Shopping", "Clothing"),
    "uniqlo": ("Shopping", "Clothing"),
    "gap": ("Shopping", "Clothing"),
    "levis": ("Shopping", "Clothing"),
    "levi's": ("Shopping", "Clothing"),
    "puma": ("Shopping", "Clothing"),
    "reebok": ("Shopping", "Clothing"),
    
    # Shopping - Electronics
    "apple store": ("Shopping", "Electronics"),
    "apple": ("Shopping", "Electronics"),
    "best buy": ("Shopping", "Electronics"),
    "croma": ("Shopping", "Electronics"),
    "reliance digital": ("Shopping", "Electronics"),
    "vijay sales": ("Shopping", "Electronics"),
    "samsung store": ("Shopping", "Electronics"),
    
    # Bills & Utilities
    "bescom": ("Bills & Utilities", "Electricity"),
    "tata power": ("Bills & Utilities", "Electricity"),
    "adani electricity": ("Bills & Utilities", "Electricity"),
    "jio fiber": ("Bills & Utilities", "Internet"),
    "airtel fiber": ("Bills & Utilities", "Internet"),
    "act fibernet": ("Bills & Utilities", "Internet"),
    "jio": ("Bills & Utilities", "Phone"),
    "airtel": ("Bills & Utilities", "Phone"),
    "vodafone": ("Bills & Utilities", "Phone"),
    "vi": ("Bills & Utilities", "Phone"),
    "verizon": ("Bills & Utilities", "Phone"),
    "at&t": ("Bills & Utilities", "Phone"),
    "t-mobile": ("Bills & Utilities", "Phone"),
    
    # Entertainment - Streaming
    "netflix": ("Entertainment", "Streaming"),
    "prime video": ("Entertainment", "Streaming"),
    "amazon prime": ("Entertainment", "Streaming"),
    "hotstar": ("Entertainment", "Streaming"),
    "disney+": ("Entertainment", "Streaming"),
    "disney plus": ("Entertainment", "Streaming"),
    "hbo": ("Entertainment", "Streaming"),
    "hbo max": ("Entertainment", "Streaming"),
    "spotify": ("Entertainment", "Streaming"),
    "apple music": ("Entertainment", "Streaming"),
    "youtube premium": ("Entertainment", "Streaming"),
    "youtube music": ("Entertainment", "Streaming"),
    "zee5": ("Entertainment", "Streaming"),
    "sonyliv": ("Entertainment", "Streaming"),
    
    # Entertainment - Movies
    "pvr": ("Entertainment", "Movies"),
    "pvr cinemas": ("Entertainment", "Movies"),
    "inox": ("Entertainment", "Movies"),
    "amc": ("Entertainment", "Movies"),
    "cinepolis": ("Entertainment", "Movies"),
    "bookmyshow": ("Entertainment", "Movies"),
    
    # Entertainment - Games
    "steam": ("Entertainment", "Games"),
    "playstation": ("Entertainment", "Games"),
    "psn": ("Entertainment", "Games"),
    "xbox": ("Entertainment", "Games"),
    "nintendo": ("Entertainment", "Games"),
    "epic games": ("Entertainment", "Games"),
    
    # Healthcare
    "apollo": ("Healthcare", "Doctor"),
    "apollo hospital": ("Healthcare", "Hospital"),
    "fortis": ("Healthcare", "Hospital"),
    "max hospital": ("Healthcare", "Hospital"),
    "medanta": ("Healthcare", "Hospital"),
    "manipal hospital": ("Healthcare", "Hospital"),
    "cvs": ("Healthcare", "Pharmacy"),
    "walgreens": ("Healthcare", "Pharmacy"),
    "apollo pharmacy": ("Healthcare", "Pharmacy"),
    "medplus": ("Healthcare", "Pharmacy"),
    "netmeds": ("Healthcare", "Pharmacy"),
    "pharmeasy": ("Healthcare", "Pharmacy"),
    "1mg": ("Healthcare", "Pharmacy"),
    
    # Personal Care
    "planet fitness": ("Personal Care", "Gym"),
    "gold's gym": ("Personal Care", "Gym"),
    "cult.fit": ("Personal Care", "Gym"),
    "cultfit": ("Personal Care", "Gym"),
    "anytime fitness": ("Personal Care", "Gym"),
    
    # Travel
    "makemytrip": ("Travel", "Flights"),
    "goibibo": ("Travel", "Flights"),
    "cleartrip": ("Travel", "Flights"),
    "yatra": ("Travel", "Flights"),
    "expedia": ("Travel", "Flights"),
    "booking.com": ("Travel", "Hotels"),
    "airbnb": ("Travel", "Hotels"),
    "oyo": ("Travel", "Hotels"),
    "trivago": ("Travel", "Hotels"),
    "marriott": ("Travel", "Hotels"),
    "hilton": ("Travel", "Hotels"),
    "taj hotels": ("Travel", "Hotels"),
    "oberoi": ("Travel", "Hotels"),
    
    # Business
    "wework": ("Business", "Coworking"),
    "91springboard": ("Business", "Coworking"),
    "awfis": ("Business", "Coworking"),
    "regus": ("Business", "Coworking"),
    "staples": ("Business", "Office Supplies"),
    "office depot": ("Business", "Office Supplies"),
}


def get_all_subcategories() -> list[str]:
    """Get a flat list of all subcategories."""
    return [sub for subs in CATEGORIES.values() for sub in subs]


def get_category_for_subcategory(subcategory: str) -> str | None:
    """Find the parent category for a given subcategory."""
    for category, subcategories in CATEGORIES.items():
        if subcategory in subcategories:
            return category
    return None


def is_valid_category(category: str, subcategory: str) -> bool:
    """Check if a category/subcategory combination is valid."""
    if category not in CATEGORIES:
        return False
    return subcategory in CATEGORIES[category]

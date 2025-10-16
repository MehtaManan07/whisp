"""Timezone detection utilities for determining user timezone from phone number."""


# Mapping of phone number prefixes to timezones for 10 famous countries
# Format: "prefix": "IANA_timezone"
PHONE_PREFIX_TIMEZONE_MAP = {
    "+91": "Asia/Kolkata",      # India
    "+81": "Asia/Tokyo",         # Japan
    "+44": "Europe/London",      # United Kingdom
    "+1": "America/New_York",    # USA/Canada (default to Eastern Time)
    "+61": "Australia/Sydney",   # Australia
    "+65": "Asia/Singapore",     # Singapore
    "+971": "Asia/Dubai",        # UAE
    "+49": "Europe/Berlin",      # Germany
    "+33": "Europe/Paris",       # France
    "+86": "Asia/Shanghai",      # China
}


def detect_timezone_from_phone(phone_number: str) -> str:
    """
    Detect timezone from phone number using country calling code prefix.
    
    Args:
        phone_number: International phone number (e.g., "+919876543210")
    
    Returns:
        IANA timezone string (e.g., "Asia/Kolkata"), defaults to "UTC" if detection fails
    
    Examples:
        >>> detect_timezone_from_phone("+919876543210")
        'Asia/Kolkata'
        >>> detect_timezone_from_phone("+447700900000")
        'Europe/London'
        >>> detect_timezone_from_phone("+819012345678")
        'Asia/Tokyo'
    """
    if not phone_number:
        return "UTC"
    
    # Normalize phone number (strip spaces and handle edge cases)
    phone_number = phone_number.strip().replace(" ", "").replace("-", "")
    
    # Ensure it starts with +
    if not phone_number.startswith("+"):
        return "UTC"
    
    # Check each prefix (longest first to handle overlapping prefixes)
    # Sort by length descending to match longer prefixes first (e.g., +971 before +1)
    sorted_prefixes = sorted(PHONE_PREFIX_TIMEZONE_MAP.keys(), key=len, reverse=True)
    
    for prefix in sorted_prefixes:
        if phone_number.startswith(prefix):
            return PHONE_PREFIX_TIMEZONE_MAP[prefix]
    
    # No match found
    return "UTC"


def get_timezone_display_name(timezone: str) -> str:
    """
    Get a human-readable display name for a timezone.
    
    Args:
        timezone: IANA timezone string
    
    Returns:
        Human-readable timezone name
    """
    display_names = {
        "Asia/Kolkata": "India Standard Time (IST, UTC+5:30)",
        "Asia/Tokyo": "Japan Standard Time (JST, UTC+9)",
        "Europe/London": "British Time (GMT/BST, UTC+0/+1)",
        "America/Toronto": "Eastern Time (ET, UTC-5/-4)",
        "America/New_York": "Eastern Time (ET, UTC-5/-4)",
        "America/Vancouver": "Pacific Time (PT, UTC-8/-7)",
        "Australia/Sydney": "Australian Eastern Time (AEDT, UTC+10/+11)",
        "Asia/Singapore": "Singapore Time (SGT, UTC+8)",
        "UTC": "Coordinated Universal Time (UTC+0)",
    }
    
    return display_names.get(timezone, f"{timezone}")


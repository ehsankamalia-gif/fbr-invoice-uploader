import re
import unicodedata

def normalize_business_name(name: str) -> str:
    """
    Normalizes a business name for uniqueness checking.
    1. Converts to lowercase.
    2. Normalizes Unicode characters (NFKD).
    3. Removes all non-alphanumeric characters (spaces, punctuation, symbols).
    
    Example: "Honda Center!" -> "hondacenter"
    """
    if not name:
        return ""
    
    # 1. Lowercase
    name = name.lower()
    
    # 2. Unicode normalization (e.g. é -> e)
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    
    # 3. Remove non-alphanumeric (keep only a-z, 0-9)
    # This removes spaces, punctuation, dashes, etc.
    name = re.sub(r'[^a-z0-9]', '', name)
    
    return name

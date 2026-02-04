import re
import fitz  # PyMuPDF

def extract_registration_code(pdf_path: str) -> tuple:
    """
    Extract registration code, license type, and size information from FortiGate/FortiAuthenticator/FortiIdentity Cloud license PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Tuple of (registration_code, license_type, size_info) or error message
    """
    try:
        # Open the PDF file
        doc = fitz.open(pdf_path)
        full_text = ""

        # Iterate through pages and extract text
        for page in doc:
            full_text += page.get_text()

        # First, try to find the Contract Registration Code pattern (12 alphanumeric characters)
        # Looking for pattern like 4456UL989056 (mix of digits and letters)
        # This pattern ensures we have both letters and digits to avoid matching regular words
        contract_code_pattern = r'[A-Z0-9]{12}'

        # Find ALL matches instead of just the first one
        all_matches = re.findall(contract_code_pattern, full_text)

        # Look for the valid one (contains both letters and digits)
        valid_contract_code = None
        for match in all_matches:
            has_letters = any(c.isalpha() for c in match)
            has_digits = any(c.isdigit() for c in match)
            if has_letters and has_digits:
                valid_contract_code = match
                break

        registration_code = "Registration code not found."
        if valid_contract_code:
            registration_code = valid_contract_code
        else:
            # If no contract code found, try the traditional format
            # Define the regex for the registration code:
            # Format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXXX (5-5-5-5-6 pattern)
            code_pattern = r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{6}'

            # Search for the pattern
            match = re.search(code_pattern, full_text)

            if match:
                registration_code = match.group(0)

        # Determine license type based on keywords in the text
        license_type = "Unknown"
        size_info = None
        full_text_lower = full_text.lower()

        if 'fortigate' in full_text_lower or 'fg-' in full_text_lower or 'fgvm' in full_text_lower:
            license_type = "FortiGate"
        elif 'fortiauthenticator' in full_text_lower or 'fac-' in full_text_lower or 'facvm' in full_text_lower:
            license_type = "FortiAuthenticator"
        elif 'fortiidentity cloud' in full_text_lower or 'idcld' in full_text_lower:
            # Specifically identify FortiIdentity Cloud codes
            license_type = "FortiIdentity Cloud"
            # Extract size information for FortiIdentity Cloud codes
            # Looking for pattern like "Units of Contract :10000"
            size_pattern = r'units of contract\s*:\s*(\d+)'
            size_match = re.search(size_pattern, full_text_lower)
            if size_match:
                size_info = size_match.group(1)
        elif valid_contract_code and 'contract' in full_text_lower and 'registration' in full_text_lower:
            # If it's a contract registration code, we can classify it as Contract type
            # For now, we'll still use Unknown to maintain compatibility, but we could create a specific type
            license_type = "Unknown"

        return (registration_code, license_type, size_info)
    except Exception as e:
        # Log the error (would need proper logger setup)
        return (f"Error extracting code: {str(e)}", "Unknown", None)
    finally:
        # Close the document if it was opened
        try:
            doc.close()
        except:
            pass

if __name__ == "__main__":
    result = extract_registration_code('/home/fortinet/mtp/tmp/9193BB553029.pdf')
    print('Result for 9193BB553029.pdf:', result)
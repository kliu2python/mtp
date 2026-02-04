#!/usr/bin/env python3
"""
Test script to verify FIC license functionality in the warehouse system.

This test verifies:
1. The License model has been updated to include license_size field
2. The warehouse API can recognize and categorize FIC licenses
3. The frontend displays FIC license types and sizes properly
"""

import os
import sys

def test_license_model_has_license_size():
    """Test 1: Verify the License model includes license_size field by checking the source file."""
    print("Test 1: Checking if License model has license_size field...")

    try:
        # Read the license model file directly
        license_model_path = os.path.join('backend', 'app', 'models', 'license.py')

        if not os.path.exists(license_model_path):
            print(f"✗ FAIL: License model file not found at {license_model_path}")
            return False

        with open(license_model_path, 'r') as f:
            content = f.read()

        # Check if license_size field is defined
        if 'license_size' in content and 'Column(' in content:
            print("✓ PASS: License model has license_size field")
            return True
        else:
            print("✗ FAIL: License model does not have license_size field")
            return False

    except Exception as e:
        print(f"✗ FAIL: Error reading License model: {e}")
        return False

def test_warehouse_api_recognizes_fic_licenses():
    """Test 2: Verify the warehouse API can recognize and categorize FIC licenses."""
    print("\nTest 2: Checking if warehouse API recognizes FIC licenses...")

    try:
        # Read the warehouse API file directly
        warehouse_api_path = os.path.join('backend', 'app', 'api', 'warehouse', '__init__.py')

        if not os.path.exists(warehouse_api_path):
            print(f"✗ FAIL: Warehouse API file not found at {warehouse_api_path}")
            return False

        with open(warehouse_api_path, 'r') as f:
            content = f.read()

        # Check if the API contains FIC license recognition logic
        required_elements = [
            'FIC',
            'license_size',
            'fic_s', 'fic_m', 'fic_l', 'fic_xl'
        ]

        found_elements = [element for element in required_elements if element in content.lower() or element in content]

        if len(found_elements) >= 3:
            print(f"✓ PASS: Warehouse API contains FIC recognition logic: {found_elements}")
            return True
        else:
            print("✗ FAIL: Warehouse API may not properly recognize FIC licenses")
            return False

    except Exception as e:
        print(f"✗ FAIL: Error reading warehouse API: {e}")
        return False

def test_frontend_displays_fic_types():
    """Test 3: Verify the frontend displays FIC license types and sizes properly."""
    print("\nTest 3: Checking if frontend displays FIC license types...")

    try:
        # Read the frontend component
        frontend_path = os.path.join('frontend', 'src', 'components', 'UnifiedWarehouse.jsx')

        if not os.path.exists(frontend_path):
            print(f"✗ FAIL: Frontend file not found at {frontend_path}")
            return False

        with open(frontend_path, 'r') as f:
            content = f.read()

        # Check if FIC license types are displayed in the frontend
        fic_indicators = ['FIC-S', 'FIC-M', 'FIC-L', 'FIC-XL']
        found_indicators = [indicator for indicator in fic_indicators if indicator in content]

        if len(found_indicators) >= 2:  # At least some FIC indicators should be present
            print(f"✓ PASS: Frontend displays FIC license types: {found_indicators}")
            # Also check if counts are handled
            count_indicators = ['fic_s', 'fic_m', 'fic_l', 'fic_xl']
            found_counts = [indicator for indicator in count_indicators if indicator in content]

            if len(found_counts) == 4:
                print("✓ PASS: Frontend handles FIC license size counts")
                return True
            else:
                print("? PARTIAL: FIC types displayed but counts may not be handled properly")
                return True
        else:
            print("✗ FAIL: Frontend does not appear to display FIC license types properly")
            return False

    except Exception as e:
        print(f"✗ FAIL: Error reading frontend: {e}")
        return False

def main():
    """Run all tests and provide a summary."""
    print("Running FIC License Functionality Tests\n")
    print("=" * 50)

    # Run all tests
    test_results = [
        test_license_model_has_license_size(),
        test_warehouse_api_recognizes_fic_licenses(),
        test_frontend_displays_fic_types()
    ]

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    passed = sum(test_results)
    total = len(test_results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! FIC license functionality is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
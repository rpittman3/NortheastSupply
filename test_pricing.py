#!/usr/bin/env python3
"""
Test script to verify that all pricing bugs are fixed.
This tests the compute_price function directly.
"""

# Import the necessary modules
from decimal import Decimal
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our app and models
from app import app, db
from admin_routes import compute_price
from models import Category

def test_override_markup_zero():
    """Test that 0% override markup is respected (was previously ignored)"""
    print("Testing 0% override markup...")
    
    with app.app_context():
        # Create a test category with 20% markup
        test_category = Category(name="Test Category", slug="test", markup=Decimal('20.0'))
        db.session.add(test_category)
        db.session.commit()
        
        # Test: Cost $100, category has 20% markup, override is 0%
        # Should result in $100.00 (no markup applied due to 0% override)
        cost = Decimal('100.00')
        override_markup = Decimal('0.00')  # 0% override should be respected
        
        result = compute_price(cost, override_markup, test_category.id)
        expected = Decimal('100.00')  # Cost with 0% markup = original cost
        
        print(f"  Cost: ${cost}, Category markup: 20%, Override: 0%")
        print(f"  Expected: ${expected}, Got: ${result}")
        
        if result == expected:
            print("  ✅ PASS: 0% override markup is correctly respected")
        else:
            print("  ❌ FAIL: 0% override markup bug still exists")
        
        # Clean up
        db.session.delete(test_category)
        db.session.commit()
        return result == expected

def test_decimal_precision():
    """Test that Decimal arithmetic prevents rounding errors"""
    print("\nTesting Decimal precision...")
    
    with app.app_context():
        # Test with values that would cause float rounding issues
        cost = Decimal('123.456')  # Precise cost
        override_markup = Decimal('7.777')  # Precise markup percentage
        
        result = compute_price(cost, override_markup, None)
        
        # Manual calculation: 123.456 * (1 + 7.777/100) = 123.456 * 1.07777 = 133.05717312
        # Quantized to 2 decimal places with ROUND_HALF_UP = 133.06
        expected = Decimal('133.06')
        
        print(f"  Cost: ${cost}, Override markup: {override_markup}%")
        print(f"  Expected: ${expected}, Got: ${result}")
        
        if result == expected:
            print("  ✅ PASS: Decimal arithmetic provides correct precision")
        else:
            print("  ❌ FAIL: Precision error in calculation")
        
        return result == expected

def test_category_fallback():
    """Test that category markup is used when no override is provided"""
    print("\nTesting category markup fallback...")
    
    with app.app_context():
        # Create a test category with specific markup
        test_category = Category(name="Test Category 2", slug="test2", markup=Decimal('15.5'))
        db.session.add(test_category)
        db.session.commit()
        
        # Test: Cost $200, no override (None), should use category's 15.5% markup
        cost = Decimal('200.00')
        override_markup = None  # No override
        
        result = compute_price(cost, override_markup, test_category.id)
        # 200.00 * (1 + 15.5/100) = 200.00 * 1.155 = 231.00
        expected = Decimal('231.00')
        
        print(f"  Cost: ${cost}, Category markup: 15.5%, Override: None")
        print(f"  Expected: ${expected}, Got: ${result}")
        
        if result == expected:
            print("  ✅ PASS: Category markup fallback works correctly")
        else:
            print("  ❌ FAIL: Category markup fallback failed")
        
        # Clean up
        db.session.delete(test_category)
        db.session.commit()
        return result == expected

def test_no_cost():
    """Test edge case with no cost"""
    print("\nTesting no cost edge case...")
    
    result = compute_price(None, Decimal('10.0'), None)
    expected = Decimal('0.00')
    
    print(f"  Cost: None, Expected: ${expected}, Got: ${result}")
    
    if result == expected:
        print("  ✅ PASS: No cost edge case handled correctly")
    else:
        print("  ❌ FAIL: No cost edge case failed")
    
    return result == expected

def main():
    """Run all tests"""
    print("=" * 60)
    print("PRICING CALCULATION TESTS")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_override_markup_zero()
    all_passed &= test_decimal_precision() 
    all_passed &= test_category_fallback()
    all_passed &= test_no_cost()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Pricing bugs are fixed.")
    else:
        print("❌ SOME TESTS FAILED! Review the issues above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    main()
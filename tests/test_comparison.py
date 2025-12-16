import pytest
from deal_evaluator import DealEvaluator

def test_comparison_with_real_data():
    """
    Tests the deal evaluator against the locally built dataset.
    This test requires 'data/deal_data.pkl' to be populated by 'build_dataset.py'.
    """
    evaluator = DealEvaluator()
    
    if not evaluator.data:
        pytest.skip("No data found in deal_data.pkl. Run build_dataset.py first.")

    print(f"Loaded {len(evaluator.data)} items from database.")

    # Create a fake item to test against
    # Using a generic item that should match something in a large electronics dataset
    test_item = {
        "title": "Gaming Monitor 144hz",
        "description": "27 inch 144hz gaming monitor, good condition",
        "attributes": ["monitor", "144hz", "gaming"],
        "price": 150,
        "link": "http://example.com/test-item"
    }
    
    rating, stats = evaluator.evaluate_deal(test_item)
    
    # Output for debugging (visible with pytest -s)
    print(f"\nItem: {test_item['title']} (${test_item['price']})")
    print(f"Rating: {rating}")
    
    if stats:
        print(f"Average Price: ${stats['average_price']}")
        print(f"Sample Size: {stats['sample_size']}")
        print("Similar Listings:")
        for item in stats['similar_listings']:
            print(f" - {item['title']} (${item['price']})")

    # Assertions
    assert rating is not None
    assert stats is not None, "No similar items found. Dataset might be too small or irrelevant."
    assert stats['sample_size'] > 0
    assert stats['average_price'] > 0

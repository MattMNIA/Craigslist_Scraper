import os
import sys
from pathlib import Path
import pytest
from deal_evaluator import DealEvaluator

@pytest.fixture
def evaluator():
    storage_file = Path('data/test_deal_data.pkl')
    if storage_file.exists():
        storage_file.unlink()
        
    evaluator = DealEvaluator(storage_file=storage_file)
    yield evaluator
    
    if storage_file.exists():
        storage_file.unlink()

def test_evaluator_logic(evaluator):
    listings = [
        {"title": "MacBook Pro 2020", "description": "13 inch, M1, 8GB RAM", "attributes": ["apple", "laptop"], "price": 900, "link": "link1"},
        {"title": "MacBook Pro M1", "description": "2020 model, 8GB memory, 256GB SSD", "attributes": ["apple", "notebook"], "price": 950, "link": "link2"},
        {"title": "MacBook Pro 13", "description": "M1 chip, like new", "attributes": ["apple"], "price": 850, "link": "link3"},
        {"title": "Old Dell Laptop", "description": "Windows 10, slow", "attributes": ["dell"], "price": 200, "link": "link4"},
    ]
    
    for l in listings:
        evaluator.add_listing(l)
        
    new_listing = {"title": "MacBook Pro M1 2020", "description": "Great condition 8gb", "attributes": ["apple"], "price": 600, "link": "link5"}
    
    rating, stats = evaluator.evaluate_deal(new_listing)
    
    assert rating == "Incredible Deal"
    assert stats is not None
    assert stats['current_price'] == 600
    assert stats['sample_size'] >= 3
    assert stats['average_price'] > 800



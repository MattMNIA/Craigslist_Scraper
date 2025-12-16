import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from deal_evaluator import DealEvaluator

@pytest.fixture
def mock_sentence_transformer():
    with patch('deal_evaluator.SentenceTransformer') as MockST:
        mock_model = MockST.return_value
        # Mock encode to return a fixed vector
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        yield MockST

@pytest.fixture
def evaluator(mock_sentence_transformer, tmp_path):
    # Use a temp file for storage to avoid messing with real data
    storage_file = tmp_path / "test_deal_data.pkl"
    return DealEvaluator(storage_file=str(storage_file))

def test_extract_features(evaluator):
    price = 100
    similar_items = [
        (0.9, {'details': {'price': 100}}),
        (0.8, {'details': {'price': 200}})
    ]
    
    # Avg price = 150. Ratio = 100/150 = 0.666...
    # Avg sim = 0.85
    # Max sim = 0.9
    # Count = 2
    
    features = evaluator._extract_features(price, similar_items)
    
    assert features.shape == (1, 4)
    assert np.isclose(features[0][0], 0.66666667) # Price Ratio
    assert np.isclose(features[0][1], 0.85)       # Avg Similarity
    assert np.isclose(features[0][2], 0.9)        # Max Similarity
    assert features[0][3] == 2.0                  # Count

def test_extract_features_no_similar(evaluator):
    features = evaluator._extract_features(100, [])
    assert np.array_equal(features, np.array([[0, 0, 0, 0]]))

def test_train_model(evaluator):
    # Mock the classifier to verify partial_fit is called
    evaluator.classifier = MagicMock()
    
    listing = {'title': 'Test Item', 'price': 100, 'link': 'http://test.com'}
    
    # Mock find_similar_listings to return something so we have features
    evaluator.find_similar_listings = MagicMock(return_value=[
        (0.9, {'details': {'price': 120}, 'title': 'Sim 1', 'link': 'l1'})
    ])
    
    evaluator.train_model(listing, "Incredible Deal")
    
    # Check if partial_fit was called
    assert evaluator.classifier.partial_fit.called
    args, kwargs = evaluator.classifier.partial_fit.call_args
    
    # Check features passed to partial_fit
    features = args[0]
    assert features.shape == (1, 4)
    
    # Check label passed
    labels = args[1]
    assert labels == ["Incredible Deal"]
    
    # Check classes passed
    assert "classes" in kwargs
    assert len(kwargs["classes"]) == 6

def test_evaluate_deal_uses_classifier(evaluator):
    # Train the classifier slightly so it has coef_ (simulated)
    # Or just mock the classifier completely
    evaluator.classifier = MagicMock()
    evaluator.classifier.coef_ = np.array([1]) # Fake that it's fitted
    evaluator.classifier.predict.return_value = ["Overpriced"]
    
    listing = {'title': 'Test Item', 'price': 1000, 'link': 'http://test.com'}
    
    # Mock similar listings
    evaluator.find_similar_listings = MagicMock(return_value=[
        (0.9, {'details': {'price': 100}, 'title': 'Sim 1', 'link': 'l1'})
    ])
    
    rating, stats = evaluator.evaluate_deal(listing)
    
    assert rating == "Overpriced"
    evaluator.classifier.predict.assert_called_once()

def test_evaluate_deal_fallback_heuristic(evaluator):
    # Ensure classifier does NOT have coef_ (not fitted yet)
    if hasattr(evaluator.classifier, 'coef_'):
        del evaluator.classifier.coef_
        
    listing = {'title': 'Test Item', 'price': 50, 'link': 'http://test.com'}
    
    # Mock similar listings (Avg price 100) -> Ratio 0.5 -> Incredible Deal
    evaluator.find_similar_listings = MagicMock(return_value=[
        (0.9, {'details': {'price': 100}, 'title': 'Sim 1', 'link': 'l1'})
    ])
    
    rating, stats = evaluator.evaluate_deal(listing)
    
    assert rating == "Incredible Deal"

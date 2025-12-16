import os
from pathlib import Path
import numpy as np
import joblib
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import SGDClassifier
from logger import get_logger

logger = get_logger("deal_evaluator")

class DealEvaluator:
    def __init__(self, model_name='all-MiniLM-L6-v2', storage_file='data/deal_data.pkl'):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self.model_path = self.storage_file.with_name("deal_classifier.pkl")
        self.interest_model_path = self.storage_file.with_name("interest_classifier.pkl")
        
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.data = self._load_data()
        self.classifier = self._load_classifier(self.model_path)
        self.interest_classifier = self._load_classifier(self.interest_model_path)
        self.classes = ["Incredible Deal", "Great Deal", "Good Deal", "Fair Price", "Slightly Overpriced", "Overpriced"]
        self.interest_classes = ["Interested", "Neutral", "Not Interested"]

    def _load_data(self):
        if self.storage_file.exists():
            try:
                data = joblib.load(self.storage_file)
                logger.info(f"Loaded {len(data)} listings from {self.storage_file}")
                return data
            except Exception as e:
                logger.error(f"Failed to load deal data: {e}")
                return []
        return []

    def _load_classifier(self, path):
        if path.exists():
            try:
                clf = joblib.load(path)
                logger.info(f"Loaded classifier from {path}")
                return clf
            except Exception as e:
                logger.error(f"Failed to load classifier {path}: {e}")
        
        # Initialize a new online learner
        return SGDClassifier(loss='log_loss', random_state=42)

    def _save_data(self):
        try:
            joblib.dump(self.data, self.storage_file)
            logger.debug(f"Saved {len(self.data)} listings to {self.storage_file}")
        except Exception as e:
            logger.error(f"Failed to save deal data: {e}")

    def _save_classifier(self, clf, path):
        try:
            joblib.dump(clf, path)
            logger.debug(f"Saved classifier to {path}")
        except Exception as e:
            logger.error(f"Failed to save classifier {path}: {e}")

    def _get_text_representation(self, listing):
        # Combine title, description, and attributes
        title = listing.get('title', '')
        description = listing.get('description', '')
        attributes = listing.get('attributes', [])
        if isinstance(attributes, list):
            attributes = " ".join(attributes)
        
        text = f"{title} {description} {attributes}".strip()
        return text

    def add_listing(self, listing):
        """
        Adds a listing to the database. Computes embedding and saves.
        """
        link = listing.get('link')
        if not link:
            logger.warning("Listing has no link, skipping add.")
            return

        # Check if already exists to avoid duplicates (by link)
        # We might want to update if it exists, but for now just skip
        for item in self.data:
            if item['link'] == link:
                return

        text = self._get_text_representation(listing)
        embedding = self.model.encode(text)
        
        entry = {
            'link': link,
            'title': listing.get('title'),
            'price': listing.get('price'),
            'embedding': embedding,
            # Store minimal details to save space, or full if needed
            'details': {k: v for k, v in listing.items() if k not in ['embedding']} 
        }
        self.data.append(entry)
        self._save_data()
        logger.info(f"Added listing to evaluator: {listing.get('title')}")

    def find_similar_listings(self, listing, top_k=5, threshold=0.4):
        """
        Finds similar listings in the database.
        """
        if not self.data:
            return []

        text = self._get_text_representation(listing)
        query_embedding = self.model.encode(text).reshape(1, -1)
        
        # Stack embeddings from stored data
        stored_embeddings = np.vstack([d['embedding'] for d in self.data])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_embedding, stored_embeddings)[0]
        
        # Create a list of (similarity, item)
        results = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                results.append((score, self.data[idx]))
        
        # Sort by score desc
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Filter out the item itself if it's already in DB (by link)
        results = [r for r in results if r[1]['link'] != listing.get('link')]
        
        return results[:top_k]

    def _extract_features(self, listing, price, similar_items):
        """
        Extracts features for the classifier.
        Features: [price_ratio, avg_similarity, max_similarity, num_similar] + [384 embedding dims]
        """
        # Calculate stats features
        if not similar_items:
            ratio = 1.0
            avg_sim = 0.0
            max_sim = 0.0
            count = 0
        else:
            prices = [item['details'].get('price') for score, item in similar_items if item['details'].get('price') is not None]
            if not prices:
                ratio = 1.0
            else:
                avg_price = np.mean(prices)
                ratio = price / avg_price if avg_price > 0 else 1.0
            
            similarities = [score for score, item in similar_items]
            avg_sim = np.mean(similarities)
            max_sim = np.max(similarities)
            count = len(similar_items)

        stats_features = np.array([ratio, avg_sim, max_sim, count])
        
        # Get embedding
        embedding = listing.get('embedding')
        if embedding is None:
            # If not pre-computed, compute it now
            text = self._get_text_representation(listing)
            embedding = self.model.encode(text)
            listing['embedding'] = embedding # Cache it
            
        return np.concatenate([stats_features, embedding]).reshape(1, -1)

    def evaluate_deal(self, listing):
        """
        Evaluates if the listing is a good deal based on similar items.
        Returns (rating, stats_dict, interest_prediction).
        """
        price = listing.get('price')
        if price is None:
            return "Unknown Price", None, "Unknown"

        similar_items = self.find_similar_listings(listing)
        
        # Extract features (includes embedding)
        features = self._extract_features(listing, price, similar_items)
        
        # --- Deal Rating ---
        if not similar_items:
            rating = "No Data"
            stats = None
        else:
            # Extract prices from similar items for stats
            prices = [item['details'].get('price') for score, item in similar_items if item['details'].get('price') is not None]
            
            if not prices:
                rating = "No Price Data"
                stats = None
            else:
                avg_price = np.mean(prices)
                
                # Avoid division by zero or weirdness
                if avg_price == 0:
                    rating = "Free?"
                    stats = {'current_price': price, 'average_price': 0}
                else:
                    ratio = price / avg_price
                    
                    # Heuristic rating (fallback)
                    if ratio < 0.7:
                        rating = "Incredible Deal"
                    elif ratio < 0.85:
                        rating = "Great Deal"
                    elif ratio < 1.0:
                        rating = "Good Deal"
                    elif ratio < 1.15:
                        rating = "Fair Price"
                    elif ratio < 1.3:
                        rating = "Slightly Overpriced"
                    else:
                        rating = "Overpriced"

                    stats = {
                        'current_price': price,
                        'average_price': round(avg_price, 2),
                        'price_difference': round(price - avg_price, 2),
                        'sample_size': len(prices),
                        'similar_listings': [
                            {
                                'title': item['title'],
                                'price': item['details'].get('price'),
                                'similarity': round(score, 2),
                                'link': item['link']
                            }
                            for score, item in similar_items
                        ]
                    }

        # Use classifier if available
        if hasattr(self.classifier, 'coef_'):
            try:
                rating = self.classifier.predict(features)[0]
            except Exception as e:
                logger.warning(f"Classifier prediction failed, using heuristic: {e}")

        # --- Interest Prediction ---
        interest = "Unknown"
        if hasattr(self.interest_classifier, 'coef_'):
            try:
                interest = self.interest_classifier.predict(features)[0]
            except Exception as e:
                logger.warning(f"Interest prediction failed: {e}")

        return rating, stats, interest

    def train_model(self, listing, actual_rating):
        """
        Updates the deal classifier with user feedback.
        """
        price = listing.get('price')
        if price is None:
            logger.warning("Cannot train on listing without price")
            return

        similar_items = self.find_similar_listings(listing)
        features = self._extract_features(listing, price, similar_items)
        
        self.classifier.partial_fit(features, [actual_rating], classes=self.classes)
        self._save_classifier(self.classifier, self.model_path)
        logger.info(f"Updated deal classifier with rating: {actual_rating}")

        # Mark as reviewed
        link = listing.get('link')
        for item in self.data:
            if item.get('link') == link:
                item['reviewed'] = True
                self._save_data()
                break

    def train_interest(self, listing, is_interested):
        """
        Updates the interest classifier.
        is_interested: "Interested" or "Not Interested"
        """
        price = listing.get('price')
        if price is None:
            return

        similar_items = self.find_similar_listings(listing)
        features = self._extract_features(listing, price, similar_items)
        
        self.interest_classifier.partial_fit(features, [is_interested], classes=self.interest_classes)
        self._save_classifier(self.interest_classifier, self.interest_model_path)
        logger.info(f"Updated interest classifier: {is_interested}")

        # Mark as reviewed
        link = listing.get('link')
        for item in self.data:
            if item.get('link') == link:
                item['reviewed'] = True
                self._save_data()
                break

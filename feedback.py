import os
from deal_evaluator import DealEvaluator

def main():
    print("Initializing Deal Evaluator...")
    evaluator = DealEvaluator()
    
    if not evaluator.data:
        print("No data found in DealEvaluator storage.")
        return

    print(f"Found {len(evaluator.data)} listings.")
    print("Starting feedback loop. Press Ctrl+C to exit.")
    
    # Filter out items that have already been reviewed
    items_to_review = [item for item in reversed(evaluator.data) if not item.get('reviewed', False)]
    
    if not items_to_review:
        print("All items have already been reviewed!")
        return

    for i, item in enumerate(items_to_review):
        listing = item['details']
        listing['link'] = item['link'] # Ensure link is present
        listing['title'] = item['title']
        listing['price'] = item['price']
        
        print("\n" + "="*50)
        print(f"Title: {listing.get('title')}")
        print(f"Price: ${listing.get('price')}")
        print(f"Link: {listing.get('link')}")
        
        current_rating, stats = evaluator.evaluate_deal(listing)
        print(f"Current Rating: {current_rating}")
        
        if stats:
            print(f"Avg Price of Similar: ${stats.get('average_price')} (based on {stats.get('sample_size')} items)")
        
        print("\nOptions:")
        print("1. Incredible Deal")
        print("2. Great Deal")
        print("3. Good Deal")
        print("4. Fair Price")
        print("5. Slightly Overpriced")
        print("6. Overpriced")
        print("s. Skip")
        print("q. Quit")
        
        choice = input("Enter your rating (1-6): ").strip().lower()
        
        if choice == 'q':
            break
        if choice == 's':
            continue
            
        rating_map = {
            '1': "Incredible Deal",
            '2': "Great Deal",
            '3': "Good Deal",
            '4': "Fair Price",
            '5': "Slightly Overpriced",
            '6': "Overpriced"
        }
        
        if choice in rating_map:
            actual_rating = rating_map[choice]
            evaluator.train_model(listing, actual_rating)
            print(f"Feedback recorded: {actual_rating}")
        else:
            print("Invalid choice, skipping.")

if __name__ == "__main__":
    main()

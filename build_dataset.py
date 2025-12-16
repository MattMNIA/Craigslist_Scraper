import time
import yaml
from scraper import fetch_listings, parse_listing, fetch_details, parse_details
from deal_evaluator import DealEvaluator
from logger import get_logger

logger = get_logger("dataset_builder")

def build_dataset():
    # Load config for location
    try:
        with open("inputs.yaml", "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("inputs.yaml not found. Please ensure it exists with location data.")
        return

    # Extract Ames location details from the first search
    # We assume the first search contains the relevant location data for Ames
    if not config.get('searches'):
        logger.error("No searches found in inputs.yaml")
        return

    base_config = config['searches'][0]
    location = base_config.get('location', 'ames')
    lat = base_config.get('lat')
    lon = base_config.get('lon')
    search_distance = base_config.get('search_distance')
    
    logger.info(f"Building dataset for location: {location} (Lat: {lat}, Lon: {lon}, Dist: {search_distance})")

    # Categories to search for electronics
    # sya: computers
    # ela: electronics
    # vga: video gaming
    # syp: computer parts
    categories = ["sya", "ela", "vga", "syp"]
    
    evaluator = DealEvaluator()
    
    # Cache existing links to avoid unnecessary processing
    existing_links = {d['link'] for d in evaluator.data}
    logger.info(f"Loaded {len(existing_links)} existing items from database.")

    for category in categories:
        logger.info(f"--- Fetching listings for category: {category} ---")
        try:
            # Empty query to get all items in the category
            rows = fetch_listings(
                location=location,
                category=category,
                query="", 
                lat=lat,
                lon=lon,
                search_distance=search_distance
            )
        except Exception as e:
            logger.error(f"Failed to fetch listings for {category}: {e}")
            continue
            
        logger.info(f"Found {len(rows)} items in {category}")
        
        new_items_count = 0
        for i, row in enumerate(rows):
            try:
                item = parse_listing(row)
                
                if item['link'] in existing_links:
                    # logger.debug(f"Skipping existing item: {item['title']}")
                    continue

                logger.info(f"Processing {i+1}/{len(rows)}: {item['title']}")
                
                # Deep fetch for description and attributes
                try:
                    soup = fetch_details(item['link'])
                    details = parse_details(soup)
                    item.update(details)
                except Exception as e:
                    logger.warning(f"Failed to fetch details for {item['link']}: {e}")
                    # We can still add it without details if we want, but details are better for embeddings
                    # Let's skip if details failed, or maybe add what we have?
                    # Adding what we have is better than nothing.
                
                evaluator.add_listing(item)
                existing_links.add(item['link'])
                new_items_count += 1
                
                # Sleep to be polite to Craigslist servers
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                continue
        
        logger.info(f"Added {new_items_count} new items from {category}")
        # Sleep between categories
        time.sleep(5)

    logger.info("Dataset build complete.")

if __name__ == "__main__":
    build_dataset()

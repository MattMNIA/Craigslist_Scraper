# Craigslist Deal Scraper & AI Evaluator

This tool scrapes Craigslist for specific items, filters them based on your criteria, and uses **AI (Sentence Transformers)** to evaluate whether a listing is a "Good Deal" by comparing it to a local database of similar items.

## 🚀 How It Works

1.  **Dataset Building**: First, you run a script to scrape a wide radius of listings (e.g., all electronics within 200 miles). These are converted into "vector embeddings" (mathematical representations of the text) and stored locally.
2.  **Targeted Scraping**: The main scraper looks for your specific items (e.g., "Gaming Monitor" in "Ames").
3.  **AI Evaluation**: When a match is found, the system:
    *   Embeds the new listing.
    *   Finds the most semantically similar items in your local database.
    *   Calculates the average price of those similar items.
    *   Compares the current price to the average to generate a **Deal Rating** (e.g., "Incredible Deal", "Overpriced").
4.  **Notification**: Sends a rich notification to Discord with the item details, price comparison, and deal rating.

## 🛠️ Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    *   Copy `inputs.example.yaml` to `inputs.yaml`.
    *   Edit `inputs.yaml` to define your searches.
    *   **Important**: Set `compare_radius` in `inputs.yaml`. This determines how far out the system looks to build its pricing baseline.
        ```yaml
        compare_radius: 200  # Miles
        ```

3.  **Environment Variables**:
    *   Create a `.env` file.
    *   Add your Discord Webhook URL:
        ```
        DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
        ```
    *   **For Interactive Bot (Optional)**:
        If you want to use the interactive bot with feedback buttons, you need a Bot Token and Channel ID instead of just a Webhook.
        ```
        DISCORD_BOT_TOKEN=your_bot_token_here
        DISCORD_CHANNEL_ID=your_channel_id_here
        ```

## 🏗️ Step 1: Build the Comparison Dataset

Before running the main scraper, you need to build the "knowledge base" of prices.

Run:
```bash
python build_dataset.py
```

**Why?**
To know if a $150 monitor is a good deal, the system needs to know what other similar monitors are selling for. This script scrapes thousands of items (Computers, Electronics, Phones) within your `compare_radius` and stores them in `data/deal_data.pkl`.

*   **Note**: This process can take a while (10-20 minutes) depending on the radius, as it respects Craigslist's rate limits.
*   **Storage**: The data is stored locally. You can re-run this periodically (e.g., once a week) to keep prices fresh.

## 🏃 Step 2: Run the Scraper

### Option A: Simple Script (Webhook)
Once the dataset is built, run the main scraper:

```bash
python main.py
```

This will:
1.  Search for the specific items defined in `inputs.yaml`.
2.  Filter out items you've already seen.
3.  Evaluate the deal quality using your dataset.
4.  Post new matches to Discord via Webhook.

### Option B: Interactive Bot (Feedback Loop)
Run the Discord bot to receive notifications with feedback buttons:

```bash
python bot.py
```

This will:
1.  Start a Discord bot that runs 24/7.
2.  Scrape every 15 minutes.
3.  Send notifications with buttons (Incredible, Great, Good, etc.).
4.  **Learn from your feedback**: When you click a button, the AI model updates to better classify future deals based on your preferences.

## 🧠 AI & Reinforcement Learning

The system uses `sentence-transformers` to understand the semantic similarity between product titles and descriptions.

*   **Initial Logic**: Compares price to the average of the top 5 most similar items.
*   **Reinforcement Learning**: When you use `bot.py` and click feedback buttons, an `SGDClassifier` learns to adjust the ratings based on features like price ratio, similarity score, and your past feedback.
5.  Add the new matches to the dataset (so it gets smarter over time).

## ⏰ Automation (Run Every Hour)

To catch deals quickly, you should schedule `main.py` to run automatically.

### Linux / macOS (Cron)

Open your crontab:
```bash
crontab -e
```

Add the following line to run every hour:
```bash
# Run at minute 0 of every hour
0 * * * * cd /path/to/craigslist_scraper && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1
```

### Windows (Task Scheduler)

1.  Open **Task Scheduler**.
2.  Click **Create Task**.
3.  **General**: Name it "Craigslist Scraper". Check "Run whether user is logged on or not".
4.  **Triggers**: New -> Begin the task: "On a schedule" -> "Daily" -> Repeat task every: "1 hour" -> for a duration of: "Indefinitely".
5.  **Actions**: New -> Action: "Start a program".
    *   **Program/script**: `path\to\python.exe` (or your venv python)
    *   **Add arguments**: `main.py`
    *   **Start in**: `C:\Projects\Personal\craigslist_scraper` (Full path to your project folder)

## 🧪 Testing

You can test the deal evaluator logic without scraping by running:
```bash
pytest tests/test_comparison.py
```

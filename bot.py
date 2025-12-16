import os
import asyncio
import yaml
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from scraper import fetch_listings, parse_listing, fetch_details, parse_details
from filters import matches_filters
from state import load_seen, save_seen
from deal_evaluator import DealEvaluator
from logger import get_logger

# Setup logging
logger = get_logger("discord_bot")

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
raw_channel_id = os.getenv("DISCORD_CHANNEL_ID")

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not found in .env")
if not raw_channel_id:
    raise RuntimeError("DISCORD_CHANNEL_ID not found in .env")

CHANNEL_ID = int(raw_channel_id)

# Initialize Bot
intents = discord.Intents.default()
# intents.message_content = True # Disabled to avoid PrivilegedIntentsRequired error. Enable in Dev Portal if you need text commands.
bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize State and Evaluator
seen = load_seen()
evaluator = DealEvaluator()

# Load Config
config_path = "inputs.yaml"
if not os.path.exists(config_path):
    config_path = "inputs.example.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Global state for batch processing
pending_items = {} # link -> {'rating': False, 'interest': False}
scraping_finished = False

async def check_completion():
    if not scraping_finished:
        return
    
    if not pending_items:
        logger.info("No items to review. Exiting.")
        await bot.close()
        return

    # Check if all items have both rating and interest
    all_done = True
    remaining = 0
    for link, status in pending_items.items():
        if not status['rating'] or not status['interest']:
            all_done = False
            remaining += 1
    
    if all_done:
        logger.info("All items reviewed. Exiting.")
        await bot.close()
    else:
        logger.info(f"Waiting for feedback on {remaining} items...")

class DealFeedbackView(discord.ui.View):
    def __init__(self, listing, evaluator):
        super().__init__(timeout=None)
        self.listing = listing
        self.evaluator = evaluator

    async def handle_feedback(self, interaction: discord.Interaction, rating: str):
        self.evaluator.train_model(self.listing, rating)
        
        # Update state
        link = self.listing['link']
        if link in pending_items:
            pending_items[link]['rating'] = True
            
        await interaction.response.send_message(content=f"✅ Deal Rating recorded: **{rating}**", ephemeral=True)
        await check_completion()

    async def handle_interest(self, interaction: discord.Interaction, interest: str):
        self.evaluator.train_interest(self.listing, interest)
        
        # Update state
        link = self.listing['link']
        if link in pending_items:
            pending_items[link]['interest'] = True

        await interaction.response.send_message(content=f"✅ Interest recorded: **{interest}**", ephemeral=True)
        await check_completion()

    # --- Row 1: Deal Rating ---
    @discord.ui.button(label="Incredible", style=discord.ButtonStyle.success, custom_id="rating_incredible", row=0)
    async def incredible(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_feedback(interaction, "Incredible Deal")

    @discord.ui.button(label="Great", style=discord.ButtonStyle.success, custom_id="rating_great", row=0)
    async def great(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_feedback(interaction, "Great Deal")

    @discord.ui.button(label="Good", style=discord.ButtonStyle.primary, custom_id="rating_good", row=0)
    async def good(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_feedback(interaction, "Good Deal")

    @discord.ui.button(label="Fair", style=discord.ButtonStyle.secondary, custom_id="rating_fair", row=0)
    async def fair(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_feedback(interaction, "Fair Price")

    @discord.ui.button(label="Overpriced", style=discord.ButtonStyle.danger, custom_id="rating_overpriced", row=0)
    async def overpriced(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_feedback(interaction, "Overpriced")

    # --- Row 2: Interest ---
    @discord.ui.button(label="I Want This!", style=discord.ButtonStyle.success, custom_id="interest_yes", row=1)
    async def interest_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_interest(interaction, "Interested")

    @discord.ui.button(label="Neutral", style=discord.ButtonStyle.secondary, custom_id="interest_neutral", row=1)
    async def interest_neutral(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_interest(interaction, "Neutral")

    @discord.ui.button(label="Not Interested", style=discord.ButtonStyle.danger, custom_id="interest_no", row=1)
    async def interest_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_interest(interaction, "Not Interested")

@bot.event
async def on_ready():
    if bot.user:
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    # Run scrape task once, not as a loop
    bot.loop.create_task(scrape_task())

async def scrape_task():
    global scraping_finished
    logger.info("Starting scrape cycle...")
    channel = bot.get_channel(CHANNEL_ID)
    if not channel or not isinstance(channel, discord.abc.Messageable):
        logger.error(f"Channel {CHANNEL_ID} not found or not messageable.")
        await bot.close()
        return

    if "searches" not in config:
        await bot.close()
        return

    for search in config["searches"]:
        logger.info(f"Searching: {search['name']}")
        try:
            # Run blocking IO in executor to avoid blocking the bot
            rows = await bot.loop.run_in_executor(None, lambda: fetch_listings(
                location=search["location"],
                category=search["category"],
                query=search["query"],
                lat=search.get("lat"),
                lon=search.get("lon"),
                search_distance=search.get("search_distance")
            ))
        except Exception as e:
            logger.error(f"Failed to fetch listings: {e}")
            continue

        for row in rows:
            try:
                item = parse_listing(row)
            except Exception:
                continue

            is_seen = item["link"] in seen
            price_changed = False
            old_price = None
            
            if is_seen:
                old_price = seen[item["link"]]
                if old_price != item["price"]:
                    price_changed = True
            
            if is_seen and not price_changed:
                continue

            if matches_filters(item, search):
                seen[item["link"]] = item["price"]
                
                try:
                    # Deep fetch
                    soup = await bot.loop.run_in_executor(None, lambda: fetch_details(item["link"]))
                    details = parse_details(soup)
                    item.update(details)

                    # Evaluate
                    rating, stats, interest = evaluator.evaluate_deal(item)
                    item["deal_rating"] = rating
                    item["deal_stats"] = stats
                    item["interest_prediction"] = interest
                    
                    evaluator.add_listing(item)

                    if price_changed and old_price is not None:
                        item["old_price"] = old_price

                    # Add to pending items BEFORE sending
                    pending_items[item['link']] = {'rating': False, 'interest': False}

                    # Send Discord Message
                    embed = create_embed(item, search["name"])
                    view = DealFeedbackView(item, evaluator)
                    await channel.send(embed=embed, view=view)
                    
                    # Save state periodically
                    save_seen(seen)
                    
                    await asyncio.sleep(2) # Be nice
                except Exception as e:
                    logger.error(f"Error processing item {item.get('link')}: {e}")
                    # If failed, remove from pending so we don't wait forever
                    if item.get('link') in pending_items:
                        del pending_items[item['link']]

    save_seen(seen)
    logger.info("Scrape cycle finished.")
    
    scraping_finished = True
    await check_completion()

def create_embed(item, search_name):
    color = 0x00ff99
    title = item["title"][:256]
    
    if "old_price" in item:
        title = f"📉 PRICE DROP: {title}"
        color = 0xff9900

    embed = discord.Embed(
        title=title,
        url=item["link"],
        color=color
    )
    
    embed.add_field(name="Price", value=f"${item['price']}" if item["price"] else "N/A", inline=True)
    if "old_price" in item:
        embed.add_field(name="Old Price", value=f"${item['old_price']}", inline=True)
        
    embed.add_field(name="Location", value=item.get("location") or "N/A", inline=True)
    embed.add_field(name="Search", value=search_name, inline=True)
    
    if "deal_rating" in item:
        embed.add_field(name="AI Rating", value=item["deal_rating"], inline=False)
        
    if "interest_prediction" in item:
        interest = item["interest_prediction"]
        icon = "❓"
        if interest == "Interested":
            icon = "😍"
        elif interest == "Neutral":
            icon = "😐"
        elif interest == "Not Interested":
            icon = "😴"
        embed.add_field(name="Interest Prediction", value=f"{icon} {interest}", inline=True)

    if "deal_stats" in item and item["deal_stats"]:
        stats = item["deal_stats"]
        avg = stats.get("average_price")
        count = stats.get("sample_size")
        embed.add_field(name="Market Context", value=f"Avg: ${avg} (n={count})", inline=True)

    return embed

@scrape_task.before_loop
async def before_scrape():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(TOKEN)

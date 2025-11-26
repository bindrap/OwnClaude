import time
import itertools

# A collection of quotes from notable Greek philosophers (including Marcus Aurelius, who was Roman but heavily influenced by Greek Stoicism)
quotes = [
    "The happiness of your life depends upon the quality of your thoughts. – Marcus Aurelius",
    "The unexamined life is not worth living. – Socrates",
    "The only true wisdom is in knowing you know nothing. – Socrates",
    "Man is the measure of all things. – Protagoras",
    "The soul becomes dyed with the colour of its thoughts. – Marcus Aurelius",
    "It is not that we have a short time to live, but that we waste a lot of it. – Seneca (Stoic, heavily influenced by Greek thought)",
    "Know thyself. – Inscribed at the Temple of Apollo at Delphi (often attributed to various Greek sages)",
    "Happiness depends upon ourselves. – Aristotle",
    "We are what we repeatedly do. Excellence, then, is not an act, but a habit. – Aristotle",
    "The greatest wealth is to live content with little. – Plato"
]

# Use itertools.cycle to loop through the quotes indefinitely in order
quote_cycle = itertools.cycle(quotes)

def display_quote():
    quote = next(quote_cycle)
    print(f"\n--- Quote of the hour ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(quote)
    print("--- End of quote ---\n")

if __name__ == "__main__":
    print("Starting Greek philosopher quote display. A new quote will appear every hour.")
    while True:
        display_quote()
        # Sleep for one hour (3600 seconds). Use a try/except to allow graceful exit with Ctrl+C.
        try:
            time.sleep(3600)
        except KeyboardInterrupt:
            print("\nQuote display stopped by user.")
            break

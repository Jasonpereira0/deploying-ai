# Assignment 2: Travel Assistant - Jason Pereira

## Overview

A **Travel Assistant** chatbot with three integrated services to help users plan trips:

1. **Weather Information** - Real-time weather data for travel destinations
2. **City Information Search** - Semantic search through database of major world cities
3. **Currency Conversion** - Real-time exchange rate calculations with fallback for unsupported currencies

## Services

### Service 1: Weather API (Weatherstack) : http://api.weatherstack.com/current

**Implementation:**
- Uses Weatherstack API with response transformation to natural, contextual advice
- Extracts city names from user messages using GPT
- Provides personalized packing recommendations based on temperature and humidity
- Falls back to Toronto if no city is specified

**API Requirements:** `WEATHERSTACK_API_KEY` in `.secrets`

### Service 2: City Information Search (ChromaDB + Geonames)

**Implementation:**
- ChromaDB with persistent storage and OpenAI embeddings
- Geonames database (`cities15000.txt`) with top 5,000 cities by population
- Semantic search with exact name matching for accurate results
- Returns city name, country, population, coordinates, and timezone
- Auto-populates on first run
- ISO country code to full name mapping

**Data Source:** Geonames public domain geographic data obtained from 'https://www.geonames.org/'

### Service 3: Currency Conversion (Frankfurter API + Function Calling)

**Implementation:**
- Frankfurter API (European Central Bank data) for real-time exchange rates - https://api.frankfurter.app/latest
- OpenAI function calling for structured tool usage
- Automatic parameter extraction from natural language

**Supported Currencies:** USD, EUR, GBP, CAD, JPY, AUD, CHF, CNY, SEK, NZD, NOK, MXN, SGD, HKD, INR, KRW, TRY, RUB, BRL, ZAR, DKK, PLN, TWD, THB, MYR, PHP, CZK, IDR, HUF, ILS, and others

**Fallback for Unsupported Currencies:** 
- For currencies not supported by Frankfurter API (e.g., AED, BTC), the system automatically falls back to OpenAI
- Returns explicit message: "{CURRENCY} is not supported by my primary currency exchange service provider. Checking with a secondary resource..."
- Provides approximate conversion using GPT's knowledge
- Ensures users always receive helpful conversion information

## Personality and Guardrails

**Personality:** Friendly, enthusiastic travel agent who integrates multiple services for trip planning

**Guardrails:**
- Prevents system prompt revelation
- Blocks restricted topics: cats/dogs, horoscopes/astrology, Taylor Swift
- Whole-word matching to avoid false positives
- Maintains travel focus

## Running the Application

### Prerequisites

1. `.secrets` file with:
   - `OPENAI_API_KEY` (required)
   - `WEATHERSTACK_API_KEY` (required)

2. Geonames data: `../documents/cities15000.txt`

### Launch

```bash
cd 05_src/assignment2_chat
python -m assignment2_chat.app
```

Interface launches at `http://localhost:7860`

## File Structure

```
assignment2_chat/
├── __init__.py       # Package marker
├── prompts.py        # System prompts and guardrails
├── main.py          # Core services and chat logic
├── app.py           # Gradio interface
├── readme.md        # This file
└── chroma_db/       # Persistent ChromaDB storage (auto-created)
```

## Architecture Decisions

**Weatherstack:** Free tier, reliable, comprehensive weather data  
**Geonames:** Public domain, standardized, high-quality geographic data  
**ChromaDB:** Persistent storage, built-in OpenAI embeddings, lightweight  
**Frankfurter API:** No API key, ECB data, broad currency support  
**Function Calling:** Structured tool usage, automatic parameter extraction

## Limitations

**Weather Service:**
- Weatherstack free tier API returns current weather only (no forecasts for future dates - uses GPT knowledge instead)
- Free tier API has rate limits

**City Information Service:**
- Covers top 5,000 cities by population from Geonames database
- No automatic updates - database is static
- Exact name matching improves accuracy for specific city queries

**Currency Conversion Service:**
- Frankfurter API supports ~30 major currencies, not all world currencies
- Unsupported currencies (e.g., AED, BTC) fall back to approximate GPT knowledge
- Exchange rates may fluctuate between API calls and timezone diffrerence considerations
- No historical rate data

**General Limitations:**
- No long-term memory persistence (conversation history lost when app restarts)
- Keyword-based routing is not robust and may misinterpret ambiguous queries
- Restricted to travel-related topics only

## Assignment Requirements

✅ **Three Services:** Weather API, Semantic Search, Currency Conversion  
✅ **Gradio Chat Interface:** Message-based with automatic memory  
✅ **Distinct Personality:** Travel enthusiast persona  
✅ **Conversation Memory:** Maintained throughout session  
✅ **Guardrails:** System prompt protection, restricted topics blocked  
✅ **Response Transformation:** Weather data converted to natural language  
✅ **Function Calling:** Currency conversion using structured tools  
✅ **Semantic Search:** ChromaDB with persistent embeddings  
✅ **README:** Technical decisions documented  
✅ **Standard Libraries Only:** No additional dependencies

## Testing Examples

- "What's the weather like in Paris?"
- "Tell me about Tokyo"
- "Convert 200 CAD to EUR"
- "I'm planning a trip to Dubai - what's the weather like there?"
- "How much is 1000 CAD in AED?" (triggers OpenAI fallback due to unsupported currency by Frankfurter API)

## Data Sources and Attribution

**Weatherstack API**  
Weather data provided by Weatherstack. Service terms: https://weatherstack.com/terms  
Data is used for current weather information only.

**Geonames Database**  
Geographic data from Geonames (http://www.geonames.org/), licensed under Creative Commons Attribution 4.0 License (CC BY 4.0).  
Source: https://www.geonames.org/export/

**Frankfurter API**  
Exchange rate data sourced from the European Central Bank (ECB) via Frankfurter.  
Free API service provided by https://www.frankfurter.app/

**OpenAI API**  
AI-powered features use OpenAI's GPT-4o-mini model for natural language processing and embeddings.  
Service terms: https://openai.com/api/policies/terms/

## Testing Challenges, Debugging, and Workarounds

### Issue 1: Token Limit Exceeded During ChromaDB Population
**Problem:** Initial attempt to load all 32,763 cities from Geonames database resulted in "Requested X tokens, max 300000 tokens per request" error.  
**Root Cause:** ChromaDB's `collection.add()` with OpenAI embeddings sends all documents to the API in one batch, exceeding OpenAI's token limit.  
**Solution:** Implemented batch processing in `_populate_city_database()` function, adding cities in batches of 500. This keeps each API call well under the 300k token limit.

### Issue 2: Paris Returns Berlin (Semantic Search Issues)
**Problem:** Querying "tell me about paris" returned information about Berlin instead of Paris.  
**Root Cause:** Semantic search was returning the most similar city by embedding similarity, not necessarily the exact match. Paris was in the dataset but semantic search was finding more "similar" cities.  
**Solution:** Implemented two-layer search strategy: (1) First attempt exact name match using metadata filtering `where={"city_name": city_name.lower()}`, (2) Fall back to semantic search only if no exact match found.

### Issue 3: Invalid Input Error from OpenAI Embeddings
**Problem:** ChromaDB population failing with `"$.input' is invalid"` error from OpenAI API.  
**Root Cause:** Some rows in the Geonames dataset have NaN (Not a Number) values for country codes. The string formatting for city descriptions resulted in "is a major city in nan" which is invalid input for embeddings.  
**Solution:** Added data validation to filter out rows with NaN country codes: `top_cities = top_cities[top_cities['country code'].notna()]` before processing.

### Issue 4: Weather Service Mis-triggering on Non-Weather Queries
**Problem:** "can you give me hotel information?" was routed to weather service because the word "hot" appears in "hotel".  
**Root Cause:** Simple substring matching `"hot" in message_lower` matched both the word "hot" (weather-related) and "hotel" (unrelated).  
**Solution:** Implemented whole-word matching for ambiguous keywords. Split weather keywords into two lists: `weather_keywords` for safe substring matching and `weather_single_words` for keywords like "hot", "cold", "wind", "dry" that use whole-word matching with padding: `any(f" {word} " in f" {message_lower} " for word in weather_single_words)`.

### Issue 5: Currency Conversion API Errors
**Problem:** Initially received `"Missing required parameter: 'tools[0].function'"` error when using `client.chat.completions.create()` with function calling.  
**Root Cause:** Function calling in OpenAI's Responses API requires `client.responses.create()` not `client.chat.completions.create()`. Mixed API usage caused parameter mismatch.  
**Solution:** Switched Service 3 (currency conversion) to use `client.responses.create()` with proper `input`, `tools`, and response handling structure.

### Issue 6: Unsupported Currency Error Handling
**Problem:** When converting unsupported currencies (e.g., AED), the system raised HTTP errors or returned generic error messages without helpful information.  
**Root Cause:** Frankfurter API returns 404 or "not found" message for unsupported currencies, but the system needed to provide a user-friendly fallback.  
**Solution:** Implemented explicit UNSUPPORTED check in `convert_currency()` function, then built separate fallback using Chat Completions API with proper message formatting and disclaimer text.

### Issue 7: Context Lost in Follow-Up Questions
**Problem:** User asks "What's the weather like in Vancouver?" then "What's the weather like there?" and the system couldn't resolve "there" to Vancouver.  
**Root Cause:** City extraction for weather queries wasn't using conversation history, only the current message.  
**Solution:** Modified extraction calls to pass `*conversation_input` to include full conversation history, and updated system prompts to explicitly instruct the model to "Look at the conversation history to resolve pronouns like 'there'."

### Issue 8: Service 2 Not Triggering on Initial City Mentions
**Problem:** "I'm visiting Vancouver" wasn't triggering Service 2 (city information search), falling through to general handler instead.  
**Root Cause:** Service 2 trigger keywords were too narrow, only matching "tell me about" but not initial travel intent phrases.  
**Solution:** Expanded Service 2 trigger conditions to include travel phrases: `"i'm visiting"`, `"i'm going to"`, `"visiting"`, `"going to"`, `"traveling to"`, `"heading to"`, `"planning a trip to"`.

### Issue 9: Guardrails Firing on Valid Queries
**Problem:** "Help me plan my vacation" triggered restricted topic guardrail.  
**Root Cause:** Substring matching meant "swift" in "swift vacation" matched "Taylor Swift" restricted keyword.  
**Solution:** Switched guardrails to whole-word matching. Split keywords into multi-word (substring match) and single-word (whole-word match) lists, similar to weather keyword solution.

### Issue 10: ChromaDB Collection Persistence
**Problem:** Re-running the notebook caused "Collection already exists" errors. Manually deleting database folders was tedious.  
**Root Cause:** ChromaDB PersistentClient maintains collections across sessions. No built-in "overwrite" flag.  
**Solution:** Added try-except block in notebook Cell 9 to delete existing collection before creating new one: `try: chroma_client.delete_collection("travel_document")`.

### Issue 11: Database Path Resolution
**Problem:** ChromaDB path was initially set to `'../05_src/assignment2_chat/chroma_db'` which failed when running from different directories.  
**Root Cause:** Relative paths are resolved from current working directory, which varies depending on how the app is launched.  
**Solution:** Changed to `'./chroma_db'` (relative to the package directory) and ensured ChromaDB persists within the `assignment2_chat` package folder.

### Issue 12: Date/Historical Weather Queries
**Problem:** Users asking "weather in Dubai in January" received current weather instead of seasonal information.  
**Root Cause:** Weatherstack free tier only provides current conditions. System wasn't detecting date mentions.  
**Solution:** Added date/month detection in weather routing logic. If date mentioned, route to GPT's general knowledge instead of Weatherstack API for contextual seasonal advice.

## License and Disclaimer

This project is for educational purposes as part of the Deploying AI course at University of Toronto. All external data sources are used in accordance with their respective terms of service and licenses. Users are responsible for compliance with API rate limits and usage policies.

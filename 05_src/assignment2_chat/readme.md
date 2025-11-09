# Assignment 2: Travel Assistant - Jason Pereira

## Overview

A **Travel Assistant** chatbot with three integrated services to help users plan trips:

1. **Weather Information** - Real-time weather data for travel destinations
2. **City Information Search** - Semantic search through database of major world cities
3. **Currency Conversion** - Real-time exchange rate calculations with fallback for unsupported currencies

> **Folder naming note:** The assignment brief references `05_src/assignment_chat`; this project keeps the implementation in `05_src/assignment2_chat`. All required code, prompts, and documentation are located here.

## Services implemented

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

**API Supported Currencies:** USD, EUR, GBP, CAD, JPY, AUD, CHF, CNY, SEK, NZD, NOK, MXN, SGD, HKD, INR, KRW, TRY, RUB, BRL, ZAR, DKK, PLN, TWD, THB, MYR, PHP, CZK, IDR, HUF, ILS, and others

**Fallback for Unsupported Currencies in API:** 
- For currencies not supported by Frankfurter API (e.g., AED, BTC), the system automatically falls back to OpenAI
- Returns explicit message: "{CURRENCY} is not supported by my primary currency exchange service provider. Checking with a secondary resource..."
- Provides response as approximate conversion using GPT's knowledge
- Ensures users always receive helpful conversion information

## Personality and Guardrails implementation

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

## Limitations of implementation

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


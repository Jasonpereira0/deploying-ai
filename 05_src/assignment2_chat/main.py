from openai import OpenAI
from dotenv import load_dotenv
from assignment2_chat.prompts import get_system_instructions, check_restricted_topics
import json
import requests
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import pandas as pd
from utils.logger import get_logger
import os

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")

client = OpenAI()
open_ai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Initialize ChromaDB client with persistent storage
chroma_client = chromadb.PersistentClient(path='./chroma_db')

# Service 1: Weather API
def get_weather_information(city: str = "Toronto") -> str:
    """
    This function calls the Weatherstack API and transforms the response into natural language.
    
    Parameters:
    - city: The name of the city to get weather for (default: Toronto)
    
    Returns:
    - A natural language description of the weather
    """
    
    api_key = os.getenv("WEATHERSTACK_API_KEY")
    
    if not api_key:
        return f"I apologize, but the weather service is not properly configured."
    
    # Make API call to Weatherstack
    try:
        base_url = "http://api.weatherstack.com/current"
        params = {
            "access_key": api_key,
            "query": city,
            "units": "m"  # Metric units (Celsius, km/h)
        }
        
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        
        # Response Error handling
        if "error" in data:
            return f"I apologize, but I couldn't retrieve weather for {city}: {data['error']['info']}"
        
        # Extract weather data from Weatherstack's response format
        current = data.get("current", {})
        location = data.get("location", {})
        
        temperature = current.get("temperature", "N/A")
        feels_like = current.get("feelslike", temperature)
        condition = current.get("weather_descriptions", ["Unknown"])[0]
        humidity = current.get("humidity", "N/A")
        wind_speed = current.get("wind_speed", "N/A")
        
        actual_city = location.get("name", city)

    # Additional error handling    
    except requests.exceptions.RequestException as e:
        return f"I apologize, but I couldn't retrieve the weather for {city} right now. The weather service may be temporarily unavailable. Error: {str(e)}"
    except KeyError as e:
        return f"I received an unexpected response from the weather service. Please try again later."
    
    # Determine comfort level based on temperature
    try:
        temp = int(temperature)
        if temp >= 25:
            comfort_desc = "quite warm"
            activity = "perfect for a swim or some outdoor water fun"
        elif temp >= 18:
            comfort_desc = "pleasant and comfortable"
            activity = "ideal for a leisurely stroll"
        elif temp >= 10:
            comfort_desc = "a bit cool but manageable"
            activity = "suitable for a brisk walk if you bundle up"
        elif temp >= 0:
            comfort_desc = "quite chilly"
            activity = "best to stay warm indoors or wear extra layers if going out"
        else:
            comfort_desc = "very cold"
            activity = "definitely dress warmly or consider indoor activities"
    except:
        comfort_desc = "unknown"
        activity = "check conditions before heading out"
    
    # Adjust description based on humidity
    try:
        humidity_val = int(humidity)
        if humidity_val >= 80:
            humidity_desc = "quite humid - expect it to feel muggier"
        elif humidity_val <= 30:
            humidity_desc = "relatively dry air"
        else:
            humidity_desc = "moderate humidity"
    except:
        humidity_desc = "moderate humidity"
    
    # Build the response with actual observations
    response = f"In {actual_city}, it's currently {temperature}°C (feels like {feels_like}°C) - {comfort_desc} out there. {condition.capitalize()} conditions with {wind_speed} km/h winds. The air has {humidity}% humidity ({humidity_desc}). {activity.capitalize()}!"
    
    return response


# Service 2: City Information Search with ChromaDB
def search_travel_document(query: str, n_results: int = 1) -> str:
    """
    Performs semantic search on the city database collection.
    
    Parameters:
    - query: The user's question or search query about a destination or place
    - n_results: Number of results to return (default: 1)
    
    Returns:
    - A formatted string with the most relevant city descriptions
    """
    
    try:
        # Get or create collection
        collection = chroma_client.get_or_create_collection(
            name="travel_document",
            embedding_function=OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small"
            )
        )
        
        # Check if collection is empty and populate if needed
        if collection.count() == 0:
            _logs.info("Populating city database...")
            _populate_city_database(collection)
        
        # Try exact match first by checking metadata
        query_lower = query.lower().strip()
        exact_results = collection.query(
            query_texts=[query],
            n_results=n_results * 3,  # Get more results to filter
            where={"city_name": query_lower}
        )
        
        # If exact match found, use it; otherwise fall back to semantic search
        if exact_results['documents'] and len(exact_results['documents'][0]) > 0:
            results = exact_results
        else:
            # Perform the semantic search
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
        
        # Format the results into a readable response
        if results['documents'] and len(results['documents'][0]) > 0:
            # Combine the relevant documents with a summary
            combined_results = "\n\n".join(results['documents'][0])
            return f" I found information about that city:\n\n{combined_results}"
        else:
            return "I couldn't find detailed information about that location in my city database."
            
    except Exception as e:
        _logs.error(f"Error in semantic search: {e}")
        return f"I encountered an error searching for city information: {str(e)}"


def _populate_city_database(collection):
    """Helper function to populate the city database on first run"""
    
    try:
        # Load real city data from Geonames database
        _logs.info("Loading Geonames cities data...")
        
        # Read the tab-separated Geonames cities file
        # Get the absolute path based on the current file location
        import os as os_module
        current_dir = os_module.path.dirname(os_module.path.abspath(__file__))
        data_file = os_module.path.join(current_dir, '..', 'documents', 'cities15000.txt')
        
        df = pd.read_csv(data_file, sep='\t', header=None,
                         names=['geonameid', 'name', 'asciiname', 'alternatenames', 'latitude',
                                'longitude', 'feature class', 'feature code', 'country code', 
                                'cc2', 'admin1', 'admin2', 'admin3', 'admin4', 'population', 
                                'elevation', 'dem', 'timezone', 'modification date'])
        
        _logs.info(f"Loaded {len(df):,} cities from Geonames database")
        
        # Country code mapping: Convert ISO codes to readable country names
        country_names = {
            'US': 'United States', 'CN': 'China', 'IN': 'India', 'BR': 'Brazil',
            'ID': 'Indonesia', 'PK': 'Pakistan', 'BD': 'Bangladesh', 'NG': 'Nigeria',
            'RU': 'Russia', 'JP': 'Japan', 'MX': 'Mexico', 'PH': 'Philippines',
            'ET': 'Ethiopia', 'EG': 'Egypt', 'VN': 'Vietnam', 'TR': 'Turkey',
            'IR': 'Iran', 'DE': 'Germany', 'TH': 'Thailand', 'GB': 'United Kingdom',
            'FR': 'France', 'IT': 'Italy', 'ZA': 'South Africa', 'MY': 'Malaysia',
            'CO': 'Colombia', 'KR': 'South Korea', 'ES': 'Spain', 'AR': 'Argentina',
            'CA': 'Canada', 'AU': 'Australia', 'SA': 'Saudi Arabia', 'PE': 'Peru',
            'VE': 'Venezuela', 'NL': 'Netherlands', 'CH': 'Switzerland', 'IQ': 'Iraq',
            'NZ': 'New Zealand', 'PL': 'Poland', 'SG': 'Singapore', 'GR': 'Greece',
            'BE': 'Belgium', 'CZ': 'Czech Republic', 'PT': 'Portugal', 'SE': 'Sweden',
            'HU': 'Hungary', 'AT': 'Austria', 'RO': 'Romania', 'IL': 'Israel',
            'IE': 'Ireland', 'CL': 'Chile', 'AE': 'United Arab Emirates', 'FI': 'Finland',
            'DK': 'Denmark', 'NO': 'Norway', 'TW': 'Taiwan', 'HK': 'Hong Kong'
        }
        
        # Create descriptive text for top 5000 cities by population
        # This provides comprehensive coverage while staying within API token limits
        top_cities = df.nlargest(5000, 'population')
        
        # Filter out cities with invalid data (NaN country codes, etc.)
        top_cities = top_cities[top_cities['country code'].notna()]
        
        sample_documents = []
        sample_metadatas = []
        for idx, row in top_cities.iterrows():
            # Get readable country name, fallback to code if not found
            country = country_names.get(row['country code'], row['country code'])
            
            # Create a natural language description of each city
            city_info = f"{row['name']} is a major city in {country} " \
                        f"with a population of {row['population']:,} inhabitants. " \
                        f"Located at {row['latitude']:.2f}°N, {row['longitude']:.2f}°E " \
                        f"in the {row['timezone']} timezone."
            sample_documents.append(city_info)
            
            # Store city name in metadata for exact matching
            sample_metadatas.append({"city_name": row['name'].lower()})
        
        document_ids = [f"city_{i+1}" for i in range(len(sample_documents))]
        
        # Add documents to the collection with metadata in batches to avoid token limits
        batch_size = 500
        for i in range(0, len(sample_documents), batch_size):
            batch_docs = sample_documents[i:i + batch_size]
            batch_metas = sample_metadatas[i:i + batch_size]
            batch_ids = document_ids[i:i + batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
        
        _logs.info(f"Successfully added {len(sample_documents):,} city descriptions to the travel assistant!")
        
    except Exception as e:
        _logs.error(f"Error populating city database: {e}")
        raise


# Service 3: Currency Conversion
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Converts currency using the Frankfurter API (European Central Bank data).
    
    Parameters:
    - amount: The amount to convert
    - from_currency: The source currency code (e.g., "USD", "EUR", "GBP", "CAD")
    - to_currency: The target currency code
    
    Returns:
    - A string describing the conversion result
    """
    
    try:
        # Frankfurter API
        base_url = "https://api.frankfurter.app/latest"
        params = {
            "from": from_currency.upper(),
            "to": to_currency.upper()
        }
        
        response = requests.get(base_url, params=params)
        
        # Check for "not found" message from Frankfurter
        if response.status_code == 404:
            return "UNSUPPORTED"
        
        response.raise_for_status()
        
        data = response.json()
        
        # Check for error message in response
        if "message" in data and data["message"] == "not found":
            return "UNSUPPORTED"
        
        exchange_rate = data.get("rates", {}).get(to_currency.upper())
        
        if exchange_rate:
            converted_amount = amount * exchange_rate
            return f"{amount} {from_currency.upper()} equals {converted_amount:.2f} {to_currency.upper()} at the current exchange rate of {exchange_rate:.4f}."
        else:
            return "UNSUPPORTED"
        
    except requests.exceptions.RequestException as e:
        return f"Error: I apologize, but I couldn't retrieve the currency conversion right now. The service may be temporarily unavailable."
    except Exception as e:
        return f"Error: I encountered an error while converting the currency: {str(e)}"


# Define tools for function calling
tools = [
    {
        "type": "function",
        "name": "convert_currency",
        "description": "Converts money from one currency to another using real-time exchange rates. Useful for travel budgeting.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "The amount of money to convert"
                },
                "from_currency": {
                    "type": "string",
                    "description": "The source currency code (e.g., USD, EUR, GBP, CAD, JPY, AUD)"
                },
                "to_currency": {
                    "type": "string",
                    "description": "The target currency code (e.g., USD, EUR, GBP, CAD, JPY, AUD)"
                }
            },
            "required": ["amount", "from_currency", "to_currency"],
            "additionalProperties": False
        }
    }
]


def travel_assistant_chat(message: str, history: list[dict] = []) -> str:
    """
    Main chat function that integrates all three services with memory and guardrails.
    
    Parameters:
    - message: The user's current message
    - history: List of previous messages in the conversation (maintains memory)
    
    Returns:
    - The assistant's response
    """
    
    _logs.info(f'User message: {message}')
    
    # Guardrail: Check for restricted topics FIRST
    if check_restricted_topics(message):
        _logs.info('Restricted topic detected')
        return "I'm sorry, but I'm not able to discuss that topic. I'm here to help with travel planning - weather, destinations, and currencies! What else can I help you with?"
    
    # Convert history to the format OpenAI expects
    conversation_input = []
    for msg in history:
        conversation_input.append({
            "role": msg.get("role"),
            "content": msg.get("content")
        })
    
    # Add the current message
    conversation_input.append({
        "role": "user",
        "content": message
    })
    
    # Determine which service to use based on message keywords
    message_lower = message.lower()
    
    # Service 1: Weatherstack API for travel planning
    # Check for weather-related keywords (whole-word matching for words that could be substrings)
    weather_keywords = ["weather", "temperature", "forecast", "climate", "packing", "pack", "rain", "snow", "sunny", "cloudy", "windy", "foggy", "stormy", "hurricane", "tornado", "smog", "flood", "haze", "mist", "humid", "humidity"]
    weather_single_words = ["cold", "hot", "wind", "dry"]  # Words that could be substrings of other words - like 'hotel' or 'hotel room'
    
    has_weather_keyword = any(word in message_lower for word in weather_keywords)
    has_weather_word = any(f" {word} " in f" {message_lower} " for word in weather_single_words)
    
    if has_weather_keyword or has_weather_word:
        # Check if user mentioned a date/month (historical or future weather)
        months = ['january', 'february', 'march', 'april', 'may', 'june', 
                  'july', 'august', 'september', 'october', 'november', 'december']
        has_date = any(month in message_lower for month in months) or \
                   any(word in message_lower for word in ['tomorrow', 'next week', 'next month', 'month of', 'summer', 'winter', 'spring', 'fall', 'autumn'])
        
        if has_date:
            # For historical/future dates, use GPT's knowledge
            try:
                instructions = get_system_instructions()
                gpt_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": instructions},
                        *conversation_input
                    ],
                    temperature=0.7
                )
                return gpt_response.choices[0].message.content
            except Exception as e:
                _logs.error(f"Error in GPT weather response: {e}")
                return f"I encountered an error: {str(e)}. I apologize, please try rephrasing your question."
        else:
            # For current weather, use Weatherstack API
            # Extract city name from the message using OpenAI's chat model WITH conversation context
            try:
                extraction_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helper that extracts city names from user messages about weather. Look at the conversation history to resolve pronouns like 'there'. If no city is mentioned, return 'NONE'. Otherwise, return only the city name, nothing else."},
                        *conversation_input  # Include conversation history for context
                    ],
                    temperature=0.3,
                    max_tokens=50
                )
                city = extraction_response.choices[0].message.content.strip()
                
                # If no city was found, use default
                if city == "NONE" or not city:
                    city = "Toronto"
                    weather_info = get_weather_information(city)
                    response = f"I'd love to help with weather! Since you didn't specify a city, let me check Toronto for you. {weather_info}"
                else:
                    weather_info = get_weather_information(city)
                    response = f"Let me check the weather for your destination!\n\n{weather_info}"
            except Exception as e:
                _logs.error(f"Error extracting city: {e}")
                # Fallback to Toronto if extraction fails
                city = "Toronto"
                weather_info = get_weather_information(city)
                response = f"I'd love to help with weather! Let me check Toronto for you. {weather_info}"
            
            return response
    
    # Service 2: City information search
    elif "tell me about" in message_lower or any(word in message_lower for word in ["planning a trip to", "i'm visiting", "i'm going to", "visiting", "going to", "traveling to", "travelling to", "heading to"]):
        # Extract city name from the message using OpenAI WITH conversation context
        try:
            extraction_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helper that extracts city names from user messages. Look at the conversation history to resolve pronouns like 'the city' or 'that place'. If no city is mentioned, return 'NONE'. Otherwise, return only the city name, nothing else."},
                    *conversation_input  # Include conversation history for context
                ],
                temperature=0.3,
                max_tokens=50
            )
            city = extraction_response.choices[0].message.content.strip()
            
            # If no city was found, use the message as-is for semantic search
            if city == "NONE" or not city:
                search_results = search_travel_document(message, n_results=1)
            else:
                search_results = search_travel_document(city, n_results=1)
            
            response = f"I love that destination! Let me share what I know. {search_results}"
            return response
        except Exception as e:
            _logs.error(f"Error extracting city for Service 2: {e}")
            # Fallback to direct search if extraction fails
            search_results = search_travel_document(message, n_results=1)
            response = f"I love that destination! Let me share what I know. {search_results}"
            return response
    
    # Service 3: Currency conversion using function calling
    elif any(word in message_lower for word in ["convert", "currency", "exchange", "euro", "usd", "cad", "pound", "yen", "yuan", "money", "budget", "cost", "eur", "gbp", "jpy", "aed", "dirham", "peso", "rupee", "krone", "franc", "shekel", "dinar"]):
        instructions = get_system_instructions()
        
        # Use OpenAI function calling for currency conversion
        try:
            response_obj = client.responses.create(
                model=open_ai_model,
                instructions=instructions,
                input=conversation_input,
                tools=tools,
            )
            
            conversation_input += response_obj.output
            
            # Handle function calls if any
            for item in response_obj.output:
                if item.type == "function_call":
                    if item.name == "convert_currency":
                        args = json.loads(item.arguments)
                        
                        # Call the actual function
                        result = convert_currency(**args)
                        
                        # If currency is unsupported, use OpenAI to get conversion info
                        if result == "UNSUPPORTED":
                            # Build a clean chat messages list for the fallback
                            fallback_messages = []
                            for msg in history:
                                fallback_messages.append({
                                    "role": msg.get("role"),
                                    "content": msg.get("content")
                                })
                            # Add the current request
                            fallback_messages.append({
                                "role": "user",
                                "content": message
                            })
                            # Add the follow-up question
                            fallback_messages.append({
                                "role": "user",
                                "content": f"What is the approximate conversion rate for {args.get('amount', '')} {args.get('from_currency', '').upper()} to {args.get('to_currency', '').upper()}? Provide just the rate and converted amount."
                            })
                            
                            gpt_response = client.chat.completions.create(
                                model=open_ai_model,
                                messages=[
                                    {"role": "system", "content": instructions},
                                    *fallback_messages
                                ],
                                temperature=0.7
                            )
                            
                            # Combine the disclaimer with OpenAI's approximation
                            disclaimer = f"I'm sorry, but {args.get('to_currency', '').upper()} is not supported by my primary currency exchange service provider. Checking with a secondary resource for an approximate conversion...\n\n"
                            approximation = gpt_response.choices[0].message.content
                            
                            return disclaimer + approximation
                        
                        # Add function call result to conversation
                        func_call_output = {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps({
                                "result": result
                            })
                        }
                        
                        conversation_input = conversation_input + [func_call_output]
                        
                        # Make second API call with function result
                        response_obj = client.responses.create(
                            model=open_ai_model,
                            instructions=instructions,
                            tools=tools,
                            input=conversation_input
                        )
                        break
            
            return response_obj.output_text
            
        except Exception as e:
            _logs.error(f"Error in currency conversion: {e}")
            return f"I encountered an error with currency conversion: {str(e)}"
    
    # General conversation - use the model's knowledge
    else:
        try:
            instructions = get_system_instructions()
            response_obj = client.chat.completions.create(
                model=open_ai_model,
                messages=[
                    {"role": "system", "content": instructions},
                    *conversation_input
                ],
                temperature=0.7
            )
            return response_obj.choices[0].message.content
        except Exception as e:
            _logs.error(f"Error in general chat: {e}")
            return f"I encountered an error: {str(e)}. I apologize, please try rephrasing your question so I can try again."


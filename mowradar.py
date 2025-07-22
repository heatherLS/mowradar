
import openai
import streamlit as st
import requests

# Streamlit layout
st.set_page_config(page_title="MowRadar™ - Local Touch + Social Proof", layout="centered")
st.title("🌤️ MowRadar™ - Hyper-Local Add-On Pitch Assistant")

# User input
address = st.text_input("📍 Enter Customer Address or ZIP Code:")
tone = st.radio("🎭 Choose Tone:", ["Professional", "Funny"])
has_bushes = st.checkbox("Customer has bushes", value=True)
has_flowerbeds = st.checkbox("Customer has flower beds", value=True)
submit = st.button("🚀 Generate Talking Points")

# Secrets
WEATHERAPI_KEY = st.secrets["WEATHERAPI_KEY"]
GEOCODE_KEY = st.secrets["GEOCODE_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

GEOCODE_URL = "https://api.opencagedata.com/geocode/v1/json"
WEATHER_URL = "http://api.weatherapi.com/v1"
REVERSE_GEO_URL = "https://nominatim.openstreetmap.org/reverse"

def get_lat_lon(location):
    res = requests.get(GEOCODE_URL, params={
        "q": location,
        "key": GEOCODE_KEY,
        "countrycode": "us"
    })
    results = res.json()
    if results["results"]:
        geometry = results["results"][0]["geometry"]
        return geometry["lat"], geometry["lng"], results["results"][0]["formatted"]
    return None, None, None

def get_local_details(lat, lon):
    res = requests.get(REVERSE_GEO_URL, params={
        "lat": lat,
        "lon": lon,
        "format": "jsonv2"
    }, headers={"User-Agent": "MowRadarBot"})
    data = res.json()
    address = data.get("address", {})
    
    road = address.get("road", "")
    neighbourhood = address.get("neighbourhood", "")
    suburb = address.get("suburb", "")
    city = address.get("city", "") or address.get("town", "") or address.get("village", "")
    county = address.get("county", "")
    state = address.get("state", "")
    
    return road, neighbourhood, suburb, city, county, state


def get_weather_summary(lat, lon):
    current = requests.get(f"{WEATHER_URL}/current.json", params={
        "key": WEATHERAPI_KEY,
        "q": f"{lat},{lon}"
    }).json()

    forecast = requests.get(f"{WEATHER_URL}/forecast.json", params={
        "key": WEATHERAPI_KEY,
        "q": f"{lat},{lon}",
        "days": 3
    }).json()

    return current, forecast

def get_weather_based_services(condition, temp_f, forecast_texts):
    conditions = " ".join(forecast_texts).lower()
    recommendations = ["Lawn Treatment", "Mosquito Treatment"]

    if "hot" in conditions or temp_f >= 85:
        recommendations.append("Lawn Treatment")
    if "rain" in conditions or "thunder" in conditions or "humid" in conditions:
        recommendations.append("Mosquito Treatment")
    if "sun" in conditions or "dry" in conditions:
        recommendations.append("Bush Trimming")
    if "cloud" in conditions or "mild" in conditions or "overcast" in conditions:
        recommendations.append("Flower Bed Weeding")
    if "wind" in conditions or "leaves" in conditions:
        recommendations.append("Leaf Removal")

    return list(set(recommendations))

def build_prompt(city, road, tone, current, forecast, services, has_bushes, has_flowerbeds, neighbourhood, suburb, county, state):
    condition = current['current']['condition']['text']
    temp_f = current['current']['temp_f']
    forecast_texts = [f"{day['date']}: {day['day']['condition']['text']}, high of {day['day']['maxtemp_f']}°F"
                      for day in forecast['forecast']['forecastday']]

    # Clean service list
    if not has_bushes and "Bush Trimming" in services:
        services.remove("Bush Trimming")
    if not has_flowerbeds and "Flower Bed Weeding" in services:
        services.remove("Flower Bed Weeding")

    # Build lead-in order based on what they have
    priority_order = []
    if has_bushes:
        priority_order.append("Bush Trimming")
    if has_flowerbeds:
        priority_order.append("Flower Bed Weeding")

    # Add rest of services, keeping original order but removing duplicates
    remaining_services = [s for s in services if s not in priority_order]
    final_services = priority_order + remaining_services

    services_text = ", ".join(final_services)


    services_text = ", ".join(services)
    location_hierarchy = [neighbourhood, suburb, city, county, state]
    local_ref = next((loc for loc in location_hierarchy if loc), "your area")




    prompt = f"""
You are a lawn care expert who has mastered the books "The Psychology of Selling and Persuasion" and "How to win Friends and Influence People" and you're upselling add-on services to a customer who just booked a mow with you. 

The customer lives near {local_ref}. Current weather is {condition}, {temp_f}°F.
Here’s the detailed 3-day weather outlook they’ll be experiencing: {"; ".join(forecast_texts)}.
Use this info to tailor your recommendations based on heat, rain, overgrowth, or pest activity.


Use a {tone.lower()} tone.

The customer has bushes: {has_bushes}
The customer has flower beds: {has_flowerbeds}

Your goal is to recommend 1–2 relevant **add-on services** from this list, based on weather and season: {services_text}

If Bush Trimming or Flower Bed Weeding is in the list, prioritize those unless the weather makes it strongly unsuitable.


Mowing is already scheduled. Use persuasive psychology by:
- Referencing common local patterns (like heat, leaf drop, or bugs in {city})
- Highlighting what they’ll avoid: “No more spending weekends tugging at weeds...”
- Adding urgency: “This is the perfect window before overgrowth kicks in...”
- Using social proof: “Most of my customers today have added...”
- Mentioning comfort: “Safer, mosquito-free space for kids and pets”
- Suggesting efficiency: “Bundling saves time”
- Use the location name “{local_ref}” naturally in your talking points — this should be a recognizable neighborhood or city name, not a full street address.
- Avoid overusing the exact neighborhood name. Mention it once if it feels natural, but don't repeat it.




Avoid recommending hydration or watering.

Write 2 short, natural-sounding talking points a rep can say. Use casual, confident language that feels like a helpful conversation — not a script. Include the local reference “{local_ref}” once if it feels natural. Avoid overexplaining.
"""
    return prompt

import openai

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def generate_blurb(prompt, model="gpt-4o"):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=500
    )
    message = response.choices[0].message.content

    # Token tracking
    usage = response.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens

    return message, prompt_tokens, completion_tokens, total_tokens

    
    # Token tracking
    usage = response['usage']
    prompt_tokens = usage['prompt_tokens']
    completion_tokens = usage['completion_tokens']
    total_tokens = usage['total_tokens']
    
    return message, prompt_tokens, completion_tokens, total_tokens


# Handle submission
if submit and address:
    lat, lon, formatted_location = get_lat_lon(address)
    
    if lat:  # ✅ valid lat/lon found
        st.success(f"📍 Location detected: {formatted_location}")
        road, neighbourhood, suburb, city, county, state = get_local_details(lat, lon)
        current_weather, forecast_weather = get_weather_summary(lat, lon)
        forecast_conditions = [day['day']['condition']['text'] for day in forecast_weather['forecast']['forecastday']]
        services = get_weather_based_services(current_weather['current']['condition']['text'], current_weather['current']['temp_f'], forecast_conditions)

        prompt = build_prompt(
            city, road, tone, current_weather, forecast_weather,
            services, has_bushes, has_flowerbeds, neighbourhood, suburb, county, state
        )

        with st.spinner("Generating hyper-local, social-proofed lawn talk..."):
            try:
                blurb, prompt_tokens, completion_tokens, total_tokens = generate_blurb(prompt, "gpt-4o")
                st.markdown("### 💬 Your Local-Aware Talking Points:")
                st.write(blurb)
                st.code(blurb, language='markdown')

                with st.expander("📊 Token Usage Details"):
                    st.write(f"• Prompt tokens: {prompt_tokens}")
                    st.write(f"• Completion tokens: {completion_tokens}")
                    st.write(f"• Total tokens: {total_tokens}")
                    st.write(f"💰 Estimated cost: ${round((prompt_tokens * 0.005 + completion_tokens * 0.015) / 1000, 4)} (using gpt-4o pricing)")
            except Exception as e:
                st.error(f"❌ Error generating blurb: {e}")
    else:
        st.error("❌ Unable to find that location. Please check the address or ZIP.")

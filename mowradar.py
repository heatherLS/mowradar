import streamlit as st
import requests
import openai
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="MowRadar Vision – Smart Sales Bullets", layout="centered")
st.title("📍 MowRadar Vision – Real Rep Talking Points")

# --- Inputs ---
address = st.text_input("Enter full customer address:")
service = st.selectbox("Choose a service to upsell:", [
    "Bush Trimming", "Mosquito Treatment", "Lawn Treatment", "Flower Bed Weeding", "Leaf Removal"
])
submit = st.button("Generate Talking Points")

# --- Secrets ---
MAPS_API_KEY = st.secrets["GOOGLE_MAPS_STATIC_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
GEOCODE_KEY = st.secrets["GEOCODE_KEY"]
WEATHERAPI_KEY = st.secrets["WEATHERAPI_KEY"]

# --- Location + Local Details ---
def get_lat_lon(address):
    res = requests.get("https://api.opencagedata.com/geocode/v1/json", params={
        "q": address,
        "key": GEOCODE_KEY,
        "countrycode": "us"
    }).json()
    if res["results"]:
        g = res["results"][0]["geometry"]
        return g["lat"], g["lng"]
    return None, None

def get_local_details(lat, lon):
    res = requests.get("https://nominatim.openstreetmap.org/reverse", params={
        "lat": lat,
        "lon": lon,
        "format": "jsonv2"
    }, headers={"User-Agent": "MowRadar"})
    address = res.json().get("address", {})
    return (
        address.get("neighbourhood", ""),
        address.get("suburb", ""),
        address.get("city", "") or address.get("town", "") or address.get("village", ""),
        address.get("county", ""),
        address.get("state", "")
    )

# --- Street View ---
def get_street_view_image(lat, lon):
    url = f"https://maps.googleapis.com/maps/api/streetview?size=640x640&location={lat},{lon}&key={MAPS_API_KEY}"
    r = requests.get(url)
    return r.content

# --- Weather ---
def get_weather(lat, lon):
    current = requests.get("http://api.weatherapi.com/v1/current.json", params={
        "key": WEATHERAPI_KEY, "q": f"{lat},{lon}"
    }).json()
    forecast = requests.get("http://api.weatherapi.com/v1/forecast.json", params={
        "key": WEATHERAPI_KEY, "q": f"{lat},{lon}", "days": 3
    }).json()
    return current, forecast

# --- Prompt Builder ---
def build_prompt(service, location_ref, condition, temp, forecast_data):
    forecast_lines = "; ".join(
        f"{day['date']}: {day['day']['condition']['text']}, high of {day['day']['maxtemp_f']}°F"
        for day in forecast_data["forecast"]["forecastday"]
    )

    return f"""
You are a persuasive, friendly lawn care rep talking to a homeowner in {location_ref}.

Current weather: {condition}, {temp}°F  
3-day forecast: {forecast_lines}

1. First, write one short sentence that a rep can say to lead into the pitch. It should:
- Mention the service: {service}
- Reference social proof or local trends (e.g., “A lot of my customers in {location_ref} are...”)
- Sound natural on a phone call

2. Then, write 4–5 short bullet points that:
- Explain WHY this service is helpful right now
- Include local climate/yard issues (e.g., fire ants, patchy grass, rapid growth)
- Mention common problems if ignored
- Be natural, helpful, easy to say (not overly scripted)
- No full address, no titles — just casual bullets
Return only the rep lead-in sentence and the bullet points.
"""

# --- OpenAI Completion ---
def generate_bullets(prompt):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.85,
        max_tokens=500
    )
    return response.choices[0].message.content

# --- Main App ---
if submit and address:
    lat, lon = get_lat_lon(address)
    if not lat:
        st.error("Could not find location.")
    else:
        neigh, suburb, city, county, state = get_local_details(lat, lon)
        location_ref = next((loc for loc in [neigh, suburb, city, county] if loc), "your area")

        with st.spinner("📷 Loading Street View..."):
            image_bytes = get_street_view_image(lat, lon)
            st.image(Image.open(BytesIO(image_bytes)), caption="Front View – Google Street View")

        with st.spinner("🌦️ Fetching Weather..."):
            current, forecast = get_weather(lat, lon)
            condition = current["current"]["condition"]["text"]
            temp = current["current"]["temp_f"]

        with st.spinner("💬 Generating Talking Points..."):
            prompt = build_prompt(service, location_ref, condition, temp, forecast)
            bullets = generate_bullets(prompt)

        st.markdown(f"### 🛠️ Use This on the Call:")
        st.write(bullets)
        st.code(bullets, language="markdown")

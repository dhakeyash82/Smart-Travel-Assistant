# app.py
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import requests
import math
import time
import random

app = Flask(__name__)

# ------------------- HARDCODED API KEYS -------------------
OWM_API_KEY = "a0b846f370c1e866b0e8292a7c261114"

FOURSQUARE_KEY = "0NXMK2QC2J0XWMRJGMZ20BWMRJCNFXOW3MZ2USHS0KSMYHOB"

NEWS_API_KEY = "9035ca6d604149d2af854acc94133429"


# ------------------- HELPERS -------------------
def log(*args):
    print("[LOG]", *args)

# ------------------- SAFETY RISK SCORING -------------------
RISK_PENALTIES = {
    # High Security / Civil Unrest Risk (Score -40)
    "KASHMIR": -40,      # Jammu & Kashmir Valley
    "SRINAGAR": -40,
    "JAMMU": -40,
    "MANIPUR": -40,      # Ongoing civil unrest
    "IMPHAL": -40,
    
    # Moderate Natural Disaster Risk (Score -20)
    "NEPAL": -20,        # High risk of earthquakes, floods, and landslides
    "KATHMANDU": -20,

    # Moderate Insurgency / Maoist Risk (Score -15 to -10)
    "CHHATTISGARH": -15, # Naxalite activity risk
    "JHARKA": -15,       # Jharkhand (Naxalite activity risk)
    "NAGALAND": -15,     # Insurgency/crime risk
    "ASSAM": -10,        # Separatist and insurgency risk in certain districts
    "ODISHA": -10,       # Naxalite activity in rural/border areas
    "TELANGANA": -10,
    "ANDHRA PRADESH": -10,
}

def get_safety_risk_penalty(city, country_code):
    """Calculates a penalty score based on known security and disaster risks."""
    city_upper = city.upper()
    
    # 1. Check for country-level risk (e.g., Nepal)
    if country_code == 'NP':
        return RISK_PENALTIES.get("NEPAL", 0)

    # 2. Check for regional/state risk using city/region name match
    for key, penalty in RISK_PENALTIES.items():
        if key in city_upper:
            return penalty
    
    # Default for all other locations
    return 0

# -----------------------------------------------------------

def geocode_city(city):
    """Return (lat, lon, country_code) using OpenWeather geocoding (safe)."""
    try:
        q = requests.utils.requote_uri(city)
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={q}&limit=1&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            log("geocode non-200", r.status_code, r.text[:200])
            return None, None, None
        arr = r.json()
        if not arr:
            return None, None, None
        rec = arr[0]
        return float(rec["lat"]), float(rec["lon"]), rec.get("country")
    except Exception as e:
        log("geocode error", e)
        return None, None, None

# OpenWeather: current weather by coords
def get_current_weather_by_coords(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            log("current weather non-200", r.status_code, r.text[:200])
            return None
        d = r.json()
        return {
            "temp": int(round(d.get("main", {}).get("temp"))) if d.get("main") else None,
            "feels_like": int(round(d.get("main", {}).get("feels_like"))) if d.get("main") else None,
            "desc": (d.get("weather") or [{}])[0].get("description", "").title(),
            "humidity": d.get("main", {}).get("humidity"),
            "wind": d.get("wind", {}).get("speed"),
            "sunrise": d.get("sys", {}).get("sunrise"),
            "sunset": d.get("sys", {}).get("sunset")
        }
    except Exception as e:
        log("get_current_weather error", e)
        return None

# OpenWeather: 5-day / 3-hour forecast (free)
def get_5day_forecast_by_coords(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            log("forecast non-200", r.status_code, r.text[:200])
            return None
        d = r.json()
        # aggregate into daily buckets: date -> list of entries
        daily = {}
        for item in d.get("list", []):
            dt = datetime.utcfromtimestamp(item["dt"]).date()
            daily.setdefault(dt, []).append(item)
        # compute simple daily summaries
        days = {}
        for dt, items in daily.items():
            temps = [it["main"]["temp"] for it in items if "main" in it]
            hums = [it["main"].get("humidity", 0) for it in items]
            winds = [it.get("wind", {}).get("speed", 0) for it in items]
            descs = [it.get("weather", [{}])[0].get("main", "") for it in items]
            days[dt] = {
                "temp": int(round(sum(temps)/len(temps))) if temps else None,
                "feels_like": None,
                "desc": max(set(descs), key=descs.count) if descs else "",
                "humidity": int(round(sum(hums)/len(hums))) if hums else None,
                "wind": round(sum(winds)/len(winds),1) if winds else None,
                "rain": any(it.get("rain") for it in items)
            }
        return days
    except Exception as e:
        log("get_5day_forecast error", e)
        return None

# Air quality (try OWM air_pollution; if fails, return None)
def get_aqi(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            log("air_pollution non-200", r.status_code, r.text[:200])
            return None
        d = r.json()
        idx = d.get("list", [{}])[0].get("main", {}).get("aqi")
        mapping = {1:25,2:75,3:125,4:200,5:300}
        return mapping.get(idx, 80)
    except Exception as e:
        log("get_aqi error", e)
        return None

# choose forecast for target_date from forecast_days (dict date->summary) or current
def choose_forecast_for_date(forecast_days, current, target_date):
    """
    forecast_days: dict {date: summary} from get_5day_forecast_by_coords
    current: current weather dict from get_current_weather_by_coords
    target_date: date
    """
    fallback = {"temp": None, "feels_like": None, "desc": "Unknown", "humidity": None, "wind": None, "rain": False}
    if forecast_days:
        if target_date in forecast_days:
            item = forecast_days[target_date]
            return {
                "temp": item.get("temp"),
                "feels_like": item.get("feels_like"),
                "desc": item.get("desc").title() if item.get("desc") else "Unknown",
                "humidity": item.get("humidity"),
                "wind": item.get("wind"),
                "rain": item.get("rain", False)
            }
        # if not available, use average of forecast days
        try:
            vals = [v for v in forecast_days.values() if v.get("temp") is not None]
            temps = [v["temp"] for v in vals]
            descs = [v["desc"] for v in vals if v.get("desc")]
            hums = [v["humidity"] for v in vals if v.get("humidity") is not None]
            winds = [v["wind"] for v in vals if v.get("wind") is not None]
            return {
                "temp": int(round(sum(temps)/len(temps))) if temps else (current.get("temp") if current else None),
                "feels_like": None,
                "desc": max(set(descs), key=descs.count).title() if descs else (current.get("desc") if current else "Unknown"),
                "humidity": int(round(sum(hums)/len(hums))) if hums else (current.get("humidity") if current else None),
                "wind": round(sum(winds)/len(winds),1) if winds else (current.get("wind") if current else None),
                "rain": any(v.get("rain") for v in vals)
            }
        except Exception as e:
            log("choose_forecast avg error", e)
            return fallback
    # fallback to current
    if current:
        return {
            "temp": current.get("temp"),
            "feels_like": current.get("feels_like"),
            "desc": current.get("desc"),
            "humidity": current.get("humidity"),
            "wind": current.get("wind"),
            "rain": False
        }
    return fallback

# app.py - NEW HELPER FUNCTION
def summarize_weather_for_range(forecast_days, current, start_date, end_date):
    """Summarize weather data for a trip date range."""
    # List of dates in the range
    date_list = [start_date + timedelta(days=d) for d in range((end_date - start_date).days + 1)]
    
    all_temps = []
    all_descs = []
    all_hums = []
    all_winds = []
    has_rain = False

    for date in date_list:
        # Use existing helper to get forecast for each day
        pred = choose_forecast_for_date(forecast_days, current, date)
        
        if pred["temp"] is not None:
            all_temps.append(pred["temp"])
        # Use the description's main part (e.g., 'Clear' from 'Clear Sky')
        if pred["desc"] not in ("Unknown", ""):
            all_descs.append(pred["desc"].split(" ")[0].title()) 
        if pred["humidity"] is not None:
            all_hums.append(pred["humidity"])
        if pred["wind"] is not None:
            all_winds.append(pred["wind"])
        if pred["rain"]:
            has_rain = True

    if not all_temps:
        return None 
        
    avg_temp = int(round(sum(all_temps) / len(all_temps)))
    
    # Find most common description without importing Counter
    desc_counts = {}
    for desc in all_descs:
        desc_counts[desc] = desc_counts.get(desc, 0) + 1
    most_common_desc = max(desc_counts, key=desc_counts.get) if desc_counts else "Varied"

    # Max/Avg for other metrics
    avg_humidity = int(round(sum(all_hums) / len(all_hums))) if all_hums else None
    avg_wind = round(sum(all_winds) / len(all_winds), 1) if all_winds else None

    return {
        "temp": avg_temp,
        "feels_like": None,
        "desc": f"Avg. {most_common_desc}" if most_common_desc != "Varied" else most_common_desc,
        "humidity": avg_humidity,
        "wind": avg_wind,
        "rain": has_rain
    }

# best day: evaluates ±5 days using available forecast_days/current
def best_day_choice(forecast_src, forecast_dst, center_date):
    best_score = -1e9
    best_date = center_date
    for delta in range(-5, 6):
        cand = center_date + timedelta(days=delta)
        s = choose_forecast_for_date(forecast_src.get("days") if forecast_src else None, forecast_src.get("current") if forecast_src else None, cand)
        d = choose_forecast_for_date(forecast_dst.get("days") if forecast_dst else None, forecast_dst.get("current") if forecast_dst else None, cand)
        if s.get("temp") is None or d.get("temp") is None:
            continue
        s_temp_score = max(0, 100 - abs(s["temp"] - 24) * 4)
        d_temp_score = max(0, 100 - abs(d["temp"] - 24) * 4)
        rain_pen = (30 if s.get("rain") else 0) + (40 if d.get("rain") else 0)
        score = 0.3 * s_temp_score + 0.6 * d_temp_score - rain_pen - abs(delta) * 1.5
        if score > best_score:
            best_score = score
            best_date = cand
    return {"date": best_date, "score": best_score if best_score > -1e8 else 0}

# simple haversine
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    a = math.sin(dlat/2)**2 + math.cos(lat1r)*math.cos(lat2r)*math.sin(dlon/2)**2
    # CRITICAL FIX: Clamp 'a' to [0.0, 1.0] to prevent floating-point errors
    a = max(0.0, min(1.0, a))
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def time_costs(distance_km):
    tc = {"distance_km": distance_km}
    tc["road"] = {"time": f"{max(1, round(distance_km/60))}h", "cost": int(distance_km*3)}
    tc["train"] = {"time": f"{max(1, round(distance_km/80))}h", "cost": int(distance_km*1.5)}
    if distance_km >= 400:
        tc["air"] = {"time": f"{max(1, round(distance_km/700))}h + 2h", "cost": int(distance_km*4.5)}
    return tc

def mode_recommendation(distance_km):
    order = []
    road_score = 100 - (distance_km/20)
    train_score = 100 - (distance_km/30)
    air_score = -999
    if distance_km >= 400:
        air_score = 100 - (distance_km/100)
    ordered = sorted([("Road", road_score), ("Train", train_score), ("Air", air_score)], key=lambda x: x[1], reverse=True)
    for name, sc in ordered:
        if name == "Air" and distance_km < 400:
            continue
        label = "Recommended" if sc >= 60 else ("Good Option" if sc >= 30 else "Optional")
        order.append([name, label])
    return {"recommendation": order[0][0] if order else "Road", "order": order}

def packing_tips(desc, temp, rain, dest_name):
    tips = []
    if rain:
        tips += ["Umbrella / Raincoat", "Waterproof shoes"]
    if temp is not None:
        if temp <= 12:
            tips += ["Warm jacket", "Thermals", "Gloves"]
        elif temp >= 34:
            tips += ["Light cotton clothes", "Sunscreen", "Hat"]
        else:
            tips += ["Layered clothing"]
    if "kashmir" in dest_name.lower() or (temp is not None and temp < 10):
        tips += ["Insulated jacket", "Warm hat"]
    out = []
    for t in tips:
        if t not in out:
            out.append(t)
    return out

# Overpass fallback
def overpass_places(lat, lon, amenity, limit=3):
    q = f"""
    [out:json][timeout:8];
    (
      node["amenity"="{amenity}"](around:3000,{lat},{lon});
      way["amenity"="{amenity}"](around:3000,{lat},{lon});
      relation["amenity"="{amenity}"](around:3000,{lat},{lon});
    );
    out center {limit};
    """
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'),
                          headers={"User-Agent":"SmartTravelAssistant/1.0"}, timeout=12)
        r.raise_for_status()
        data = r.json()
        results = []
        for el in data.get("elements", [])[:limit]:
            tags = el.get("tags", {})
            name = tags.get("name") or amenity.title()
            if 'center' in el:
                plat = el['center']['lat']; plon = el['center']['lon']
            else:
                plat = el.get('lat'); plon = el.get('lon')
            results.append({"name": name, "area": tags.get("addr:street",""), "lat": plat, "lon": plon})
        return results
    except Exception as e:
        log("overpass error", e)
        return []

def foursquare_nearby(lat, lon, query, limit=3):
    try:
        url = "https://api.foursquare.com/v3/places/search"
        headers = {"Accept":"application/json","Authorization":FOURSQUARE_KEY}
        params = {"ll": f"{lat},{lon}", "query": query, "limit": limit}
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 401:
            log("foursquare unauthorized (401)")
            return []
        r.raise_for_status()
        data = r.json()
        out = []
        for p in data.get("results", [])[:limit]:
            name = p.get("name")
            location = p.get("location", {})
            area = location.get("locality") or location.get("region") or location.get("formatted_address","")
            coords = p.get("geocodes", {}).get("main", {})
            plat = coords.get("latitude"); plon = coords.get("longitude")
            out.append({"name": name, "area": area, "lat": plat, "lon": plon})
        return out
    except Exception as e:
        log("foursquare error", e)
        return []

def get_nearby_essentials(lat, lon):
    results = []
    for q in ["ATM","Hospital","Pharmacy"]:
        items = foursquare_nearby(lat, lon, q, limit=2)
        if not items:
            items = overpass_places(lat, lon, q.lower(), limit=2)
        for it in items:
            dkm = None
            try:
                if it.get("lat") and it.get("lon"):
                    dkm = round(haversine_km(lat, lon, float(it["lat"]), float(it["lon"])),2)
            except:
                dkm = None
            results.append({"type": q, "name": it.get("name"), "area": it.get("area"), "distance_km": dkm})
    return results

def news_alerts_for_city(city):
    try:
        terms = "disaster OR flood OR cyclone OR earthquake OR landslide OR alert OR emergency OR storm OR warning"
        
        # 1. Define the User-Agent Header (Crucial for server identification)
        headers = {
            'User-Agent': 'Smart-Travel-Assistant-Server-App/1.0 (India Domestic Travel)'
        }
        
        # 2. Define the URL endpoint
        url = "https://newsapi.org/v2/everything"
        
        # 3. Define ALL Query Parameters in a Dictionary (Best Practice for encoding)
        params = {
            'q': f"{city} AND ({terms})", # Combine city and terms cleanly
            'pageSize': 6,
            'sortBy': 'publishedAt',
            'apiKey': NEWS_API_KEY
        }
        
        # 4. Use requests.get with params and headers
        r = requests.get(url, headers=headers, params=params, timeout=10)
        
        if r.status_code == 401:
            log("newsapi unauthorized (401)")
            return []
        
        r.raise_for_status() # This will raise an error on 403 or 404.
        
        data = r.json()
        articles = data.get("articles", [])
        out = [{"title": a.get("title"), "url": a.get("url"), "publishedAt": a.get("publishedAt")} for a in articles]
        return out
        
    except requests.exceptions.HTTPError as e:
        # Check specifically for the 403 error here
        if r.status_code == 403:
             log(f"NewsAPI Error 403: Check User-Agent or API key restrictions. Details: {r.text}")
             return [{"title": f"News service restricted. (Error 403/CORS)"}]
        
        log(f"newsapi HTTP error: {e}")
        return []
        
    except Exception as e:
        log(f"newsapi general error: {e}")
        return []
    
def booking_links_for_country(country_code):
    mapping = {
        "IN": [
            {"label":"IRCTC (Trains)", "url":"https://www.irctc.co.in/"},
            {"label":"MakeMyTrip (Flights & Hotels)", "url":"https://www.makemytrip.com/flights/"},
            {"label":"redBus (Buses)", "url":"https://www.redbus.in/"},
            {"label":"Cleartrip (Flights & Hotels)", "url":"https://www.cleartrip.com/"}
        ],
        "NP": [
            {"label":"Buddha Air (Flights)", "url":"https://www.buddhaair.com/"},
            {"label":"Yeti Airlines", "url":"https://www.yetiairlines.com/"},
            {"label":"Booking.com (Hotels)", "url":"https://www.booking.com/"}
        ],
        "US": [
            {"label":"Amtrak (Trains)", "url":"https://www.amtrak.com/"},
            {"label":"Google Flights", "url":"https://www.google.com/flights"},
            {"label":"Expedia (Flights & Hotels)", "url":"https://www.expedia.com/"},
            {"label":"Greyhound (Buses)", "url":"https://www.greyhound.com/"}
        ],
        "GB": [
            {"label":"Trainline (Trains)", "url":"https://www.thetrainline.com/"},
            {"label":"Skyscanner (Flights)", "url":"https://www.skyscanner.net/"},
            {"label":"Booking.com (Hotels)", "url":"https://www.booking.com/"}
        ],
    }
    if country_code in mapping:
        return mapping[country_code]
    return [
        {"label":"Skyscanner (Flights)", "url":"https://www.skyscanner.net/"},
        {"label":"Google Flights", "url":"https://www.google.com/flights"},
        {"label":"Booking.com (Hotels)", "url":"https://www.booking.com/"},
        {"label":"Expedia (Flights & Hotels)", "url":"https://www.expedia.com/"}
    ]

# ------------------- ROUTES -------------------
@app.route("/")
def home():
    return render_template("index.html")

# app.py - Modified /api/analyze route
@app.route("/api/analyze", methods=["POST"])
def analyze():
    t0 = time.time()
    try:
        payload = request.get_json() or {}
        src = (payload.get("source_city") or "").strip()
        dst = (payload.get("dest_city") or "").strip()
        from_date_str = payload.get("from_date")
        to_date_str = payload.get("to_date")

        if not src or not dst or not from_date_str or not to_date_str:
            return jsonify({"error":"Please provide source_city, dest_city, from_date and to_date (YYYY-MM-DD)"}), 400

        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
        except:
            return jsonify({"error":"Invalid date format. Use YYYY-MM-DD"}), 400

        if from_date > to_date:
             return jsonify({"error":"'From Date' cannot be after 'To Date'."}), 400

        if (to_date - from_date).days > 7:
             return jsonify({"error":"Trip duration cannot exceed 7 days due to limited forecast data."}), 400

        # geocode both cities
        src_lat, src_lon, src_country = geocode_city(src)
        dst_lat, dst_lon, dst_country = geocode_city(dst)
        if src_lat is None or dst_lat is None:
            return jsonify({"error":"Could not geocode source or destination"}), 400

        # current + 5-day forecast
        src_current = get_current_weather_by_coords(src_lat, src_lon)
        dst_current = get_current_weather_by_coords(dst_lat, dst_lon)
        src_forecast_days = get_5day_forecast_by_coords(src_lat, src_lon)
        dst_forecast_days = get_5day_forecast_by_coords(dst_lat, dst_lon)

        # build structures useful for functions above
        one_src = {"current": src_current, "days": src_forecast_days}
        one_dst = {"current": dst_current, "days": dst_forecast_days}

        # chosen forecasts for the date *range*
        src_summary = summarize_weather_for_range(one_src["days"], one_src["current"], from_date, to_date)
        dst_summary = summarize_weather_for_range(one_dst["days"], one_dst["current"], from_date, to_date)
        
        if src_summary is None or dst_summary is None:
            return jsonify({"error":"Could not fetch complete weather data for the selected range."}), 400

        # fetch AQI
        src_aqi = get_aqi(src_lat, src_lon) or 80
        dst_aqi = get_aqi(dst_lat, dst_lon) or 80

        # distance (great-circle approx)
        distance_km = int(round(haversine_km(src_lat, src_lon, dst_lat, dst_lon)))

        # time & cost
        tc = time_costs(distance_km)

        # mode rec
        modes = mode_recommendation(distance_km)

        # packing tips (use destination summary)
        tips = packing_tips(dst_summary.get("desc",""), dst_summary.get("temp"), dst_summary.get("rain", False), dst)

        # nearby essentials
        essentials = get_nearby_essentials(dst_lat, dst_lon)

        # news alerts (disaster related)
        alerts = news_alerts_for_city(dst)
        if not alerts:
            alerts = [{"title":"No need to worry — no major disaster-related news found for your destination recently."}]

        # booking links per country
        booking_links = booking_links_for_country(dst_country)

        # best day (±5 days), center on the start date
        best = best_day_choice(one_src, one_dst, from_date)

        # scores
        temp = dst_summary.get("temp") or 25
        dst_city_upper = dst.upper() # Use UPPERCASE for RISK_PENALTIES lookup
        
        # --- PENALTY LOGIC ---
        
        # 1. Weather Penalty (Only penalize if TOO high or TOO low)
        weather_penalty = 0
        if temp < 10: # Very Cold
            weather_penalty = (10 - temp) * 4 
        elif temp > 32: # Very Hot
            weather_penalty = (temp - 32) * 5
        weather_penalty = min(30, weather_penalty) 

        # 2. AQI Penalty (Location Penalty for pollution, applies only if AQI > 150)
        aqi_penalty = 0
        if dst_aqi > 150:
            aqi_penalty = (dst_aqi - 150) / 10
        aqi_penalty = min(25, aqi_penalty)
        
        # 3. News Risk Penalty (Location Penalty for active risk/disaster alerts)
        num_alerts = len([a for a in alerts if "No need to worry" not in a.get("title", "")])
        news_penalty = min(10, num_alerts * 5)

        # 4. Geopolitical/Known Location Penalty (Uses the user-provided RISK_PENALTIES map)
        geo_penalty = 0
        
        # Check all keys in the RISK_PENALTIES map
        for key, penalty_value in RISK_PENALTIES.items():
            # Check if the key is in the destination name (e.g., 'SRINAGAR' in 'SRINAGAR, J&K')
            if key in dst_city_upper:
                 geo_penalty = max(geo_penalty, abs(penalty_value)) # Apply the highest matching penalty

        # --- FINAL SCORE CALCULATION ---
        
        # Score component for breakdown: based on original 24C logic (used only for display)
        weather_score = int(max(0, 100 - abs(temp - 24)*3))
        
        # Overall score: Starts at 100, deducts all extreme/risk penalties.
        overall = 100 - weather_penalty - aqi_penalty - news_penalty - geo_penalty
        overall = int(max(40, min(100, overall))) # Ensures minimum score of 75

        # News Score component for breakdown display (reflects impact of AQI, News, and Geo penalties)
        news_score_display = int(max(0, 100 - (aqi_penalty*2 + news_penalty*4 + geo_penalty))) 

        response = {
            "source": {"city": src, "weather": src_summary, "aqi": src_aqi},
            "destination": {"city": dst, "weather": dst_summary, "aqi": dst_aqi},
            "scores": {"overall": overall, "weather_score": weather_score, "news_score": news_score_display},
            "forecast_best_day": {"day": best['date'].strftime("%Y-%m-%d"), "score": int(round(best['score']))},
            "packing_tips": tips,
            "mode": {"recommendation": modes.get("recommendation"), "order": modes.get("order")},
            "time_cost": tc,
            "news": alerts,
            "essentials": essentials,
            "booking_links": booking_links,
            "runtime_s": round(time.time()-t0,2)
        }
        return jsonify(response)
    except Exception as e:
        log("analyze exception", e)
        return jsonify({"error":"Internal server error"}), 500

if __name__ == "__main__":
    app.run()
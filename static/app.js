// static/app.js
document.addEventListener("DOMContentLoaded", () => {

  const analyzeBtn = document.getElementById("analyzeBtn");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const form = document.getElementById("tripForm");
  const results = document.getElementById("results");

  const srcTitle = document.getElementById("srcTitle");
  const dstTitle = document.getElementById("dstTitle");
  const srcWeather = document.getElementById("srcWeather");
  const dstWeather = document.getElementById("dstWeather");
  const srcMeta = document.getElementById("srcMeta");
  const dstMeta = document.getElementById("dstMeta");
  const score = document.getElementById("score");
  const scoreBreak = document.getElementById("scoreBreak");
  const bestDay = document.getElementById("bestDay");
  const tipsUl = document.getElementById("tips");
  const modeP = document.getElementById("mode");
  const modeOrder = document.getElementById("modeOrder");
  const dtc = document.getElementById("dtc");
  const newsUl = document.getElementById("news");
  const bookingDiv = document.getElementById("bookingLinks");
  const essentialsUl = document.getElementById("essentials");

  function nl(x){ return x == null ? "—" : x; }

  

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    results.classList.add("hidden");

    // --- START NEW LOADING LOGIC ---
    analyzeBtn.disabled = true;
    loadingIndicator.classList.remove("hidden");
    // --- END NEW LOADING LOGIC ---
    const fd = new FormData(form);
    const payload = {
      source_city: fd.get("source_city"),
      dest_city: fd.get("dest_city"),
      from_date: fd.get("from_date"), // Changed from 'date'
      to_date: fd.get("to_date") // Added
    };

    // loading state
    [srcWeather,dstWeather,score,scoreBreak,bestDay,modeP,dtc].forEach(el => el.textContent = "Loading…");
    tipsUl.innerHTML = ""; newsUl.innerHTML = ""; bookingDiv.innerHTML = ""; essentialsUl.innerHTML = ""; modeOrder.innerHTML = "";

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(payload)
      });

      if(!res.ok){
        const err = await res.json().catch(()=>({error:"Server error"}));
        alert(err.error || `Server returned ${res.status}`);
        return;
      }

      const data = await res.json();

      // reveal results
      results.classList.remove("hidden");

      // Source
      srcTitle.textContent = `Source: ${nl(data.source.city)}`;
      const s = data.source.weather || {};
      srcWeather.textContent = `${nl(s.temp)}°C • ${nl(s.desc)}`;
      srcMeta.textContent = `Humidity: ${nl(s.humidity)}% | Wind: ${nl(s.wind)} m/s | AQI: ${nl(data.source.aqi)}`;

      // Destination
       dstTitle.textContent = `Destination Trip Summary: ${nl(data.destination.city)}`; // Updated title
      const d = data.destination.weather || {};
      const rain_status = d.rain ? "Rain Likely" : "No Major Rain";
      dstWeather.textContent = `${nl(d.temp)}°C • ${nl(d.desc)} (${rain_status})`; // Updated display to reflect summary/rain status
      dstMeta.textContent = `Avg. Humidity: ${nl(d.humidity)}% | Avg. Wind: ${nl(d.wind)} m/s | Avg. AQI: ${nl(data.destination.aqi)}`;

      // Scores & Best day
      score.textContent = `${nl(data.scores.overall)}/100`;
      scoreBreak.textContent = `Weather=${nl(data.scores.weather_score)} • News=${nl(data.scores.news_score)}`;
      bestDay.textContent = `${nl(data.forecast_best_day.day)} (score ${nl(data.forecast_best_day.score)})`;

      // Packing tips
      tipsUl.innerHTML = "";
      (data.packing_tips || []).forEach(t=>{
        const li = document.createElement("li"); li.textContent = t; tipsUl.appendChild(li);
      });

      // Mode
      modeP.textContent = `Recommendation: ${nl(data.mode.recommendation)}`;
      modeOrder.innerHTML = "";
      (data.mode.order || []).forEach(pair=>{
        const li = document.createElement("li"); li.textContent = `${pair[0]} — ${pair[1]}`; modeOrder.appendChild(li);
      });

      // Time & cost
      dtc.innerHTML = "";
      if(data.time_cost){
        dtc.innerHTML += `Distance: ${nl(data.time_cost.distance_km)} km<br/>`;
        if(data.time_cost.road) dtc.innerHTML += `Road: ${nl(data.time_cost.road.time)}, ₹${nl(data.time_cost.road.cost)}<br/>`;
        if(data.time_cost.train) dtc.innerHTML += `Train: ${nl(data.time_cost.train.time)}, ₹${nl(data.time_cost.train.cost)}<br/>`;
        if(data.time_cost.air) dtc.innerHTML += `Air: ${nl(data.time_cost.air.time)}, ₹${nl(data.time_cost.air.cost)}<br/>`;
      }

      // News / Alerts
      newsUl.innerHTML = "";
      (data.news || []).forEach(n=>{
        const li = document.createElement("li");
        if(n.url){
          const a = document.createElement("a"); a.href = n.url; a.target="_blank"; a.textContent = n.title || "News";
          li.appendChild(a);
        }else{
          li.textContent = n.title || "(notice)";
        }
        newsUl.appendChild(li);
      });

      // Booking links
      bookingDiv.innerHTML = "";
      (data.booking_links || []).forEach(b=>{
        const a = document.createElement("a"); a.href = b.url; a.target="_blank"; a.className="booking-link";
        a.textContent = b.label;
        bookingDiv.appendChild(a);
      });

      // Essentials
      essentialsUl.innerHTML = "";
      (data.essentials || []).forEach(e=>{
        const li = document.createElement("li");
        let s = `${nl(e.type)}: ${nl(e.name)}`;
        if(e.area) s += ` — ${e.area}`;
        if(e.distance_km) s += ` — ${e.distance_km} km`;
        li.textContent = s;
        essentialsUl.appendChild(li);
      });

    } catch(err){
      console.error("Fetch error", err);
      alert("Network or server error. Check backend logs.");
      // Ensure results are visible to display alert/error content
      results.classList.remove("hidden"); 
      score.textContent = "Error: See alert for details."; 
    } finally {
      // --- FINAL UI RESET (Must run regardless of success or failure) ---
      analyzeBtn.disabled = false; // Re-enable the button
      loadingIndicator.classList.add("hidden"); // Hide the loading message
      // --- END FINAL UI RESET ---
    }
  }); // <--- This closes the submit event listener
}); // <--- This c


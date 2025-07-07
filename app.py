import streamlit as st
import pandas as pd

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Load CSV files
prop = pd.read_csv("propositions.csv")
rating = pd.read_csv("rating.csv")
id_table = pd.read_csv("ID.csv")

# Dictionaries
fuel_dict = {1: "Petrol", 2: "Diesel", 3: "LPG", 4: "LPG", 5: "Hybrid", 6: "Electric", 8: "LPG", 9: "LPG", 10: "Hybrid"}
body_dict = {3: "sedan", 2: "wagon", 5: "SUV", 4: "hatchback", 8: "minivan", 6: "coupe", 9: "pickup", 254: "van", 307: "liftback"}
gearbox_map = {1: "MT", 2: "AT"}
drive_map = {1: "AWD", 2: "FWD", 3: "RWD"}

prop["FuelType"] = prop["Fuel"].map(fuel_dict)
segment_list = sorted(rating["segment"].dropna().unique())

# Sidebar filters
st.sidebar.title("Your preferences")
min_price, max_price = st.sidebar.slider("Price ($)", 1000, 50000, (5000, 20000), step=500)
st.sidebar.markdown("---")

with st.sidebar.expander("Vehicle segment"):
    selected_segments = st.multiselect("Segment", options=segment_list, default=segment_list)

with st.sidebar.expander("Fuel type"):
    selected_fuels = st.multiselect("Fuel", list(set(fuel_dict.values())), default=list(set(fuel_dict.values())))
    selected_fuel_ids = [k for k, v in fuel_dict.items() if v in selected_fuels]

with st.sidebar.expander("Body type"):
    selected_bodies = st.multiselect("Body", list(body_dict.values()), default=list(body_dict.values()))
    selected_body_ids = [k for k, v in body_dict.items() if v in selected_bodies]

with st.sidebar.expander("Year"):
    year_min = st.number_input("From", min_value=1980, max_value=2025, value=2000)
    year_max = st.number_input("To", min_value=1980, max_value=2025, value=2024)

with st.sidebar.expander("Mileage (max, thousands km)"):
    odo_limit = st.number_input("Mileage", min_value=10, max_value=1000, value=300, step=10) * 1000

with st.sidebar.expander("Gearbox"):
    selected_gearbox = st.multiselect("Gearbox", gearbox_map.values(), default=gearbox_map.values())
    selected_gearbox_ids = [k for k, v in gearbox_map.items() if v in selected_gearbox]

with st.sidebar.expander("Drivetrain"):
    selected_drives = st.multiselect("Drive", drive_map.values(), default=drive_map.values())
    selected_drive_ids = [k for k, v in drive_map.items() if v in selected_drives]

if st.sidebar.button("🔄 Start over"):
    st.rerun()

# Filtering
filtered_prop = prop[
    (prop["Price"] >= min_price) &
    (prop["Price"] <= max_price) &
    (prop["Fuel"].isin(selected_fuel_ids)) &
    (prop["Body"].isin(selected_body_ids)) &
    (prop["Year"] >= year_min) &
    (prop["Year"] <= year_max) &
    (prop["Odo"] <= odo_limit) &
    (prop["Gear"].isin(selected_gearbox_ids)) &
    (prop["Drive"].isin(selected_drive_ids))
]

filtered_rating = rating[rating["segment"].isin(selected_segments)]
top_models = filtered_rating["model_r"].tolist()

model_counts = []
for model in top_models:
    count = filtered_prop[filtered_prop["Model"] == model].shape[0]
    if count > 0:
        model_counts.append({"Model": model, "Count": count})

result_df = pd.DataFrame(model_counts).sort_values(by="Count", ascending=False).head(15)

show_details = st.session_state.get("show_details", None)

st.subheader("Top picks for you:")

for i, row in result_df.iterrows():
    model = row["Model"]
    count = row["Count"]
    year_from = int(prop[prop["Model"] == model]["Year"].min())
    year_to = int(prop[prop["Model"] == model]["Year"].max())

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"**{model}** — {count} available cars")
    with col2:
        show_details = st.button("Details", key=f"btn_{i}")

    if show_details:
        prompt = (
            f"Explain whether {model} (production years: {year_from}–{year_to}) is a good used car choice in 2025. "
            f"Write for a buyer: describe its known features, strengths, weaknesses, and who it suits. "
            f"Avoid stating obvious facts (e.g., electric cars are not diesel)."
        )

        details = []
        if selected_fuel_ids and len(selected_fuel_ids) < len(fuel_dict):
            details.append("selected fuel: " + ", ".join(selected_fuels))
        if selected_gearbox_ids and len(selected_gearbox_ids) < len(gearbox_map):
            details.append("gearbox type: " + ", ".join(selected_gearbox))
        if selected_drive_ids and len(selected_drive_ids) < len(drive_map):
            details.append("drivetrain: " + ", ".join(selected_drives))
        if details:
            prompt += " Filters applied: " + "; ".join(details) + "."

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300
        )

        with st.container():
            st.markdown(f"**GPT on {model}:**")
            st.markdown(response.choices[0].message.content)
            st.markdown(f"[🔗 View listings for {model}](#)", unsafe_allow_html=True)

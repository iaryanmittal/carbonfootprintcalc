import streamlit as st
import sqlite3
from hashlib import sha256
from datetime import datetime
import pandas as pd

# Database setup
conn = sqlite3.connect('carbon_calculator.db')
cursor = conn.cursor()

# Create tables if not exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT ,
    date TEXT,
    distance REAL,
    electricity REAL,
    waste REAL,
    meals INTEGER,
    total_emissions REAL,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
''')
conn.commit()

# Helper function: hash password
def hash_password(password):
    return sha256(password.encode()).hexdigest()

# Define emission factors
EMISSION_FACTORS = {
    "India": {
        "Transportation": 0.14,
        "Electricity": 0.82,
        "Diet":1.25,
        "Waste": 0.1
    }
}

# App title and page config
st.set_page_config(layout="wide", page_title="Personal Carbon Calculator")

# Navigation and authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Login or Signup")
    auth_choice = st.radio("Choose:", ["Login", "Signup"])

    if auth_choice == "Signup":
        st.subheader("Create a new account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign Up"):
            hashed_pw = hash_password(password)
            try:
                cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_pw))
                conn.commit()
                st.success("Account created successfully! Please log in.")
                st.write(username)
            except sqlite3.IntegrityError:
                st.error("Username already exists.")

    if auth_choice == "Login":
        st.subheader("Login to your account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        st.write(username)
        if st.button("Login"):
            hashed_pw = hash_password(password)
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_pw))
            user = cursor.fetchone()
            if user:
                st.session_state.authenticated = True
                st.session_state.user_id = user[0]
                st.session_state.username = username
                st.success("Logged in successfully!")
            else:
                st.error("Invalid username or password.")
else:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to:", ["Home", "Add Data", "Reports (Daily)", "Reports (Weekly)", "Reports (Monthly)", "Reports (Yearly)"])

    if page == "Home":
        st.title("Welcome to the Carbon Footprint Calculator")
        st.write("Your personalized tool to track and reduce your carbon emissions.")
        st.warning('''Global CO2 emissions from fossil fuels are projected to reach a record high of 37.4 billion metric tons in 2024, representing a 0.8 percent increase from 2023.\n
         India’s CO2 emissions are expected to rise by 4.6% in 2024, accounting for 8% of the global total.
         
     Carbon emissions drive climate change, causing catastrophic natural disasters, rising sea levels,
      and extreme weather events. These trigger resource scarcity, mass migrations,
     and economic collapse, fueling conflicts over water, food, and habitable land.
     Such turmoil risks destabilizing nations, inciting wars, and leading to the loss of millions of lives. ''')

    elif page == "Add Data":
        st.title("Add Today's Data")
        country = "India"
        distance = st.slider("🚗 Daily commute distance (in km)", 0.0, 100.0, key="distance_input",step=0.5)
        electricity = st.slider("💡 Monthly electricity consumption (in kWh)", 0.0, 1000.0, key="electricity_input",step=0.5)
        waste = st.slider("🗑️ Waste generated today (in kg)", 0.0, 100.0, key="waste_input",step=0.5)
        meals = st.number_input("🍽️ Number of meals per day", 0, key="meals_input")

        if st.button("Submit Data"):
            # Normalize inputs
            distance_annual = distance * 365
            electricity_annual = electricity * 12
            waste_annual = waste * 52
            meals_annual = meals * 365

            # Calculate emissions
            transportation_emissions = EMISSION_FACTORS[country]["Transportation"] * distance_annual
            electricity_emissions = EMISSION_FACTORS[country]["Electricity"] * electricity_annual
            diet_emissions = EMISSION_FACTORS[country]["Diet"] * meals_annual
            waste_emissions = EMISSION_FACTORS[country]["Waste"] * waste_annual

            total_emissions = round(
                (transportation_emissions + electricity_emissions + diet_emissions + waste_emissions) / 1000, 2
            )

            # Save to database
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute('INSERT INTO data (user_id,username, date, distance, electricity, waste, meals, total_emissions) VALUES (?, ?, ?, ?, ?, ?, ?,?)',
                           (st.session_state.user_id,st.session_state.username, today, distance_annual, electricity_annual, waste_annual, meals_annual, total_emissions))
            conn.commit()
            st.success("Data added successfully!")

    elif page.startswith("Reports"):
        st.title(f"{page} Carbon Footprint")
        cursor.execute('SELECT * FROM data WHERE user_id = ? AND username = ?', (st.session_state.user_id,st.session_state.username))
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=["ID", "User ID","Username", "Date", "Distance", "Electricity", "Waste", "Meals", "Total Emissions"])
        df["Date"] = pd.to_datetime(df["Date"])
        st.write(df)

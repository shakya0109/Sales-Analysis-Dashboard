import streamlit as st
import pandas as pd
import requests
import io
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(page_title="Sales & Student Dashboard", layout="wide", page_icon="📊")

# We will store the authorized users here. 
# You can replace the dummy numbers with the actual numbers you provide.
AUTHORIZED_USERS = {
    "9039039555": "Sandeep Shakya",
    "8602268880": "Shah Nawaz Rayeen",
    "9870287695": "Mohammad Daniyal"
}

# Securely fetch the URL from Streamlit Secrets
SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"]

# --- AUTHENTICATION ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""

def authenticate(mobile_number):
    mobile_number = mobile_number.strip()
    if mobile_number in AUTHORIZED_USERS:
        st.session_state['authenticated'] = True
        st.session_state['user_name'] = AUTHORIZED_USERS[mobile_number]
        st.rerun()
    else:
        st.error("Unauthorized Mobile Number. Access Denied.")

if not st.session_state['authenticated']:
    st.title("🔒 Secure Access")
    st.write("Please enter your registered mobile number to access the dashboard.")
    
    # Text input for mobile number
    mobile_input = st.text_input("Mobile Number", placeholder="e.g. 9876543210")
    
    if st.button("Verify & Login"):
        if mobile_input:
            authenticate(mobile_input)
        else:
            st.warning("Please enter a mobile number.")
    
    st.stop() # Stop execution here if not authenticated. Everything below is hidden.

# --- DATA LOADING ---
@st.cache_data(ttl=3600) # Cache the data for 1 hour so it's fast, but still updates regularly
def load_data():
    try:
        r = requests.get(SHAREPOINT_URL)
        r.raise_for_status()
        
        # Read the specific sheet directly from the downloaded content
        df = pd.read_excel(io.BytesIO(r.content), sheet_name="Mastersheet MIS Apr23 till now")
        
        # Basic Data Cleaning
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Months'] = df['Months'].astype(str)
        df['Financial Year'] = df['Financial Year'].astype(str)
        df['Online/Offline'] = df['Online/Offline'].fillna('Unknown')
        
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

# --- DASHBOARD UI ---
st.title("📊 Sales & Student Dashboard")
st.write(f"Welcome, **{st.session_state['user_name']}**! Here is the latest data.")

with st.spinner("Fetching latest data from SharePoint..."):
    df = load_data()

if df.empty:
    st.warning("No data available to display.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")
selected_fy = st.sidebar.multiselect(
    "Select Financial Year", 
    options=df['Financial Year'].unique(), 
    default=df['Financial Year'].unique()
)
selected_mode = st.sidebar.multiselect(
    "Online/Offline", 
    options=df['Online/Offline'].unique(), 
    default=df['Online/Offline'].unique()
)

# Apply filters
filtered_df = df[
    (df['Financial Year'].isin(selected_fy)) & 
    (df['Online/Offline'].isin(selected_mode))
]

# --- KPIs ---
st.markdown("### Key Metrics")
col1, col2, col3 = st.columns(3)

total_revenue = filtered_df['Amount'].sum()
total_enrollments = len(filtered_df)
avg_ticket = total_revenue / total_enrollments if total_enrollments > 0 else 0

col1.metric("Total Revenue", f"₹ {total_revenue:,.0f}")
col2.metric("Total Enrollments", f"{total_enrollments:,}")
col3.metric("Avg Ticket Size", f"₹ {avg_ticket:,.0f}")

st.divider()

# --- CHARTS ---
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("#### Revenue by Month")
    monthly_rev = filtered_df.groupby('Months')['Amount'].sum().reset_index()
    fig1 = px.bar(monthly_rev, x='Months', y='Amount', text_auto='.2s', color_discrete_sequence=['#1f77b4'])
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    st.markdown("#### Revenue by Online/Offline")
    mode_rev = filtered_df.groupby('Online/Offline')['Amount'].sum().reset_index()
    fig2 = px.pie(mode_rev, names='Online/Offline', values='Amount', hole=0.4)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("#### Top 10 Cities by Revenue")
    city_rev = filtered_df.groupby('City Name')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(10)
    fig3 = px.bar(city_rev, x='Amount', y='City Name', orientation='h', color_discrete_sequence=['#2ca02c'])
    fig3.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig3, use_container_width=True)

with col_chart4:
    st.markdown("#### Top 10 Packages by Revenue")
    package_rev = filtered_df.groupby('Package Name')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(10)
    fig4 = px.bar(package_rev, x='Amount', y='Package Name', orientation='h', color_discrete_sequence=['#ff7f0e'])
    fig4.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig4, use_container_width=True)

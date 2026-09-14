import streamlit as st
import pandas as pd
import requests
import io
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Sales & Student Dashboard", layout="wide", page_icon="📈")

# --- HIDE STREAMLIT BRANDING (WHITE-LABEL) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* Adjust top padding to remove empty space */
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

AUTHORIZED_USERS = {
    "9039039555": "Sandeep Shakya",
    "8602268880": "Shah Nawaz Rayeen",
    "9870287695": "Mohammad Daniyal"
}

try:
    SHAREPOINT_URL = st.secrets["SHAREPOINT_URL"]
except:
    # Fallback just in case secrets fail, but it's hidden in UI anyway
    SHAREPOINT_URL = ""

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
    st.markdown("<h1 style='text-align: center;'>TopRankers Secure Portal</h1>", unsafe_allow_html=True)
    st.write("---")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("### Executive Dashboard Login")
        mobile_input = st.text_input("Enter Registered Mobile Number", type="password")
        if st.button("Access Dashboard", use_container_width=True):
            if mobile_input:
                authenticate(mobile_input)
            else:
                st.warning("Please enter a mobile number.")
    st.stop()

# --- DATA LOADING ---
@st.cache_data(ttl=3600)
def load_data():
    try:
        r = requests.get(SHAREPOINT_URL)
        r.raise_for_status()
        df = pd.read_excel(io.BytesIO(r.content), sheet_name="Mastersheet MIS Apr23 till now")
        
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Months'] = df['Months'].astype(str)
        df['Financial Year'] = df['Financial Year'].astype(str)
        df['Online/Offline'] = df['Online/Offline'].fillna('Unknown')
        df['City Name'] = df['City Name'].fillna('Unknown')
        df['Package Name'] = df['Package Name'].fillna('Unknown')
        
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

# --- DASHBOARD HEADER ---
st.markdown(f"<h2>📊 Executive Sales Dashboard <span style='font-size:16px; color:gray;'>| Welcome, {st.session_state['user_name']}</span></h2>", unsafe_allow_html=True)

with st.spinner("Synchronizing live data..."):
    df = load_data()

if df.empty:
    st.warning("No data available.")
    st.stop()

# --- SIDEBAR FILTERS (ADVANCED) ---
st.sidebar.markdown("### 🎛️ Dashboard Controls")
selected_fy = st.sidebar.multiselect("Financial Year", options=sorted(df['Financial Year'].unique()), default=sorted(df['Financial Year'].unique()))
selected_mode = st.sidebar.multiselect("Mode (Online/Offline)", options=df['Online/Offline'].unique(), default=df['Online/Offline'].unique())
selected_states = st.sidebar.multiselect("State", options=sorted([str(x) for x in df['STATE'].unique() if pd.notnull(x)]), default=[])

# Apply filters
mask = (df['Financial Year'].isin(selected_fy)) & (df['Online/Offline'].isin(selected_mode))
if selected_states:
    mask = mask & (df['STATE'].astype(str).isin(selected_states))
filtered_df = df[mask]

# --- ADVANCED KPIS ---
total_revenue = filtered_df['Amount'].sum()
total_enrollments = len(filtered_df)
avg_ticket = total_revenue / total_enrollments if total_enrollments > 0 else 0
max_month = filtered_df.groupby('Months')['Amount'].sum().idxmax() if not filtered_df.empty else "N/A"

st.markdown("""<style>
.kpi-box { padding: 20px; border-radius: 10px; background-color: #f8f9fa; border-left: 5px solid #0d6efd; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);}
</style>""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
col1.markdown(f"<div class='kpi-box'><h4>Total Revenue</h4><h2>₹ {total_revenue:,.0f}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='kpi-box' style='border-color: #198754;'><h4>Total Enrollments</h4><h2>{total_enrollments:,}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='kpi-box' style='border-color: #ffc107;'><h4>Avg. Ticket Size</h4><h2>₹ {avg_ticket:,.0f}</h2></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='kpi-box' style='border-color: #dc3545;'><h4>Top Performing Month</h4><h2>{max_month}</h2></div>", unsafe_allow_html=True)

st.write("---")

# --- TABS FOR DEEP ANALYSIS ---
tab1, tab2, tab3 = st.tabs(["📈 Trend & Overview", "🌍 Geographic Analysis", "📦 Product & Package Insights"])

with tab1:
    st.markdown("### Revenue Trends Over Time")
    monthly_rev = filtered_df.groupby('Months')['Amount'].sum().reset_index()
    # Sort logically if months have codes, else just plot
    fig_trend = px.line(monthly_rev, x='Months', y='Amount', markers=True, title="Monthly Revenue Velocity", line_shape='spline')
    fig_trend.update_traces(line_color='#0d6efd', line_width=3, marker_size=8)
    st.plotly_chart(fig_trend, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Revenue by Modality")
        fig_pie = px.pie(filtered_df, names='Online/Offline', values='Amount', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_b:
        st.markdown("### Top 5 Centers (POS)")
        pos_rev = filtered_df.groupby('POS')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(5)
        fig_pos = px.bar(pos_rev, x='Amount', y='POS', orientation='h', color='Amount', color_continuous_scale='Blues')
        fig_pos.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_pos, use_container_width=True)

with tab2:
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("### Revenue by State")
        state_rev = filtered_df.groupby('STATE')['Amount'].sum().reset_index().sort_values('Amount', ascending=False)
        fig_state = px.bar(state_rev.head(15), x='STATE', y='Amount', color='Amount', color_continuous_scale='Viridis')
        st.plotly_chart(fig_state, use_container_width=True)
    with col_d:
        st.markdown("### Revenue by City")
        city_rev = filtered_df.groupby('City Name')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(15)
        fig_city = px.bar(city_rev, x='Amount', y='City Name', orientation='h', color='Amount', color_continuous_scale='Magma')
        fig_city.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_city, use_container_width=True)

with tab3:
    st.markdown("### Package Performance Distribution")
    pkg_rev = filtered_df.groupby(['Package Name', 'Online/Offline'])['Amount'].sum().reset_index()
    fig_pkg = px.sunburst(pkg_rev, path=['Online/Offline', 'Package Name'], values='Amount', title="Revenue Breakdown by Package Type")
    st.plotly_chart(fig_pkg, use_container_width=True)
    
    st.markdown("### Top 15 Highest Grossing Packages")
    top_pkgs = filtered_df.groupby('Package Name')['Amount'].sum().reset_index().sort_values('Amount', ascending=False).head(15)
    fig_bar_pkg = px.bar(top_pkgs, x='Package Name', y='Amount', text_auto='.2s')
    st.plotly_chart(fig_bar_pkg, use_container_width=True)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from mftool import Mftool

st.set_page_config(page_title="Mutual Fund Comparison Portal", layout="wide")
mf = Mftool()

# Cache the list of scheme codes so the app loads instantly without refetching on every interaction
@st.cache_data
def get_all_schemes():
    return mf.get_scheme_codes()

scheme_dict = get_all_schemes()

st.title("Mutual Fund Comparative Analytics & Research Terminal")
st.write("Compare historical returns, maximum drawdowns, SIP, and Lumpsum performance.")

# Sidebar controls
st.sidebar.header("Fund Selector")

# Default selected fund codes if present in master list
default_codes = ["120503", "118778", "100033"]
valid_defaults = [c for c in default_codes if c in scheme_dict]

# Searchable Multi-Select Dropdown
selected_codes = st.sidebar.multiselect(
    "Search & Select Funds",
    options=list(scheme_dict.keys()),
    default=valid_defaults,
    format_func=lambda code: f"{scheme_dict.get(code, code)} ({code})"
)

st.sidebar.header("Simulation Inputs")
investment_amount = st.sidebar.number_input("Investment Amount (₹)", value=100000.0, step=10000.0)
sip_day = st.sidebar.slider("Monthly SIP Day", min_value=1, max_value=28, value=5)
lumpsum_date = st.sidebar.date_input("Lumpsum Investment Date", value=datetime(2020, 1, 1))

def calculate_xirr(dates, cashflows):
    """Approximate XIRR calculation using Newton-Raphson method."""
    try:
        dates = pd.to_datetime(dates)
        days = (dates - dates.min()).dt.days.values
        
        def npv(rate):
            if rate <= -1.0:
                return float('inf')
            return sum(cf / (1.0 + rate) ** (d / 365.0) for cf, d in zip(cashflows, days))
        
        def npv_prime(rate):
            if rate <= -1.0:
                return float('inf')
            return sum(- (d / 365.0) * cf / (1.0 + rate) ** (d / 365.0 + 1.0) for cf, d in zip(cashflows, days))
            
        rate = 0.10
        for _ in range(100):
            val = npv(rate)
            deriv = npv_prime(rate)
            if abs(val) < 1e-6:
                return rate
            if deriv == 0:
                break
            new_rate = rate - val / deriv
            if abs(new_rate - rate) < 1e-6:
                return new_rate
            rate = new_rate
        return rate
    except Exception:
        return 0.0

if st.sidebar.button("Run Simulation"):
    if not selected_codes:
        st.warning("Please select at least one mutual fund scheme from the drop-down.")
    else:
        comparison_data = []
        chart_data_list = []

        for code in selected_codes:
            data = mf.get_scheme_historical_nav(code)
            scheme_name = scheme_dict.get(code, f"Scheme {code}")
            nav_list = data.get('data', [])
            
            if nav_list:
                df = pd.DataFrame(nav_list)
                df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                df['nav'] = pd.to_numeric(df['nav'])
                df = df.sort_values('date').reset_index(drop=True)
                
                # 1. Max Drawdown
                df['peak'] = df['nav'].cummax()
                df['drawdown'] = (df['nav'] - df['peak']) / df['peak']
                max_drawdown = df['drawdown'].min() * 100
                
                inception_date = df.iloc[0]['date']
                latest_nav = df.iloc[-1]['nav']
                latest_date = df.iloc[-1]['date']
                
                # 2. Lumpsum Simulation
                lumpsum_dt = pd.to_datetime(lumpsum_date)
                df_lumpsum = df[df['date'] >= lumpsum_dt]
                
                if not df_lumpsum.empty:
                    ls_start_nav = df_lumpsum.iloc[0]['nav']
                    ls_start_date = df_lumpsum.iloc[0]['date']
                    ls_units = investment_amount / ls_start_nav
                    ls_current_val = ls_units * latest_nav
                    
                    ls_years = (latest_date - ls_start_date).days / 365.25
                    ls_cagr = ((latest_nav / ls_start_nav) ** (1 / ls_years) - 1) * 100 if ls_years > 0 else 0.0
                    ls_xirr = calculate_xirr([ls_start_date, latest_date], [-investment_amount, ls_current_val]) * 100
                else:
                    ls_current_val, ls_cagr, ls_xirr, ls_start_date = 0.0, 0.0, 0.0, lumpsum_date

                # 3. Monthly SIP Simulation
                sip_df = df[df['date'].dt.day == sip_day]
                if sip_df.empty:
                    sip_df = df
                    
                sip_dates, sip_cashflows = [], []
                total_sip_units = 0.0
                for _, row in sip_df.iterrows():
                    sip_dates.append(row['date'])
                    sip_cashflows.append(-investment_amount)
                    total_sip_units += investment_amount / row['nav']
                    
                sip_current_val = total_sip_units * latest_nav
                total_invested = investment_amount * len(sip_dates)
                
                if sip_dates:
                    sip_xirr = calculate_xirr(sip_dates + [latest_date], sip_cashflows + [sip_current_val]) * 100
                else:
                    sip_xirr = 0.0

                comparison_data.append({
                    "Scheme Code": code,
                    "Scheme Name": scheme_name,
                    "Max Drawdown (%)": f"{max_drawdown:.2f}%",
                    f"Lumpsum Value (from {ls_start_date.strftime('%Y-%m-%d')})": f"₹{ls_current_val:,.2f}",
                    "Lumpsum CAGR (%)": f"{ls_cagr:.2f}%",
                    "Lumpsum XIRR (%)": f"{ls_xirr:.2f}%",
                    f"SIP Total Invested ({len(sip_dates)} mos)": f"₹{total_invested:,.2f}",
                    "SIP Current Value": f"₹{sip_current_val:,.2f}",
                    "SIP XIRR (%)": f"{sip_xirr:.2f}%"
                })
                
                temp_df = df[['date', 'nav']].copy()
                temp_df['Scheme'] = scheme_name
                chart_data_list.append(temp_df)

        if comparison_data:
            st.subheader("Summary Metrics & Performance Comparison")
            summary_df = pd.DataFrame(comparison_data)
            st.dataframe(summary_df, use_container_width=True)
            
            if chart_data_list:
                st.subheader("Interactive Historical NAV Trend")
                combined_chart_df = pd.concat(chart_data_list)
                
                fig = px.line(
                    combined_chart_df, 
                    x='date', 
                    y='nav', 
                    color='Scheme',
                    labels={'date': 'Date', 'nav': 'NAV / Value', 'Scheme': 'Mutual Fund Scheme'},
                    hover_data={'date': '|%Y-%m-%d', 'nav': ':.2f'}
                )
                fig.update_layout(
                    hovermode='x unified',
                    xaxis_title="Year",
                    yaxis_title="NAV",
                    template="plotly_white",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Could not fetch data for the selected schemes.")
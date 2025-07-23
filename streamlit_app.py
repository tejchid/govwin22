import streamlit as st
import requests
import pandas as pd
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# secret values
CLIENT_ID = "QL6T5GNJLC1TGCJHTDJNJH4521LM1DFLG12390AULPNFO"
CLIENT_SECRET = "L43DCOP64E29M14ONB208UCA1BVGAESCA3INAP270AN5N"
USERNAME = "webservices@commscope.com"
PASSWORD = "APItool123456"
SCOPE = "read"

AUTH_URL = "https://services.govwin.com/neo-ws/oauth/token"
SEARCH_URL = "https://services.govwin.com/neo-ws/opportunities"

st.title("Deal Pilot - GovWin Opportunities Scoring Dashboard")

# sidepanel with ruckus dog
try:
    st.sidebar.image("ruckus_battle_card.png", use_container_width=True)
except:
    st.sidebar.markdown("🐶")
st.sidebar.markdown("<div style='text-align:center; font-size:2em;'><b>Deal Pilot</b></div>", unsafe_allow_html=True)

# User first enters keywords to search
user_input = st.text_input("Enter keywords (comma separated):", "switch, access point, wireless, wi-fi")
keywords = [kw.strip().lower() for kw in user_input.split(",") if kw.strip()]

if not keywords:
    st.warning("Please enter at least one keyword to search.")
    st.stop()

st.write(f"Searching for bids matching: {', '.join(keywords)}")

# Authenticate with GovWin API to get token
try:
    auth_payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "scope": SCOPE,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    # authentication api call to get access token
    auth_response = requests.post(AUTH_URL, data=auth_payload, headers=headers, verify=False)
    auth_response.raise_for_status()
    access_token = auth_response.json()["access_token"]
    st.success("Logged in successfully!")
except Exception as e:
    st.error(f"Authentication failed: {e}")
    st.stop()

# Search GovWin for open opportunities matching keywords
try:
    query_string = ",".join(keywords)
    search_headers = {"Authorization": f"Bearer {access_token}"}
    search_params = {
        "q": query_string,
        "max": 50,
        "offset": 0,
    }
    # search api call to fetch opps
    search_response = requests.get(SEARCH_URL, headers=search_headers, params=search_params, verify=False)
    search_response.raise_for_status()
    results = search_response.json()
    opportunities = results.get("opportunities", [])
    
    if not opportunities:
        st.warning("No opportunities found for your keywords.")
        st.stop()

    rows = []
    for opp in opportunities:
        title = opp.get("title", "")
        description = opp.get("description", "")
        smart_tags = " ".join([tag.get("name", "") for tag in opp.get("smartTagObject", [])])
        status = opp.get("status", "")
        agency = opp.get("agencyName", "")
        location = opp.get("placeOfPerformance", {}).get("location", "")
        date_posted = opp.get("publicationDate", "")
        response_date_raw = opp.get("responseDate", "")
        if isinstance(response_date_raw, dict) and "value" in response_date_raw:
            try:
                response_date = datetime.fromisoformat(response_date_raw["value"].split(".")[0]).strftime("%Y-%m-%d %H:%M")
            except Exception:
                response_date = str(response_date_raw["value"])
        else:
            try:
                response_date = datetime.fromisoformat(response_date_raw.split(".")[0]).strftime("%Y-%m-%d %H:%M")
            except Exception:
                response_date = str(response_date_raw)
        text_to_search = f"{title} {description} {smart_tags}".lower()
        score = sum(kw.lower() in text_to_search for kw in keywords)
        if status.upper() != "AWARDED":
            row = {
                "Title": title,
                "Description": description,
                "Tags": smart_tags,
                "Status": status,
                "Score": score,
                "Response Date": response_date,
                "Agency": agency,
                "Location": location,
                "Date Posted": date_posted
            }
            rows.append(row)
    if not rows:
        st.warning("⚠️ No non-awarded opportunities found matching your keywords.")
        st.stop()

    st.subheader(f"Keyword-Matched Non-Awarded Opportunities ({len(rows)})")

    cols = ["Title", "Description", "Tags", "Status", "Score", "Response Date", "Agency", "Location", "Date Posted"]
    df = pd.DataFrame(rows)[cols]

    # if score > 0
    def highlight_score(val):
        color = 'lime' if val > 0 else ''
        return f'color: {color}'

    st.dataframe(df.style.applymap(highlight_score, subset=['Score']))

except Exception as e:
    st.error(f"Oops, something went wrong fetching data: {e}")
    st.stop()

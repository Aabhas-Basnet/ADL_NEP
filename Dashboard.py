import streamlit as st
import pandas as pd
import os, re, requests
from datetime import datetime, timedelta

# --- 1. UI CONFIG & STYLE (Your Original Design) ---
st.set_page_config(page_title="Adelaide Nepal", page_icon="ADL_NPL.jpg")

st.markdown("""
    <style>
    .stApp { background-color: #f2f4f7; }
    .post-card { 
        background: white; padding: 15px; border-radius: 8px; 
        border: 1px solid #ddd; margin-bottom: 10px; color: #1c1e21;
    }
    .badge { background: #e7f3ff; color: #1877f2; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: bold; }
    .contact { background: #f8f9fa; padding: 8px; border-radius: 5px; margin-top: 10px; font-size: 0.85rem; border: 1px solid #eee; }
    .btn { display: inline-block; background: #1877f2; color: white !important; padding: 6px 12px; border-radius: 5px; text-decoration: none; font-size: 0.8rem; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

MASTER_FILE = "master.csv"
FB_DATA_FILE = "fb_data.csv"

# Access Secrets
PAGE_ID = st.secrets.get("FB_PAGE_ID", "YOUR_PAGE_ID")
ACCESS_TOKEN = st.secrets.get("FB_ACCESS_TOKEN", "YOUR_TOKEN")

# --- 2. LOGIC: FETCH & EXTRACTION ---

def get_meta(text):
    t = str(text).lower()
    if any(x in t for x in ["room", "rent", "kotha", "sharing", "flat"]): cat = "Accommodation"
    elif any(x in t for x in ["job", "hiring", "kaam", "work", "shift", "cleaning"]): cat = "Jobs"
    elif any(x in t for x in ["sale", "price", "selling", "available", "iphone", "car"]): cat = "Sales"
    else: cat = "General"
    
    loc = "South" if "marion" in t else "North" if "salisbury" in t else "Adelaide"
    ph = re.findall(r'(\d{4}\s?\d{3}\s?\d{3}|04\d{8})', str(text))
    em = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', str(text))
    return cat, loc, ph[0] if ph else "", em[0] if em else ""

def fetch_facebook_data():
    """Fetches the last 14 days of data from FB API."""
    since_date = int((datetime.now() - timedelta(days=14)).timestamp())
    all_posts = []
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    params = {
        'access_token': ACCESS_TOKEN,
        'since': since_date,
        'limit': 50, 
        'fields': 'id,message,created_time,permalink_url'
    }
    
    try:
        while url:
            response = requests.get(url, params=params)
            response.raise_for_status()
            res_json = response.json()
            data = res_json.get('data', [])
            all_posts.extend(data)
            url = res_json.get('paging', {}).get('next')
            params = {} 
            if not data: break

        df = pd.DataFrame(all_posts)
        if not df.empty:
            df = df.rename(columns={'id': 'Post ID', 'message': 'Description', 'created_time': 'Publish time', 'permalink_url': 'Permalink'})
            df['Publish time'] = pd.to_datetime(df['Publish time']).dt.strftime('%Y-%m-%d %H:%M')
            df.to_csv(FB_DATA_FILE, index=False)
            return True
    except Exception as e:
        st.error(f"Fetch Error: {e}")
    return False

@st.cache_data
def load_data():
    # If file doesn't exist, try to fetch it first
    if not os.path.exists(FB_DATA_FILE):
        fetch_facebook_data()
        
    if os.path.exists(FB_DATA_FILE):
        raw = pd.read_csv(FB_DATA_FILE)
        data = []
        for _, r in raw.iterrows():
            txt = str(r.get('Description', ''))
            if len(txt) < 10: continue
            
            c, l, p, e = get_meta(txt)
            time_val = r.get('Publish time')
            
            data.append({
                "Time": time_val,
                "Text": txt, 
                "Cat": c, 
                "Loc": l, 
                "Ph": p, 
                "Em": e, 
                "Url": str(r.get('Permalink', '#'))
            })
        df = pd.DataFrame(data)
        df.to_csv(MASTER_FILE, index=False)
        return df
    return pd.DataFrame(columns=["Time", "Text", "Cat", "Loc", "Ph", "Em", "Url"])

# --- 3. UI (Your Original Design) ---

col_l, col_r = st.columns([1, 6])
if os.path.exists("ADL_NPL.jpg"):
    col_l.image("ADL_NPL.jpg", width=70)
col_r.title("Adelaide Nepal Community")

# Refresh Button
if st.button("🔄 Update Feed from Facebook"):
    with st.spinner("Fetching latest updates..."):
        if fetch_facebook_data():
            st.cache_data.clear()
            st.rerun()

df = load_data()
search = st.text_input("🔍 Search feed...")

c1, c2 = st.columns(2)
f_cat = c1.selectbox("Category", ["All"] + list(df['Cat'].unique()))
f_loc = c2.selectbox("Location", ["All"] + list(df['Loc'].unique()))

v = df.copy()
if f_cat != "All": v = v[v['Cat'] == f_cat]
if f_loc != "All": v = v[v['Loc'] == f_loc]
if search: v = v[v['Text'].str.contains(search, case=False)]

st.divider()

for _, r in v.head(100).iterrows():
    time_val = r.get('Time')
    contact = f"<div class='contact'><b>📞</b> {r['Ph']} <br> <b>📧</b> {r['Em']}</div>" if r['Ph'] or r['Em'] else ""
    btn = f"<a href='{r['Url']}' target='_blank' class='btn'>View Original</a>" if r['Url'] != "#" else ""
    
    st.markdown(f"""
    <div class="post-card">
        <div style="display:flex; justify-content: space-between; align-items: center;">
            <div>
                <span class="badge">{r['Cat']}</span>
                <span style="font-size:0.75rem; color:grey; margin-left:10px;">📍 {r['Loc']}</span>
            </div>
            <span style="font-size:0.65rem; color:#999;">{time_val}</span>
        </div>
        <div style="margin-top:10px; line-height:1.5;">{r['Text']}</div>
        {contact}
        {btn}
    </div>
    """, unsafe_allow_html=True)

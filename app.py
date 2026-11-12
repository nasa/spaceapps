import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Silent Guardians - NASA Space Apps 2026",
    page_icon="🚀",
    layout="wide"
)

# --- CUSTOM CSS THEMING ---
st.markdown("""
<style>
    .main {
        background-color: #0B0C10;
        color: #C5C6C7;
    }
    h1, h2, h3 {
        color: #66FCF1;
    }
    .stMetric {
        background-color: #1F2833;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #45A29E;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVIGATION SIDEBAR ---
st.sidebar.title("🚀 Mission Control")
page = st.sidebar.radio("Select Sector:", [
    "🏠 Home Hub", 
    "🌙 Chapter 1: The Silver Moon", 
    "🔴 Chapter 2: Mars", 
    "🌌 Chapter 3: Interstellar Space", 
    "🧠 Quiz & Q&A"
])

# ==========================================
# 🏠 HOME HUB
# ==========================================
if page == "🏠 Home Hub":
    st.title("🌌 Silent Guardians: Forgotten Pioneers of Space")
    st.markdown("### *Abandoned, but never forgotten.*")
    
    st.write("""
    Humanity has always gazed upward, striving to step beyond our home planet to gain knowledge 
    and unravel the incredible mysteries of the universe. Out of thousands of stories written in the stars, 
    three major chapters capture our greatest leaps into the silent deep.
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🌙 **Chapter 1: Moon**\n\nApollo 11 & 15 hardware measuring lunar drift and ancient crusts.")
    with col2:
        st.warning("🔴 **Chapter 2: Mars**\n\nOpportunity & InSight rovers uncovering water and listening to planet cores.")
    with col3:
        st.success("🌌 **Chapter 3: Interstellar**\n\nVoyager 1 & 2 carrying humanity's Golden Record beyond the Sun.")
        
    st.divider()
    st.caption("Built for NASA Space Apps Challenge 2026 • Target: School-Age Space Enthusiasts")

# ==========================================
# 🌙 CHAPTER 1: THE MOON
# ==========================================
elif page == "🌙 Chapter 1: The Silver Moon":
    st.title("🌙 Chapter 1: The Silver Moon")
    
    tab1, tab2 = st.tabs(["Apollo 11 Retroreflector", "Apollo 15 Lunar Rover"])
    
    with tab1:
        st.subheader("Apollo 11: The Eternal Mirror (1969)")
        st.info("🎭 *'No batteries, no Wi-Fi, just a high-tech mirror bouncing laser beams across the dark!'*")
        st.write("""
        When Neil Armstrong and Buzz Aldrin walked on the *Sea of Tranquility*, they left behind a passive glass-prism panel. 
        It requires zero electricity! Every night, observatories fire green laser pulses at it to measure Earth-Moon distance.
        """)
        
        st.metric(label="Laser Round-Trip Time", value="2.56 seconds")
        st.metric(label="Moon Recession Rate", value="3.82 cm / year")
        
        if st.button("🚀 Test Laser Ping Simulation"):
            st.success("Laser hit reflector! Calculated distance: **384,400 km**.")

    with tab2:
        st.subheader("Apollo 15: Expanding the Horizon (1971)")
        st.info("🎭 *'Space's first-ever electric dune buggy—no driver's license required!'*")
        st.write("""
        Parked near Hadley Rille and the Apennine Mountains, the Lunar Roving Vehicle (LRV) allowed astronauts 
        to drive over 27 km across rough terrain, retrieving the legendary 4.1-billion-year-old **Genesis Rock**.
        """)
        st.metric(label="Max Speed", value="13 km/h (8 mph)")

# ==========================================
# 🔴 CHAPTER 2: MARS
# ==========================================
elif page == "🔴 Chapter 2: Mars":
    st.title("🔴 Chapter 2: Mars — The Red Planet")
    
    tab1, tab2 = st.tabs(["Opportunity Rover ('Oppy')", "InSight Lander"])
    
    with tab1:
        st.subheader("Opportunity: The Unstoppable Pioneer (2004)")
        st.info("🎭 *'Built to last 3 months, but stayed so long it ran the longest marathon on Mars!'*")
        st.write("""
        Designed for a 90-day sprint, Oppy rolled across 45.16 km of Martian dust for **14 years**. 
        It discovered iron 'blueberries' proving liquid water once flowed across ancient Mars.
        """)
        st.warning("💬 **Final Message:** *'My battery is low and it's getting dark.'*")
        st.progress(0.95, text="Total Distance: 45.16 km")

    with tab2:
        st.subheader("InSight Lander: The Planetary Doctor (2018)")
        st.info("🎭 *'The ultimate introvert: it didn't drive an inch, but listened to the whole planet!'*")
        st.write("""
        Staying completely still at Elysium Planitia, InSight's seismometer listened to the deep interior of Mars, 
        recording over 1,300 marsquakes and proving Mars has a liquid iron core.
        """)
        st.metric(label="Marsquakes Detected", value="1,300+")

# ==========================================
# 🌌 CHAPTER 3: INTERSTELLAR SPACE
# ==========================================
elif page == "🌌 Chapter 3: Interstellar Space":
    st.title("🌌 Chapter 3: Interstellar Space")
    st.subheader("Voyager 1 & 2: The Interstellar Messengers (1977)")
    st.info("🎭 *'Earth's ultimate cosmic hitchhikers, carrying whale songs and rock music into the dark!'*")
    
    st.write("""
    Launched in 1977, twin Voyager probes crossed the heliopause into interstellar space carrying the **Golden Record**. 
    They are humanity's farthest ambassadors.
    """)
    
    st.markdown("### 🛰️ Live Telemetry Milestone")
    st.metric(label="Voyager 1 Distance (Nov 2026)", value=">1 Light-Day (>25.9 Billion km)")
    st.write("A radio signal sent from NASA now takes a full **24-hour wait** just to reach the probe!")

# ==========================================
# 🧠 QUIZ & Q&A
# ==========================================
elif page == "🧠 Quiz & Q&A":
    st.title("🧠 Space Hardware Mastery Quiz & Q&A")
    
    st.subheader("Interactive Knowledge Check")
    q1 = st.radio("1. How fast is the Moon drifting away from Earth?", ["A) 1.2 cm/year", "B) 3.82 cm/year", "C) 10.5 cm/year"])
    q2 = st.radio("2. Which rover said: 'My battery is low and it's getting dark'?", ["A) Curiosity", "B) Opportunity", "C) Perseverance"])
    
    if st.button("Submit Answers"):
        score = 0
        if "3.82" in q1: score += 1
        if "Opportunity" in q2: score += 1
        st.success(f"You scored {score} / 2! Great job exploring the silent guardians!")
        
    st.divider()
    st.subheader("Frequently Asked Questions (Q&A)")
    with st.expander("Why don't the Moon artifacts rust or decay?"):
        st.write("Because the Moon has no atmosphere or liquid water, protecting exposed metals from oxidation!")
    with st.expander("How long does radio communication take with Voyager 1?"):
        st.write("Over 24 hours one-way, because it is more than 25.9 billion kilometers away in interstellar space.")

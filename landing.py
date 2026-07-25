import streamlit as st

st.set_page_config(
    page_title="Home Appliance AI",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>

#MainMenu{visibility:hidden;}
header{visibility:hidden;}
footer{visibility:hidden;}

.block-container{
    padding-top:20px;
    padding-left:60px;
    padding-right:60px;
}

[data-testid="stAppViewContainer"]{
    background:#f5f7fb;
}

/* Navbar */

.navbar{
    background:white;
    padding:18px 30px;
    border-radius:15px;
    box-shadow:0 5px 15px rgba(0,0,0,.08);
}

/* Hero */

.hero{

background:linear-gradient(135deg,#155EEF,#3B82F6);

padding:40px;

border-radius:22px;

color:white;

margin-top:20px;

}

.hero h1{

font-size:44px;

font-weight:800;

margin-bottom:10px;

}

.hero p{

font-size:18px;

color:#eef4ff;

}

.bigbutton button{

height:52px;

border-radius:12px;

font-size:17px;

font-weight:700;

}

</style>

""",unsafe_allow_html=True)

# ---------------- NAVBAR ----------------

title,wp,ge=st.columns([6,1,1])

with title:

    st.markdown(
        '<div class="navbar"><span style="font-size:30px;font-weight:800;color:#155EEF;">🏠 Home Appliance AI Support Assistant</span></div>',
        unsafe_allow_html=True
    )

with wp:

    st.image("assets/Whirlpool.jpg",width=130)

with ge:

    st.image("assets/GE.png",width=95)

# ---------------- HERO ----------------

left,right=st.columns([2,1])

with left:

    st.markdown("""

<div class="hero">

<h1>

AI-powered Support

for Home Appliances

</h1>

<p>

Reliable answers from official Whirlpool and

GE documentation using

Retrieval-Augmented Generation (RAG).

</p>

</div>

""",unsafe_allow_html=True)

    st.write("")

    c1,c2,c3=st.columns([1,1,3])

    with c1:

        st.markdown('<div class="bigbutton">',unsafe_allow_html=True)

        st.button("🚀 Start Chat")

        st.markdown("</div>",unsafe_allow_html=True)

    with c2:

        st.markdown('<div class="bigbutton">',unsafe_allow_html=True)

        st.button("📖 Learn More")

        st.markdown("</div>",unsafe_allow_html=True)

with right:

    st.image("assets/Whirlpool.jpg",width=260)

    st.write("")

    st.image("assets/GE.png",width=180)
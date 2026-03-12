"""
ReuBoost - Application d'animation de réunions interactives
==============================================================
Une application Streamlit complète pour animer des réunions avec :
- Sondages Express
- Météo du Jour (Moodboard avec Heatmap)
- Diagramme en Araignée (Radar Chart)
- Nuage de Mots (Word Cloud)
"""

import streamlit as st
import plotly.graph_objects as go
import qrcode
import json
import os
import random
import io
import base64
import time
from datetime import datetime
from collections import Counter
from PIL import Image, ImageDraw
import numpy as np
import io
import json
import zipfile
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from streamlit_image_coordinates import streamlit_image_coordinates
from streamlit_autorefresh import st_autorefresh

# =============================================================================
# CONFIGURATION & STYLING
# =============================================================================

APP_TITLE = "ReuBoost"
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")

GOOGLE_COLORS = {
    "blue": "#4285F4",
    "red": "#EA4335",
    "yellow": "#FBBC05",
    "green": "#34A853",
    "grey_bg": "#F8F9FA",
    "grey_text": "#5F6368",
    "white": "#FFFFFF",
    "dark": "#202124",
    "light_blue": "#E8F0FE",
    "light_green": "#E6F4EA",
    "light_red": "#FCE8E6",
    "light_yellow": "#FEF7E0",
}

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
def inject_css():
    """Injecte un CSS Material Design renforcé pour forcer le mode clair."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Google+Sans:wght@400;500;700&display=swap');

        /* 1. FORCE LE MODE CLAIR AU NIVEAU DU NAVIGATEUR */
        :root {
            color-scheme: light !important;
        }

        /* 2. BASE DE L'APPLICATION */
        .stApp {
            background-color: #F8F9FA !important;
            color: #202124 !important;
        }

        /* 3. FORCE LA COULEUR DES TEXTES STANDARDS */
        .stMarkdown, p, span, label, li, h1, h2, h3, h4, h5, h6 {
            color: #202124 !important;
            font-family: 'Roboto', sans-serif !important;
        }

        /* 4. CORRECTION DES ZONES D'INPUT (POUR ÉVITER LE NOIR) */
        input, textarea, .stSelectbox div[data-baseweb="select"] {
            background-color: #FFFFFF !important;
            color: #202124 !important;
            border-radius: 8px !important;
        }

        /* Cible spécifiquement les fonds des champs de texte Streamlit */
        div[data-testid="stTextInput"] input, 
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input {
            background-color: #FFFFFF !important;
            color: #202124 !important;
            border: 1px solid #DADCE0 !important;
        }

        /* Correction pour les menus déroulants (selectbox) */
        div[data-baseweb="select"] > div {
            background-color: #FFFFFF !important;
            color: #202124 !important;
        }

        /* 5. BOUTONS MATERIAL DESIGN */
        .stButton > button {
            font-family: 'Google Sans', sans-serif !important;
            border-radius: 24px !important;
            background-color: #4285F4 !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
        }
        
        .stButton > button:hover {
            background-color: #3367D6 !important;
            box-shadow: 0 4px 8px rgba(66,133,244,0.3) !important;
        }

        /* 6. CARTES ET CONTENEURS */
        .material-card {
            background: white !important;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            border: 1px solid #E8EAED !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        }

        /* 7. MASQUAGE DES ÉLÉMENTS STREAMLIT */
        #MainMenu, footer, header { visibility: hidden !important; }
        
        /* Ajustement de la largeur */
        .block-container {
            max-width: 1100px !important;
            padding-top: 2rem !important;
        }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# SESSION / DATA MANAGEMENT
# =============================================================================

def init_session_db():
    """Initialize the sessions database in session_state."""
    if "sessions" not in st.session_state:
        st.session_state["sessions"] = load_sessions()
    if "current_role" not in st.session_state:
        st.session_state["current_role"] = None
    if "current_session_code" not in st.session_state:
        st.session_state["current_session_code"] = None
    if "participant_name" not in st.session_state:
        st.session_state["participant_name"] = None


def save_sessions():
    """Persist sessions to a local JSON file."""
    try:
        sessions_data = {}
        for code, session in st.session_state["sessions"].items():
            s = dict(session)
            # Convert sets to lists for JSON serialization
            s["participants"] = list(s.get("participants", []))
            # Handle image data in activities
            activities = []
            for act in s.get("activities", []):
                a = dict(act)
                if "image_data" in a and a["image_data"] is not None:
                    # Store as base64
                    if isinstance(a["image_data"], bytes):
                        a["image_data"] = base64.b64encode(a["image_data"]).decode("utf-8")
                activities.append(a)
            s["activities"] = activities
            sessions_data[code] = s
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        st.error(f"Erreur de sauvegarde: {e}")


def load_sessions():
    """Load sessions from the local JSON file."""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for code, session in data.items():
                session["participants"] = set(session.get("participants", []))
                for act in session.get("activities", []):
                    if "image_data" in act and act["image_data"] is not None:
                        if isinstance(act["image_data"], str):
                            act["image_data"] = base64.b64decode(act["image_data"])
            return data
        except Exception:
            return {}
    return {}


def create_session(session_name):
    """Create a new session with a random 4-digit code."""
    while True:
        code = str(random.randint(1000, 9999))
        if code not in st.session_state["sessions"]:
            break
    st.session_state["sessions"][code] = {
        "name": session_name,
        "code": code,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "participants": set(),
        "activities": [],
        "admin_name": session_name,
    }
    save_sessions()
    return code


def join_session(code, participant_name):
    """Join an existing session as a participant."""
    if code in st.session_state["sessions"]:
        session = st.session_state["sessions"][code]
        if session["status"] == "active":
            session["participants"].add(participant_name)
            save_sessions()
            return True
    return False


def get_session(code):
    """Get a session by its code."""
    return st.session_state["sessions"].get(code)


def generate_qr_code(session_code):
    """Generate a QR code image for the session URL."""
    # Build the participant URL
    base_url = "http://localhost:8501"
    url = f"{base_url}/?role=participant&code={session_code}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#4285F4", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# =============================================================================
# ACTIVITY: SONDAGES EXPRESS (POLLS)
# =============================================================================

def admin_create_poll(session_code):
    """Admin form to create a new poll."""
    if f"poll_count_{session_code}" not in st.session_state:
        st.session_state[f"poll_count_{session_code}"] = 2
        
    st.markdown("#### 📊 Créer un Sondage Express")
    question = st.text_input("Question", placeholder="Ex: Quel est votre outil préféré ?", key=f"poll_q_{session_code}")
    cols = st.columns(2)
    options = []
    for i in range(st.session_state[f"poll_count_{session_code}"]):
        with cols[i % 2]:
            opt = st.text_input(f"Option {i+1}", key=f"poll_opt_{i}_{session_code}", placeholder=f"Option {i+1}")
            if opt:
                options.append(opt)
                
    col_add, col_sub = st.columns(2)
    with col_add:
        if st.button("➕ Ajouter une option", key=f"add_poll_opt_{session_code}", use_container_width=True):
            st.session_state[f"poll_count_{session_code}"] += 1
            st.rerun()
    with col_sub:
        if st.button("✅ Créer le sondage", type="primary", key=f"submit_poll_{session_code}", use_container_width=True):
            if question and len(options) >= 2:
                session = get_session(session_code)
                activity = {
                    "type": "poll",
                    "id": f"poll_{len(session['activities'])}_{int(time.time())}",
                    "question": question,
                    "options": options,
                    "votes": {opt: 0 for opt in options},
                    "voters": [],
                    "voter_choices": {},
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }
                session["activities"].append(activity)
                save_sessions()
                
                # Clear inputs to reset form behavior manually
                st.session_state[f"poll_q_{session_code}"] = ""
                for i in range(st.session_state[f"poll_count_{session_code}"]):
                    if f"poll_opt_{i}_{session_code}" in st.session_state:
                         st.session_state[f"poll_opt_{i}_{session_code}"] = ""
                st.session_state[f"poll_count_{session_code}"] = 2
                
                st.toast("✅ Sondage créé avec succès !")
                st.rerun()
            else:
                st.warning("Veuillez saisir une question et au moins 2 options.")


def admin_view_poll_results(activity):
    """Display poll results as a horizontal bar chart."""
    votes = activity["votes"]
    total = sum(votes.values())

    if total == 0:
        st.info("🕐 En attente des votes des participants...")
        return

    # Sort by votes
    sorted_options = sorted(votes.items(), key=lambda x: x[1], reverse=True)
    labels = [item[0] for item in sorted_options]
    values = [item[1] for item in sorted_options]
    colors = [GOOGLE_COLORS["blue"], GOOGLE_COLORS["red"],
              GOOGLE_COLORS["yellow"], GOOGLE_COLORS["green"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels,
        x=values,
        orientation='h',
        marker_color=colors[:len(labels)],
        text=[f"{v} ({v/total*100:.0f}%)" for v in values],
        textposition='auto',
        textfont=dict(family="Roboto", size=14, color="white"),
    ))
    fig.update_layout(
        title=None,
        xaxis_title="Nombre de votes",
        yaxis_title=None,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Roboto", size=13),
        height=max(200, len(labels) * 60 + 80),
        margin=dict(l=10, r=20, t=10, b=40),
        xaxis=dict(gridcolor="#E8EAED", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<span class="badge badge-count">📊 {total} vote{"s" if total > 1 else ""}</span>',
                unsafe_allow_html=True)


def participant_vote_poll(activity, participant_name):
    """Participant form to vote on a poll."""
    if participant_name in activity.get("voters", []):
        my_choice = activity.get("voter_choices", {}).get(participant_name, "Inconnu")
        st.markdown(f"""
        <div class="confirmation-box">
            <h3>✅ Vote enregistré !</h3>
            <p>Votre choix : <strong>{my_choice}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        return

    st.subheader(activity['question'])
    choice = st.radio(
        "Choisissez votre réponse :",
        activity["options"],
        key=f"vote_{activity['id']}_{participant_name}",
        label_visibility="collapsed",
    )

    if st.button("✅ Voter", key=f"btn_vote_{activity['id']}_{participant_name}",
                 use_container_width=True):
        activity["votes"][choice] = activity["votes"].get(choice, 0) + 1
        activity.setdefault("voters", []).append(participant_name)
        activity.setdefault("voter_choices", {})[participant_name] = choice
        save_sessions()
        st.rerun()


# =============================================================================
# ACTIVITY: MÉTÉO DU JOUR (MOODBOARD / HEATMAP)
# =============================================================================

def admin_create_moodboard(session_code):
    """Admin form to create a moodboard activity."""
    st.markdown("#### 🌤️ Créer un Placement sur image")

    with st.form(f"moodboard_form_{session_code}", clear_on_submit=True, border=False):
            title = st.text_input("Titre", placeholder="Ex: Comment vous sentez-vous aujourd'hui ?")
            uploaded_file = st.file_uploader("Importer une image de fond", type=["png", "jpg", "jpeg"],
                                             key=f"moodboard_upload_{session_code}")

            submitted = st.form_submit_button("✅ Créer la météo", use_container_width=True)
            if submitted and title and uploaded_file:
                image_data = uploaded_file.read()
                session = get_session(session_code)
                activity = {
                    "type": "moodboard",
                    "id": f"moodboard_{len(session['activities'])}_{int(time.time())}",
                    "title": title,
                    "image_data": image_data,
                    "clicks": [],  # List of {"x": float, "y": float, "participant": str}
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }
                session["activities"].append(activity)
                save_sessions()
                st.success("Météo du jour créée avec succès !")
                st.rerun()
            elif submitted:
                st.warning("Veuillez saisir un titre et importer une image.")


def admin_view_heatmap(activity):
    """Display the moodboard image with a heatmap overlay."""
    if not activity.get("image_data"):
        st.warning("Aucune image disponible.")
        return

    # Load image
    img = Image.open(io.BytesIO(activity["image_data"]))
    img_array = np.array(img)
    h, w = img_array.shape[:2]

    clicks = activity.get("clicks", [])

    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.imshow(img_array)

    if clicks:
        # Create heatmap
        heatmap = np.zeros((h, w), dtype=np.float64)
        for click in clicks:
            cx = int(click["x"] * w)
            cy = int(click["y"] * h)
            # Gaussian blob
            y_coords, x_coords = np.ogrid[max(0,cy-40):min(h,cy+40), max(0,cx-40):min(w,cx+40)]
            y_local = y_coords - cy
            x_local = x_coords - cx
            gaussian = np.exp(-(x_local**2 + y_local**2) / (2 * 20**2))
            heatmap[max(0,cy-40):min(h,cy+40), max(0,cx-40):min(w,cx+40)] += gaussian

        # Overlay heatmap
        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()
        ax.imshow(heatmap, cmap='YlOrRd', alpha=0.5, extent=[0, w, h, 0])

        # Draw individual markers
        for click in clicks:
            cx = click["x"] * w
            cy = click["y"] * h
            ax.plot(cx, cy, 'o', markersize=8, markerfacecolor='#EA4335',
                    markeredgecolor='white', markeredgewidth=2)

    ax.set_axis_off()
    plt.tight_layout(pad=0)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    st.image(buf, use_container_width=True)
    st.markdown(f'<span class="badge badge-count">📍 {len(clicks)} marqueur{"s" if len(clicks) > 1 else ""}</span>',
                unsafe_allow_html=True)


def participant_click_moodboard(activity, participant_name):
    """Participant interface to click on the moodboard image."""
    already_clicked = any(c["participant"] == participant_name for c in activity.get("clicks", []))

    if already_clicked:
        st.markdown("""
        <div class="confirmation-box">
            <h3>✅ Position enregistrée !</h3>
            <p>Votre marqueur a été placé.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    if not activity.get("image_data"):
        st.warning("Aucune image disponible.")
        return

    img = Image.open(io.BytesIO(activity["image_data"]))
    img_w, img_h = img.size

    st.subheader(activity['title'])
    st.markdown("*📍 Cliquez sur l'image pour placer votre marqueur, puis validez.*")
    
    # Check if participant already clicked
    my_click = next((c for c in activity.get("clicks", []) if c["participant"] == participant_name), None)

    if my_click:
        st.success("✅ Votre position a bien été enregistrée !")
        # Draw all clicks on image for the participant
        drawn_img = img.copy()
        draw = ImageDraw.Draw(drawn_img)
        r = 15
        cx, cy = my_click["x"] * img_w, my_click["y"] * img_h
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=GOOGLE_COLORS["blue"], outline="white", width=2)
        st.image(drawn_img, use_container_width=True)
        return

    # Draw current selection if present
    if f"temp_x_{activity['id']}" in st.session_state:
        temp_x, temp_y = st.session_state[f"temp_x_{activity['id']}"], st.session_state[f"temp_y_{activity['id']}"]
        preview_img = img.copy()
        draw = ImageDraw.Draw(preview_img)
        cx, cy = temp_x * img_w, temp_y * img_h
        draw.ellipse((cx-10, cy-10, cx+10, cy+10), fill=GOOGLE_COLORS["red"], outline="white", width=2)
    else:
        preview_img = img

    value = streamlit_image_coordinates(
        preview_img,
        key=f"img_coords_{activity['id']}_{participant_name}",
    )
    
    if value is not None:
        x_pct = value["x"] / img_w
        y_pct = value["y"] / img_h
        
        if st.session_state.get(f"temp_x_{activity['id']}") != x_pct or st.session_state.get(f"temp_y_{activity['id']}") != y_pct:
            st.session_state[f"temp_x_{activity['id']}"] = x_pct
            st.session_state[f"temp_y_{activity['id']}"] = y_pct
            st.rerun()
        
    if f"temp_x_{activity['id']}" in st.session_state:
        st.info("📍 Position sélectionnée visible en rouge. Cliquez sur Valider pour envoyer définitivement.")
        if st.button("✅ Valider ma position", use_container_width=True):
            activity.setdefault("clicks", []).append({
                "x": st.session_state[f"temp_x_{activity['id']}"],
                "y": st.session_state[f"temp_y_{activity['id']}"],
                "participant": participant_name,
            })
            save_sessions()
            st.rerun()


# =============================================================================
# ACTIVITY: DIAGRAMME EN ARAIGNÉE (RADAR CHART)
# =============================================================================

def admin_create_radar(session_code):
    """Admin form to create a radar chart activity."""
    if f"radar_count_{session_code}" not in st.session_state:
        st.session_state[f"radar_count_{session_code}"] = 4
        
    st.markdown("#### 🕸️ Créer un Diagramme en Araignée")

    title = st.text_input("Titre", placeholder="Ex: Évaluation de l'équipe", key=f"radar_t_{session_code}")
    cols = st.columns(3)
    criteria = []
    for i in range(st.session_state[f"radar_count_{session_code}"]):
        with cols[i % 3]:
            c = st.text_input(f"Critère {i+1}", key=f"radar_c_{i}_{session_code}", placeholder=f"Critère {i+1}")
            if c:
                criteria.append(c)

    col_add, col_sub = st.columns(2)
    with col_add:
        if st.button("➕ Ajouter un critère", key=f"add_radar_crit_{session_code}", use_container_width=True):
            st.session_state[f"radar_count_{session_code}"] += 1
            st.rerun()
    with col_sub:
        if st.button("✅ Créer le diagramme", type="primary", key=f"submit_radar_{session_code}", use_container_width=True):
            if title and len(criteria) >= 4:
                session = get_session(session_code)
                activity = {
                    "type": "radar",
                    "id": f"radar_{len(session['activities'])}_{int(time.time())}",
                    "title": title,
                    "criteria": criteria,
                    "responses": [],  # List of {"participant": str, "scores": [int]}
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }
                session["activities"].append(activity)
                save_sessions()
                st.success("Diagramme en araignée créé avec succès !")
                st.rerun()
            else:
                st.warning("Veuillez saisir un titre et au moins 4 critères.")


def admin_view_radar_results(activity):
    """Display the radar chart with averaged scores using Plotly."""
    responses = activity.get("responses", [])

    if not responses:
        st.info("🕐 En attente des évaluations des participants...")
        return

    criteria = activity["criteria"]
    # Calculate averages
    all_scores = [r["scores"] for r in responses]
    avg_scores = [sum(s[i] for s in all_scores) / len(all_scores) for i in range(len(criteria))]

    # Close the radar
    plot_criteria = criteria + [criteria[0]]
    plot_avg = avg_scores + [avg_scores[0]]

    fig = go.Figure()

    # Individual responses (faded)
    for resp in responses:
        scores = resp["scores"] + [resp["scores"][0]]
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=plot_criteria,
            fill=None,
            name=resp["participant"],
            line=dict(width=1),
            opacity=0.3,
            showlegend=False,
        ))

    # Average (bold)
    fig.add_trace(go.Scatterpolar(
        r=plot_avg,
        theta=plot_criteria,
        fill='toself',
        name="Moyenne",
        fillcolor='rgba(66,133,244,0.15)',
        line=dict(color=GOOGLE_COLORS["blue"], width=3),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickfont=dict(size=11, family="Roboto"),
                gridcolor="#E8EAED",
            ),
            angularaxis=dict(
                type='category',
                tickfont=dict(size=13, family="Google Sans, Roboto"),
                gridcolor="#E8EAED",
            ),
            bgcolor="white",
            gridshape="linear",
        ),
        showlegend=True,
        legend=dict(font=dict(family="Roboto", size=12)),
        paper_bgcolor="white",
        font=dict(family="Roboto"),
        height=450,
        margin=dict(l=60, r=60, t=30, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stats
    col_stats = st.columns(len(criteria))
    for i, c in enumerate(criteria):
        with col_stats[i]:
            st.metric(c, f"{avg_scores[i]:.1f}/10")

    st.markdown(f'<span class="badge badge-count">👥 {len(responses)} évaluation{"s" if len(responses) > 1 else ""}</span>',
                unsafe_allow_html=True)


def participant_rate_radar(activity, participant_name):
    """Participant form to rate criteria on a radar chart."""
    responses = activity.get("responses", [])
    my_resp = next((r for r in responses if r["participant"] == participant_name), None)

    if my_resp:
        scores_str = '<br>'.join(f"- {c}: <b>{s}/10</b>" for c, s in zip(activity["criteria"], my_resp["scores"]))
        st.markdown(f"""
        <div class="confirmation-box">
            <h3>✅ Évaluation enregistrée !</h3>
            <p style="text-align: left; margin-top: 10px;">Vos réponses :<br>{scores_str}</p>
        </div>
        """, unsafe_allow_html=True)
        return

    st.subheader(activity['title'])
    st.markdown("*Évaluez chaque critère de 1 à 10 :*")

    scores = []
    for i, criterion in enumerate(activity["criteria"]):
        score = st.slider(
            criterion,
            min_value=1, max_value=10, value=5,
            key=f"radar_score_{activity['id']}_{i}_{participant_name}"
        )
        scores.append(score)

    if st.button("✅ Envoyer mon évaluation",
                 key=f"btn_radar_{activity['id']}_{participant_name}",
                 use_container_width=True):
        activity.setdefault("responses", []).append({
            "participant": participant_name,
            "scores": scores,
        })
        save_sessions()
        st.rerun()


# =============================================================================
# ACTIVITY: NUAGE DE MOTS (WORD CLOUD)
# =============================================================================

def admin_create_wordcloud(session_code):
    """Admin form to create a word cloud activity."""
    st.markdown("#### ☁️ Créer un Nuage de Mots")

    with st.form(f"wc_form_{session_code}", clear_on_submit=True, border=False):
        prompt = st.text_input("Question / Prompt",
                                   placeholder="Ex: En un mot, décrivez votre semaine")

        submitted = st.form_submit_button("✅ Créer le nuage de mots", use_container_width=True)
        if submitted and prompt:
            session = get_session(session_code)
            activity = {
                "type": "wordcloud",
                "id": f"wc_{len(session['activities'])}_{int(time.time())}",
                "prompt": prompt,
                "words": [],  # List of {"word": str, "participant": str}
                "status": "active",
                "created_at": datetime.now().isoformat(),
            }
            session["activities"].append(activity)
            save_sessions()
            st.success("Nuage de mots créé avec succès !")
            st.rerun()
        elif submitted:
            st.warning("Veuillez saisir une question.")


def admin_view_wordcloud(activity):
    """Generate and display the word cloud."""
    words_list = activity.get("words", [])

    if not words_list:
        st.info("🕐 En attente des mots des participants...")
        return

    # Count word frequencies
    word_freq = Counter(w["word"].lower().strip() for w in words_list if w["word"].strip())

    if not word_freq:
        st.info("Aucun mot valide soumis.")
        return

    # Generate word cloud
    wc = WordCloud(
        width=900,
        height=450,
        background_color="white",
        colormap="Set2",
        font_path=None,  # Uses default
        max_words=100,
        max_font_size=150,
        min_font_size=14,
        prefer_horizontal=1.0, # All horizontal
        relative_scaling=1.0, # Word size strictly proportionate to frequency
        margin=10,
    )
    wc.generate_from_frequencies(word_freq)

    # Convert to image
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.set_axis_off()
    plt.tight_layout(pad=0)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)

    st.image(buf, use_container_width=True)

    # Word list
    st.markdown(f'<span class="badge badge-count">💬 {len(words_list)} contribution{"s" if len(words_list) > 1 else ""}</span>',
                unsafe_allow_html=True)

    with st.expander("📋 Voir tous les mots"):
        for word, count in word_freq.most_common():
            st.markdown(f"- **{word}** × {count}")


def participant_submit_words(activity, participant_name):
    """Participant form to submit words for the word cloud."""
    my_words = [w["word"] for w in activity.get("words", []) if w["participant"] == participant_name]
    if my_words:
        st.info(f"💡 Vos mots déjà envoyés : **{', '.join(my_words)}**")

    st.subheader(activity['prompt'])
    st.markdown("*Entrez un ou plusieurs mots (séparés par des virgules) :*")

    input_key = f"wc_input_{activity['id']}_{participant_name}"
    
    with st.form(key=f"wc_part_form_{activity['id']}_{participant_name}", clear_on_submit=True, border=False):
        words_input = st.text_input(
            "Vos mots",
            key=input_key,
            placeholder="Ex: innovation, collaboration, énergie",
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("✅ Envoyer", use_container_width=True)
        
        if submitted:
            if words_input.strip():
                words = [w.strip() for w in words_input.split(",") if w.strip()]
                for word in words:
                    activity.setdefault("words", []).append({
                        "word": word,
                        "participant": participant_name,
                    })
                save_sessions()
                st.toast("✅ Mots envoyés !")
                st.rerun()
            else:
                st.warning("Veuillez saisir au moins un mot.")


# =============================================================================
# ACTIVITY: ÉCHELLE DE LIKERT
# =============================================================================

def admin_create_likert(session_code):
    """Admin form to create a Likert scale activity."""
    st.markdown("#### 📏 Créer une Échelle de Likert")
    statement = st.text_input("Affirmation", placeholder="Ex: Je suis satisfait de cette réunion.", key=f"likert_statement_{session_code}")
        
    col1, col2 = st.columns(2)
    with col1:
        scale_min = st.number_input("Note minimum", min_value=0, max_value=1, value=1, key=f"lik_min_{session_code}")
        scale_max = st.number_input("Note maximum", min_value=2, max_value=10, value=5, key=f"lik_max_{session_code}")
    with col2:
        label_min = st.text_input("Label Min", value="Pas du tout d'accord", key=f"lik_lmin_{session_code}")
        label_max = st.text_input("Label Max", value="Tout à fait d'accord", key=f"lik_lmax_{session_code}")
        
    if st.button("✅ Créer l'échelle de Likert", type="primary", key=f"submit_likert_{session_code}", use_container_width=True):
        if statement:
            session = get_session(session_code)
            votes = {}
            for i in range(scale_min, scale_max + 1):
                if i == scale_min: label = f"{i} - {label_min}"
                elif i == scale_max: label = f"{i} - {label_max}"
                else: label = str(i)
                votes[label] = 0
                
            activity = {
                "type": "likert",
                "id": f"likert_{len(session['activities'])}_{int(time.time())}",
                "statement": statement,
                "votes": votes,
                "voters": [],
                "voter_choices": {},
                "status": "active",
                "created_at": datetime.now().isoformat(),
            }
            session["activities"].append(activity)
            save_sessions()
            st.success("Activité créée avec succès !")
            st.rerun()
        else:
            st.warning("Veuillez saisir une affirmation.")

def admin_view_likert_results(activity):
    """Display Likert scale results."""
    votes = activity["votes"]
    total = sum(votes.values())

    if total == 0:
        st.info("🕐 En attente des votes des participants...")
        return

    labels = list(votes.keys())
    values = list(votes.values())
    colors = [GOOGLE_COLORS["red"], GOOGLE_COLORS["light_red"],
              GOOGLE_COLORS["yellow"], GOOGLE_COLORS["light_green"], GOOGLE_COLORS["green"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=[f"{v}" for v in values],
        textposition='auto',
    ))
    fig.update_layout(
        title=None,
        xaxis_title="Nombre de votes",
        yaxis_title=None,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=300,
        margin=dict(l=10, r=20, t=10, b=40),
        xaxis=dict(gridcolor="#E8EAED", zeroline=False),
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Calculate average
    total_score = 0
    for k, v in votes.items():
        try:
            score_val = int(str(k).split(" - ")[0])
            total_score += score_val * v
        except ValueError:
            pass
            
    avg = total_score / total if total > 0 else 0
    
    st.markdown(f"**Moyenne : {avg:.1f}/5**")
    st.markdown(f'<span class="badge badge-count">📊 {total} vote{"s" if total > 1 else ""}</span>', unsafe_allow_html=True)

def participant_vote_likert(activity, participant_name):
    """Participant interface for Likert scale."""
    if participant_name in activity.get("voters", []):
        my_choice = activity.get("voter_choices", {}).get(participant_name, "Inconnu")
        st.markdown(f"""
        <div class="confirmation-box">
            <h3>✅ Vote enregistré !</h3>
            <p>Votre choix : <strong>{my_choice}</strong></p>
        </div>
        """, unsafe_allow_html=True)
        return

    st.subheader(activity['statement'])
    
    options = list(activity["votes"].keys())
    
    choice = st.radio(
        "Votre niveau d'accord :",
        options,
        key=f"likert_vote_{activity['id']}_{participant_name}",
        label_visibility="collapsed",
    )

    if st.button("✅ Voter", key=f"btn_likert_{activity['id']}_{participant_name}", use_container_width=True):
        activity["votes"][choice] = activity["votes"].get(choice, 0) + 1
        activity.setdefault("voters", []).append(participant_name)
        activity.setdefault("voter_choices", {})[participant_name] = choice
        save_sessions()
        st.rerun()


# =============================================================================
# ACTIVITY: MUR DES IDÉES (BRAINSTORMING)
# =============================================================================

def get_category_color(index):
    """Return styling info and emoji for a given category index."""
    colors = [
        {"bg": "#E8F0FE", "border": "#4285F4", "emoji": "🔵"},
        {"bg": "#FCE8E6", "border": "#EA4335", "emoji": "🔴"},
        {"bg": "#FEF7E0", "border": "#FBBC05", "emoji": "🟡"},
        {"bg": "#E6F4EA", "border": "#34A853", "emoji": "🟢"},
        {"bg": "#FFEFE6", "border": "#FF6D01", "emoji": "🟠"},
        {"bg": "#F3E8FD", "border": "#A142F4", "emoji": "🟣"}
    ]
    return colors[index % len(colors)]

def admin_create_brainstorming(session_code):
    """Admin form to create a brainstorming activity."""
    st.markdown("#### 💡 Créer un Mur des Idées")
    with st.form(f"brain_form_{session_code}", clear_on_submit=True, border=False):
        title = st.text_input("Titre du brainstorming", placeholder="Ex: Rétrospective de sprint")
        categories_str = st.text_input("Catégories (séparées par des virgules)", placeholder="Ex: À garder, À améliorer, Nouvelles idées")
            
        submitted = st.form_submit_button("✅ Créer le mur des idées", use_container_width=True)
        if submitted and title and categories_str:
            categories = [c.strip() for c in categories_str.split(",") if c.strip()]
            if len(categories) > 0:
                session = get_session(session_code)
                activity = {
                    "type": "brainstorming",
                    "id": f"brain_{len(session['activities'])}_{int(time.time())}",
                    "title": title,
                    "categories": categories,
                    "ideas": {c: [] for c in categories},
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }
                session["activities"].append(activity)
                save_sessions()
                st.success("Activité créée avec succès !")
                st.rerun()
            else:
                st.warning("Veuillez saisir au moins une catégorie valide.")
        elif submitted:
            st.warning("Veuillez saisir un titre et des catégories.")

def admin_view_brainstorming_results(activity):
    """Display brainstorming results in columns."""
    categories = activity.get("categories", [])
    ideas = activity.get("ideas", {})
    
    total_ideas = sum(len(cat_ideas) for cat_ideas in ideas.values())
    st.markdown(f'<span class="badge badge-count">💬 {total_ideas} idée{"s" if total_ideas > 1 else ""} au total</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not categories:
        return

    cols = st.columns(len(categories))
    for i, cat in enumerate(categories):
        style = get_category_color(i)
        with cols[i]:
            st.markdown(f"##### {style['emoji']} {cat} ({len(ideas.get(cat, []))})")
            for idea in reversed(ideas.get(cat, [])):
                st.markdown(f"""
                <div style="background-color: {style['bg']}; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid {style['border']}; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="font-size: 0.95rem;">{idea['text']}</div>
                    <div style="font-size: 0.75rem; color: #5F6368; margin-top: 5px; text-align: right;">- {idea['author']}</div>
                </div>
                """, unsafe_allow_html=True)

def participant_submit_idea_brainstorming(activity, participant_name):
    """Participant interface to submit idea to a category."""
    st.subheader(activity['title'])
    
    categories = activity.get("categories", [])
    cat_options = [f"{get_category_color(i)['emoji']} {cat}" for i, cat in enumerate(categories)]
    
    selected_val = st.selectbox("Choisissez une catégorie :", cat_options, key=f"brain_cat_{activity['id']}_{participant_name}")
    cat = categories[cat_options.index(selected_val)]
    
    input_key = f"brain_text_{activity['id']}_{participant_name}"
    
    with st.form(key=f"brain_part_form_{activity['id']}_{participant_name}", clear_on_submit=True, border=False):
        idea_text = st.text_area("Votre idée :", key=input_key)
        
        submitted = st.form_submit_button("✅ Ajouter l'idée", use_container_width=True)
        
        if submitted:
            if idea_text.strip():
                activity.setdefault("ideas", {}).setdefault(cat, []).append({"text": idea_text.strip(), "author": participant_name})
                save_sessions()
                st.toast("✅ Idée ajoutée avec succès !")
                st.rerun()
            else:
                st.warning("Veuillez saisir une idée.")
            
    my_ideas = []
    for c, items in activity.get("ideas", {}).items():
        for item in items:
            if item["author"] == participant_name:
                my_ideas.append((c, item["text"]))
                
    if my_ideas:
        st.markdown("---")
        st.markdown("**Vos idées soumises :**")
        for c, t in my_ideas:
            st.markdown(f"- [{c}] {t}")


# =============================================================================
# ACTIVITY: PRIORISATION
# =============================================================================

def admin_create_prioritization(session_code):
    """Admin form to create a prioritization activity."""
    st.markdown("#### 🥇 Créer une Priorisation")
    with st.form(f"prio_form_{session_code}", clear_on_submit=True, border=False):
        title = st.text_input("Question", placeholder="Ex: Quelles sont les priorités pour le prochain trimestre ?")
        items_str = st.text_area("Éléments à prioriser (un par ligne)", placeholder="Projet A\nProjet B\nAmélioration UX")
            
        submitted = st.form_submit_button("✅ Créer la priorisation", use_container_width=True)
        if submitted and title and items_str:
            items = [i.strip() for i in items_str.split('\n') if i.strip()]
            if len(items) >= 2:
                session = get_session(session_code)
                activity = {
                    "type": "prioritization",
                    "id": f"prio_{len(session['activities'])}_{int(time.time())}",
                    "title": title,
                    "items": items,
                    "rankings": [],
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }
                session["activities"].append(activity)
                save_sessions()
                st.success("Activité créée avec succès !")
                st.rerun()
            else:
                st.warning("Veuillez saisir au moins 2 éléments à prioriser.")
        elif submitted:
            st.warning("Veuillez remplir tous les champs.")

def admin_view_prioritization_results(activity):
    """Display prioritization ranking results."""
    rankings = activity.get("rankings", [])
    items = activity.get("items", [])
    
    if not rankings:
        st.info("🕐 En attente des réponses des participants...")
        return
        
    scores = {item: 0 for item in items}
    n = len(items)
    
    for r in rankings:
        for idx, item in enumerate(r.get("ranking", [])):
            if item in scores:
                scores[item] += (n - idx)
                
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, v in sorted_scores]
    values = [v for k, v in sorted_scores]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker_color=GOOGLE_COLORS["blue"],
        text=[f"{v} pts" for v in values],
        textposition='auto',
    ))
    fig.update_layout(
        title=None,
        xaxis_title="Points",
        yaxis_title=None,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(300, len(items) * 40 + 100),
        margin=dict(l=10, r=20, t=10, b=40),
        xaxis=dict(gridcolor="#E8EAED", zeroline=False),
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f'<span class="badge badge-count">👥 {len(rankings)} participant{"s" if len(rankings) > 1 else ""}</span>', unsafe_allow_html=True)

def participant_rank_prioritization(activity, participant_name):
    """Participant interface for prioritization."""
    rankings = activity.get("rankings", [])
    my_rank = next((r for r in rankings if r["participant"] == participant_name), None)
    
    if my_rank:
        st.markdown("""
        <div class="confirmation-box">
            <h3>✅ Vos priorités sont enregistrées !</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Votre classement :**")
        for i, item in enumerate(my_rank.get("ranking", [])):
            st.markdown(f"{i+1}. {item}")
        return

    st.subheader(activity['title'])
    st.markdown("*Sélectionnez les éléments dans l'ordre de priorité (le 1er est le plus important) :*")
    
    selected_ranking = st.multiselect(
        "Ordre de priorité :",
        options=activity["items"],
        key=f"prio_rank_{activity['id']}_{participant_name}",
        placeholder="Choisissez d'abord le plus prioritaire..."
    )
    
    if len(selected_ranking) > 0:
        st.markdown("**Aperçu de votre classement :**")
        for i, item in enumerate(selected_ranking):
            st.markdown(f"{i+1}. {item}")

    if st.button("✅ Valider mon classement", key=f"btn_prio_{activity['id']}_{participant_name}", use_container_width=True):
        if len(selected_ranking) == len(activity["items"]):
            activity.setdefault("rankings", []).append({
                "participant": participant_name,
                "ranking": selected_ranking
            })
            save_sessions()
            st.rerun()
        else:
            st.warning(f"Veuillez classer tous les éléments ({len(selected_ranking)}/{len(activity['items'])} sélectionnés).")


# =============================================================================
# ADMIN INTERFACE
# =============================================================================

# This fragment auto-refreshes for live results (except wordcloud)
@st.experimental_fragment(run_every="3s") if hasattr(st, "experimental_fragment") else (st.fragment(run_every="3s") if hasattr(st, "fragment") else lambda f: f)
def live_results_fragment(session_code, act_id):
    """Auto-refreshing fragment for live results (except wordcloud)."""
    fresh_session = get_session(session_code)
    if not fresh_session: return
    act = next((a for a in fresh_session.get("activities", []) if a["id"] == act_id), None)
    if not act: return
    act_type = act["type"]
    if act_type == "poll":
        admin_view_poll_results(act)
    elif act_type == "moodboard":
        admin_view_heatmap(act)
    elif act_type == "radar":
        admin_view_radar_results(act)
    elif act_type == "likert":
        admin_view_likert_results(act)
    elif act_type == "brainstorming":
        admin_view_brainstorming_results(act)
    elif act_type == "prioritization":
        admin_view_prioritization_results(act)

def static_wordcloud_fragment(session_code, act_id):
    """Non-refreshing fragment for wordclouds."""
    fresh_session = get_session(session_code)
    if not fresh_session: return
    act = next((a for a in fresh_session.get("activities", []) if a["id"] == act_id), None)
    if not act: return
    admin_view_wordcloud(act)

def display_live_results(session_code, act_id):
    """Dispatcher for live results."""
    fresh_session = get_session(session_code)
    if not fresh_session: return
    act = next((a for a in fresh_session.get("activities", []) if a["id"] == act_id), None)
    if not act: return
    
    if act["type"] == "wordcloud":
        static_wordcloud_fragment(session_code, act_id)
    else:
        live_results_fragment(session_code, act_id)


def generate_zip_export(session):
    """Generate a ZIP file with CSV data and PNG charts for the session."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # Create Main Session CSV
        session_info = pd.DataFrame([{
            "Nom_Session": session.get("name", "Sans nom"),
            "Code": session.get("code", "N/A"),
            "Date": session.get("created_at", "N/A"),
            "Participants": ", ".join(session.get("participants", set()))
        }])
        zip_file.writestr("01_Info_Session.csv", session_info.to_csv(index=False))
        
        # Add Activities
        for idx, act in enumerate(session.get('activities', [])):
            act_type = act.get('type', 'Inconnu')
            
            # Safely handle the title which can be None
            title_parts = []
            if act.get('question'): title_parts.append(act['question'])
            if act.get('title'): title_parts.append(act['title'])
            if act.get('prompt'): title_parts.append(act['prompt'])
            
            raw_title = title_parts[0] if title_parts else f"Activite_{idx+1}"
            safe_title = "".join(x for x in str(raw_title) if x.isalnum() or x in " _-")[:30]
            prefix = f"{idx+2:02d}_{act_type}_{safe_title}"
            
            if act_type == "poll":
                df = pd.DataFrame(list(act.get('votes', {}).items()), columns=["Option", "Votes"])
                zip_file.writestr(f"{prefix}.csv", df.to_csv(index=False))
                
                # Image Result
                if act.get('votes'):
                    fig, ax = plt.subplots(figsize=(8, 5))
                    ax.bar(list(act['votes'].keys()), list(act['votes'].values()), color=GOOGLE_COLORS["blue"])
                    ax.set_title(str(raw_title), pad=20, fontsize=14, fontweight="bold")
                    ax.set_ylabel("Votes")
                    img_buf = io.BytesIO()
                    fig.savefig(img_buf, format='png', dpi=120, bbox_inches='tight')
                    plt.close(fig)
                    zip_file.writestr(f"{prefix}_resultat.png", img_buf.getvalue())
                
            elif act_type == "moodboard":
                df = pd.DataFrame(act.get('clicks', []))
                if not df.empty:
                    df['x'] = (df['x']*100).round(1).astype(str) + '%'
                    df['y'] = (df['y']*100).round(1).astype(str) + '%'
                zip_file.writestr(f"{prefix}.csv", df.to_csv(index=False))
                
                # Image Result
                if act.get("image_data"):
                    img = Image.open(io.BytesIO(act["image_data"])).convert("RGBA")
                    draw = ImageDraw.Draw(img)
                    img_w, img_h = img.size
                    for c in act.get('clicks', []):
                        cx, cy = c['x'] * img_w, c['y'] * img_h
                        draw.ellipse((cx-15, cy-15, cx+15, cy+15), fill=GOOGLE_COLORS["blue"], outline="white", width=2)
                    img_buf = io.BytesIO()
                    img.save(img_buf, format="PNG")
                    zip_file.writestr(f"{prefix}_resultat.png", img_buf.getvalue())
                    
            elif act_type == "radar":
                criteria = act.get('criteria', [])
                records = []
                for r in act.get('responses', []):
                    record = {"Participant": r.get("participant", "Anonyme")}
                    record.update({c: s for c, s in zip(criteria, r.get("scores", []))})
                    records.append(record)
                df = pd.DataFrame(records)
                zip_file.writestr(f"{prefix}.csv", df.to_csv(index=False))
                
                # Image Result
                if act.get('responses') and len(criteria) >= 3:
                    try:
                        all_scores = [r["scores"] for r in act['responses']]
                        avg_scores = [sum(s[i] for s in all_scores) / len(all_scores) for i in range(len(criteria))]
                        plot_criteria = criteria + [criteria[0]]
                        plot_avg = avg_scores + [avg_scores[0]]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatterpolar(
                            r=plot_avg,
                            theta=plot_criteria,
                            fill='toself',
                            name="Moyenne",
                            fillcolor='rgba(66,133,244,0.15)',
                            line=dict(color=GOOGLE_COLORS["blue"], width=3),
                        ))
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(visible=True, range=[0, 10]),
                                angularaxis=dict(type='category'),
                                gridshape="linear",
                            ),
                            showlegend=False,
                            title=str(raw_title)
                        )
                        img_bytes = fig.to_image(format="png", engine="kaleido")
                        zip_file.writestr(f"{prefix}_resultat.png", img_bytes)
                    except Exception as e:
                        print(f"Export Radar PNG error: {e}")
                
            elif act_type == "wordcloud":
                words = act.get('words', [])
                if words:
                    from collections import Counter
                    word_freq = Counter(w["word"].lower().strip() for w in words if w.get("word", "").strip())
                    df = pd.DataFrame(word_freq.most_common(), columns=["Mot", "Frequence"])
                    zip_file.writestr(f"{prefix}.csv", df.to_csv(index=False))
                    
                    # Image Result
                    if word_freq:
                        wc = WordCloud(width=800, height=400, background_color="white", colormap="Set2")
                        wc.generate_from_frequencies(word_freq)
                        fig, ax = plt.subplots(figsize=(8, 4))
                        ax.imshow(wc, interpolation='bilinear')
                        ax.set_axis_off()
                        ax.set_title(str(raw_title), pad=20, fontsize=14, fontweight="bold")
                        img_buf = io.BytesIO()
                        fig.savefig(img_buf, format='png', dpi=120, bbox_inches='tight')
                        plt.close(fig)
                        zip_file.writestr(f"{prefix}_resultat.png", img_buf.getvalue())
                    
            elif act_type == "likert":
                df = pd.DataFrame(list(act.get('votes', {}).items()), columns=["Niveau", "Votes"])
                zip_file.writestr(f"{prefix}.csv", df.to_csv(index=False))
                
                if act.get('votes'):
                    fig, ax = plt.subplots(figsize=(8, 5))
                    ax.barh(list(act['votes'].keys()), list(act['votes'].values()), color=GOOGLE_COLORS["blue"])
                    ax.set_title(str(raw_title), pad=20, fontsize=14, fontweight="bold")
                    ax.invert_yaxis()
                    img_buf = io.BytesIO()
                    fig.savefig(img_buf, format='png', dpi=120, bbox_inches='tight')
                    plt.close(fig)
                    zip_file.writestr(f"{prefix}_resultat.png", img_buf.getvalue())
                    
            elif act_type == "brainstorming":
                records = []
                for cat, items in act.get("ideas", {}).items():
                    for item in items:
                        records.append({"Categorie": cat, "Idee": item["text"], "Auteur": item["author"]})
                df = pd.DataFrame(records)
                if not df.empty:
                    zip_file.writestr(f"{prefix}.csv", df.to_csv(index=False))
                    
            elif act_type == "prioritization":
                rank_records = []
                for r in act.get("rankings", []):
                    rec = {"Participant": r.get("participant", "Anonyme")}
                    for i, item in enumerate(r.get("ranking", [])):
                        rec[f"Rang {i+1}"] = item
                    rank_records.append(rec)
                df = pd.DataFrame(rank_records)
                zip_file.writestr(f"{prefix}_classements.csv", df.to_csv(index=False))
                
                items = act.get("items", [])
                rankings = act.get("rankings", [])
                if items and rankings:
                    scores = {item: 0 for item in items}
                    n = len(items)
                    for r in rankings:
                        for idx, item in enumerate(r.get("ranking", [])):
                            if item in scores:
                                scores[item] += (n - idx)
                    
                    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=False)
                    if sorted_scores:
                        fig, ax = plt.subplots(figsize=(8, max(4, len(items)*0.6)))
                        ax.barh([k for k, v in sorted_scores], [v for k, v in sorted_scores], color=GOOGLE_COLORS["blue"])
                        ax.set_title(str(raw_title) + " - Scores", pad=20, fontsize=14, fontweight="bold")
                        img_buf = io.BytesIO()
                        fig.savefig(img_buf, format='png', dpi=120, bbox_inches='tight')
                        plt.close(fig)
                        zip_file.writestr(f"{prefix}_resultat.png", img_buf.getvalue())
                    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def render_header(subtitle=""):
    """Render the app header."""
    st.markdown(f"""
    <div class="app-header">
        <h1>🎯 {APP_TITLE}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def admin_view():
    """Main admin interface."""
    if "fullscreen_results" not in st.session_state:
        st.session_state["fullscreen_results"] = False

    if not st.session_state["fullscreen_results"]:
        render_header("Interface Administrateur — Gérez vos sessions et activités")

    # If no session is active, show creation form
    if not st.session_state.get("current_session_code"):
        admin_session_manager()
        return

    code = st.session_state["current_session_code"]
    session = get_session(code)

    if not session:
        st.error("Session introuvable.")
        st.session_state["current_session_code"] = None
        st.rerun()
        return


    # ---- Session Info Bar ----
    if not st.session_state["fullscreen_results"]:
        col_info, col_qr = st.columns([2, 1])

        with col_info:
            st.markdown(f"""
            <div class="session-code-box">
                <div class="session-code-label">Code de session</div>
                <div class="session-code">{code}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="material-card">
                <h3>📋 {session['name']}</h3>
                <p>
                    <span class="badge badge-active">● Active</span>&nbsp;&nbsp;
                    <span class="badge badge-count">👥 {len(session['participants'])} participant{"s" if len(session['participants']) > 1 else ""}</span>&nbsp;&nbsp;
                    <span class="badge badge-count">📝 {len(session['activities'])} activité{"s" if len(session['activities']) > 1 else ""}</span>
                </p>
            </div>
            """, unsafe_allow_html=True)

        with col_qr:
            with st.container(border=True):
                st.markdown("<div style='text-align: center'><b>📱 QR Code Participants</b></div>", unsafe_allow_html=True)
                qr_buf = generate_qr_code(code)
                st.image(qr_buf, use_container_width=True)
                st.markdown(f"<div style='text-align: center; font-size: 0.8em; color: gray'>Code: <b>{code}</b><br><i>(Appuyez sur Échap pour fermer le QR Code en grand)</i></div>", unsafe_allow_html=True)

        st.markdown("---")

        # ---- Activity Creation ----
        st.markdown("### ➕ Nouvelle Activité")
        st.markdown("""
        <style>
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.creation-container),
            div.element-container:has(.creation-container) + div {
                background-color: #E8F0FE !important;
                border-radius: 12px;
                padding: 1rem;
                border: 2px solid #A1C2FA !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown('<div class="creation-container"></div>', unsafe_allow_html=True)
            act_options = {
                "poll": "📊 Sondage Express",
                "moodboard": "🌤️ Placement sur image",
                "radar": "🕸️ Diagramme Araignée",
                "wordcloud": "☁️ Nuage de Mots",
                "likert": "📏 Échelle de Likert",
                "brainstorming": "💡 Mur des Idées",
                "prioritization": "🥇 Priorisation"
            }
            
            selected_act = st.selectbox("Choisissez le type d'activité à créer :", list(act_options.keys()), format_func=lambda x: act_options[x], label_visibility="collapsed")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if selected_act == "poll": admin_create_poll(code)
            elif selected_act == "moodboard": admin_create_moodboard(code)
            elif selected_act == "radar": admin_create_radar(code)
            elif selected_act == "wordcloud": admin_create_wordcloud(code)
            elif selected_act == "likert": admin_create_likert(code)
            elif selected_act == "brainstorming": admin_create_brainstorming(code)
            elif selected_act == "prioritization": admin_create_prioritization(code)

        st.markdown("---")

    # ---- Live Results (Slideshow) ----
    col_res_title, col_res_fs = st.columns([4, 1])
    with col_res_title:
        st.markdown("### 📊 Résultats en Direct")
    with col_res_fs:
        if st.session_state["fullscreen_results"]:
            if st.button("⬅️ Quitter Plein Écran", use_container_width=True):
                st.session_state["fullscreen_results"] = False
                st.rerun()
        else:
            if st.button("📺 Plein Écran", use_container_width=True):
                st.session_state["fullscreen_results"] = True
                st.rerun()

    if not session["activities"]:
        st.info("Aucune activité créée pour le moment. Utilisez les onglets ci-dessus pour en créer une !")
        return

    # Slideshow state logic
    total_slides = len(session["activities"])
    if "slide_index" not in st.session_state:
        st.session_state["slide_index"] = 0
    elif st.session_state["slide_index"] >= total_slides:
        st.session_state["slide_index"] = total_slides - 1

    act_idx = st.session_state["slide_index"]
    activities_list = list(reversed(session["activities"]))  # newest first
    activity = activities_list[act_idx]
    
    # Slideshow navigation
    col_prev, col_prog, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅️ Précédente", disabled=(act_idx == 0), use_container_width=True):
            st.session_state["slide_index"] -= 1
            st.rerun()
    with col_prog:
        st.write(f"<div style='text-align: center; padding-top: 10px; color: gray;'>Activité {act_idx + 1} / {total_slides}</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("Suivante ➡️", disabled=(act_idx == total_slides - 1), use_container_width=True):
            st.session_state["slide_index"] += 1
            st.rerun()

    st.markdown("---")

    act_type = activity["type"]
    type_icons = {
        "poll": "📊", "moodboard": "🌤️", "radar": "🕸️", "wordcloud": "☁️",
        "likert": "📏", "brainstorming": "💡", "prioritization": "🥇"
    }
    type_labels = {
        "poll": "Sondage", "moodboard": "Placement sur image", "radar": "Diagramme Araignée", "wordcloud": "Nuage de Mots",
        "likert": "Échelle de Likert", "brainstorming": "Mur des Idées", "prioritization": "Priorisation"
    }

    icon = type_icons.get(act_type, "📝")
    label = type_labels.get(act_type, "Activité")
    title = activity.get("question") or activity.get("title") or activity.get("prompt") or activity.get("statement") or "Sans titre"

    with st.container(border=True):
        col_t1, col_t2 = st.columns([5, 1])
        with col_t1:
            st.markdown(f"#### {icon} {label} : {title}")
        with col_t2:
            real_idx = len(session["activities"]) - 1 - act_idx
            if st.button("🗑️ Supprimer", key=f"del_{activity['id']}", use_container_width=True):
                session["activities"].pop(real_idx)
                save_sessions()
                st.session_state["slide_index"] = max(0, act_idx - 1)
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        display_live_results(code, activity['id'])

    # ---- Control buttons ----
    if not st.session_state["fullscreen_results"]:
        st.markdown("---")
        col_refresh, col_export, col_end = st.columns(3)
        with col_refresh:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.session_state["sessions"] = load_sessions()
                st.rerun()
        with col_export:
            zip_data = generate_zip_export(session)
            st.download_button(
                label="📄 Exporter Session (ZIP)",
                data=zip_data,
                file_name=f"export_{code}_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        with col_end:
            if st.button("🔴 Terminer session", use_container_width=True):
                session["status"] = "ended"
                save_sessions()
                st.session_state["current_session_code"] = None
                st.rerun()


def admin_session_manager():
    """Session creation and selection interface for admin."""
    col_create, col_resume = st.columns(2)

    with col_create:
        with st.container(border=True):
            st.markdown("#### 🆕 Créer une Nouvelle Session")
            with st.form("create_session_form", border=False):
                session_name = st.text_input("Nom de la session",
                                              placeholder="Ex: Réunion d'équipe - Mars 2026")
                create_btn = st.form_submit_button("🚀 Lancer la session", use_container_width=True)
                if create_btn and session_name:
                    code = create_session(session_name)
                    st.session_state["current_session_code"] = code
                    st.rerun()
                elif create_btn:
                    st.warning("Veuillez donner un nom à la session.")

    with col_resume:
        with st.container(border=True):
            st.markdown("#### 📂 Sessions Existantes")
            sessions = st.session_state.get("sessions", {})
            active_sessions = {code: s for code, s in sessions.items() if s.get("status") == "active"}

            if active_sessions:
                for code, s in active_sessions.items():
                    col_name, col_btn = st.columns([7, 3])
                    with col_name:
                        st.markdown(f"**{s['name']}** — Code: `{code}`<br>👥 {len(s['participants'])} participants", unsafe_allow_html=True)
                    with col_btn:
                        st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                        if st.button("Ouverte", key=f"open_{code}", use_container_width=True):
                            st.session_state["current_session_code"] = code
                            st.rerun()
            else:
                st.info("Aucune session active.")


# =============================================================================
# PARTICIPANT INTERFACE
# =============================================================================

def participant_view():
    """Main participant interface (mobile-first)."""
    render_header("Interface Participant — Rejoignez une session")

    # If not in a session, show join form
    if not st.session_state.get("current_session_code"):
        participant_join()
        return

    code = st.session_state["current_session_code"]
    session = get_session(code)

    if not session:
        st.error("Session introuvable.")
        st.session_state["current_session_code"] = None
        st.rerun()
        return

    if session["status"] != "active":
        st.markdown("""
        <div class="material-card" style="text-align: center;">
            <h3>🔴 Session terminée</h3>
            <p>Cette session n'est plus active. Merci pour votre participation !</p>
        </div>
        """, unsafe_allow_html=True)
        return

    participant_name = st.session_state.get("participant_name", "Anonyme")

    # Session info
    st.markdown(f"""
    <div class="material-card" style="text-align: center;">
        <h3>🎯 {session['name']}</h3>
        <p>Connecté en tant que <strong>{participant_name}</strong> • Code: <strong>{code}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    # Activities
    activities = session.get("activities", [])

    if not activities:
        st.markdown("""
        <div class="material-card" style="text-align: center;">
            <h3>⏳ En attente...</h3>
            <p>L'animateur n'a pas encore lancé d'activité. Merci de patienter !</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.session_state["sessions"] = load_sessions()
            st.rerun()
        return

    for activity in reversed(activities):
        act_type = activity["type"]
        type_icons = {
            "poll": "📊", "moodboard": "🌤️", "radar": "🕸️", "wordcloud": "☁️",
            "likert": "📏", "brainstorming": "💡", "prioritization": "🥇"
        }
        type_labels = {
            "poll": "Sondage Express", "moodboard": "Météo du Jour",
            "radar": "Diagramme Araignée", "wordcloud": "Nuage de Mots",
            "likert": "Échelle de Likert", "brainstorming": "Mur des Idées",
            "prioritization": "Priorisation"
        }

        icon = type_icons.get(act_type, "📝")
        label = type_labels.get(act_type, "Activité")
        title = activity.get("question") or activity.get("title") or activity.get("prompt") or activity.get("statement") or "Sans titre"

        with st.container(border=True):
            st.markdown(f"**{icon} {label}**")

            if act_type == "poll":
                participant_vote_poll(activity, participant_name)
            elif act_type == "moodboard":
                participant_click_moodboard(activity, participant_name)
            elif act_type == "radar":
                participant_rate_radar(activity, participant_name)
            elif act_type == "wordcloud":
                participant_submit_words(activity, participant_name)
            elif act_type == "likert":
                participant_vote_likert(activity, participant_name)
            elif act_type == "brainstorming":
                participant_submit_idea_brainstorming(activity, participant_name)
            elif act_type == "prioritization":
                participant_rank_prioritization(activity, participant_name)
        st.markdown("")

    # Footer buttons
    st.markdown("---")
    if st.button("🔄 Rafraîchir la page", use_container_width=True):
        st.session_state["sessions"] = load_sessions()
        st.rerun()


def participant_join():
    """Participant session join form."""
    col_spacer1, col_form, col_spacer2 = st.columns([1, 2, 1])
    with col_form:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; margin-top: 0;'>🔐 Rejoindre une Session</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #5F6368;'>Entrez le code à 4 chiffres affiché par l'animateur</p>", unsafe_allow_html=True)
            with st.form("join_form", border=False):
                name = st.text_input("Votre prénom", placeholder="Ex: Matth")
                code = st.text_input("Code de session (4 chiffres)", placeholder="1234", max_chars=4)

                join_btn = st.form_submit_button("🚀 Rejoindre", use_container_width=True)
                if join_btn:
                    if not name or not code:
                        st.warning("Veuillez saisir votre prénom et le code de session.")
                    elif len(code) != 4 or not code.isdigit():
                        st.error("Le code doit contenir exactement 4 chiffres.")
                    elif join_session(code, name):
                        st.session_state["current_session_code"] = code
                        st.session_state["participant_name"] = name
                        st.rerun()
                    else:
                        st.error("❌ Code invalide ou session terminée.")


# =============================================================================
# LANDING PAGE (ROLE SELECTOR)
# =============================================================================

def landing_page():
    """Landing page with role selection."""
    render_header("Animez vos réunions de manière interactive et gratuite")

    st.markdown("")

    col_spacer1, col_admin, col_spacer2, col_participant, col_spacer3 = st.columns([0.5, 2, 0.5, 2, 0.5])

    st.markdown("""
    <style>
        .role-button {
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }
        div[data-testid="stButton"] button {
            height: 180px;
            border-radius: 12px;
            border: 2px solid #E8EAED;
            background-color: white;
            transition: all 0.2s ease;
        }
        div[data-testid="stButton"] button p {
            font-size: 1.1rem !important;
            font-weight: 500;
        }
        div[data-testid="stButton"] button:hover {
            border-color: #4285F4;
            box-shadow: 0 4px 6px rgba(66, 133, 244, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

    with col_admin:
        if st.button("🖥️ Animateur\n\nCréez et gérez une session", key="btn_admin", use_container_width=True):
            st.session_state["current_role"] = "admin"
            st.rerun()

    with col_participant:
        if st.button("📱 Participant\n\nRejoignez une session avec un code", key="btn_participant", use_container_width=True):
            st.session_state["current_role"] = "participant"
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #5F6368; font-size: 0.85rem; padding: 1rem;">
        <strong>ReuBoost</strong> — Application d'animation de réunions interactives<br>
        Sondages • Placements sur image • Diagrammes Araignée • Nuages de Mots<br>
        <span style="font-size: 0.75rem;">Gratuit et open-source</span>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# MAIN ROUTER
# =============================================================================

def bootstrap():
    """Wrapper to run main."""
    main()

    inject_css()
    init_session_db()

    # Check URL query parameters for routing
    params = st.query_params
    role_param = params.get("role", None)
    code_param = params.get("code", None)

    # Auto-route from URL
    if role_param == "participant" and code_param:
        st.session_state["current_role"] = "participant"
        if not st.session_state.get("current_session_code"):
            # Don't auto-join — let participant enter their name
            pass
    elif role_param == "admin":
        st.session_state["current_role"] = "admin"

    # Route to the correct view
    role = st.session_state.get("current_role")

    # Sidebar global navigation always present
    with st.sidebar:
        st.markdown("### 🧭 Navigation")
        if role:
            st.markdown(f"**Rôle actuel :** {role.capitalize()}")
        else:
            st.markdown("Vous êtes sur l'accueil.")
            
        st.markdown("Accès rapide pour revenir au menu principal.")
        if st.button("🏠 Retour à l'accueil", use_container_width=True):
            st.session_state["current_session_code"] = None
            st.session_state["current_role"] = None
            st.session_state.pop("participant_name", None)
            st.rerun()

    if role == "admin":
        admin_view()
    elif role == "participant":
        participant_view()
    else:
        landing_page()


if __name__ == "__main__":
    bootstrap()

import streamlit as st
from dm_logic import query_dm_system_with_personality

st.title("Dungeon Master Simulator")

st.write("Bienvenido al simulador de Dungeon Master. ¿En qué puedo ayudarte hoy?")

# Caja de texto para que el usuario ingrese su pregunta
question = st.text_input("Haz tu pregunta sobre el manual de Dungeon Master:")
player_state = {
    'health': 100,
    'inventory': ['espada', 'pociones'],
    'quests': ['explorar la cueva']
}

world_state = {
    'current_area': 'bosque oscuro',
    'events': ['el jugador ha derrotado a un lobo feroz']
}


if question:
    # Obtener respuesta del sistema de Dungeon Master
    response = query_dm_system_with_personality(question, player_state, world_state)
    st.write(f"Respuesta: {response}")

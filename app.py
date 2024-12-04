import streamlit as st
from dm_logic import query_dm_system_with_personality

# Inicializar los estados en st.session_state si no existen
if 'player_state' not in st.session_state:
    st.session_state.player_state = {
        'health': 100,
        'inventory': ['espada', 'pociones'],
        'quests': ['explorar la cueva']
    }

if 'world_state' not in st.session_state:
    st.session_state.world_state = {
        'current_area': 'bosque oscuro',
        'events': ['el jugador ha derrotado a un lobo feroz']
    }

# Manejar el input del jugador
def handle_player_input():
    player_input = st.session_state.player_input  # Leer la entrada del jugador
    if player_input:
        # Llamar a la función para obtener la respuesta del Dungeon Master
        result = query_dm_system_with_personality(
            player_input, 
            st.session_state.player_state, 
            st.session_state.world_state
        )

        print(result)
        # Extraer el mensaje y las actualizaciones de estado
        message = result["message"]
        player_updates = result["player_updates"]
        world_updates = result["world_updates"]

        # Actualizar el estado del jugador
        for key, value in player_updates.items():
            if key == "health":
                st.session_state.player_state[key] += value  # Cambios relativos
            elif key == "inventory":
                st.session_state.player_state[key].extend(value)  # Añadir al inventario
            else:
                st.session_state.player_state[key] = value  # Otros cambios directos

        # Actualizar el estado del mundo
        for key, value in world_updates.items():
            if key == "events":
                st.session_state.world_state[key].extend(value)  # Añadir eventos
            else:
                st.session_state.world_state[key] = value  # Otros cambios directos

        # Agregar la entrada y respuesta al historial con formato HTML
        st.session_state.history.append(f"<b style='color:gold;'>Jugador:</b> {player_input}")
        st.session_state.history.append(f"<b style='color:red;'>Dungeon Master:</b> {message}")

        # Limpiar la entrada después de procesarla
        st.session_state.player_input = ""  # Limpiar el campo de texto

# Iniciar la interfaz
st.title("Dungeon Master Simulator")

# Crear las dos columnas (3/4 y 1/4)
col1, col2 = st.columns([3, 1])

# Columna 1: Historial y campo de texto
with col1:
    st.subheader("Historial del Dungeon Master")

    # Mostrar el historial de lo que ha dicho el Dungeon Master
    if 'history' not in st.session_state:
        st.session_state.history = []

    # Mostrar historial con formato HTML
    chat_history = "<br>".join(st.session_state.history)  # Convertir lista de historial en un string con saltos de línea
    
    # Usar una caja con desplazamiento (scroll) y tamaño fijo
    st.markdown(f"<div style='height: 300px; overflow-y: scroll;'>{chat_history}</div>", unsafe_allow_html=True)

    # Caja para insertar la acción o pregunta del jugador
    st.text_input("¿Qué acción tomas?", key="player_input", on_change=handle_player_input)

# Columna 2: Estado del jugador y del mundo
with col2:
    # Mostrar el estado del jugador
    st.subheader("Estado del Jugador")
    st.write(f"**Salud**: {st.session_state.player_state['health']}")
    st.write(f"**Inventario**: {', '.join(st.session_state.player_state['inventory'])}")
    st.write(f"**Misión actual**: {', '.join(st.session_state.player_state['quests'])}")

    # Mostrar el estado del mundo
    st.subheader("Estado del Mundo")
    st.write(f"**Área actual**: {st.session_state.world_state['current_area']}")
    st.write(f"**Eventos recientes**: {', '.join(st.session_state.world_state['events'])}")

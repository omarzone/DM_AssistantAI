import streamlit as st

st.set_page_config(
    page_title="Simulador de Dungeon Master",
    page_icon=""
)

# Título de la página
st.title("¡Bienvenido a tu aventura!")


# Área de texto para mostrar las respuestas del Dungeon Master
st.text_area("Respuesta del Dungeon Master", value="", height=200, key="response")

# Caja de texto para la entrada del usuario
user_input = st.text_input("Escribe tu comando:")
# Botón para enviar el mensaje
if st.button("Enviar"):
    # Aquí es donde iría la lógica para procesar la entrada del usuario y generar la respuesta
    # Por ahora, simplemente mostraremos un mensaje de ejemplo
    st.session_state.response = "¡Estás en una oscura caverna! A lo lejos, escuchas un gruñido. ¿Qué haces?"
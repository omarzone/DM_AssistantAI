import os
import chromadb
from langchain_chroma import Chroma
import json
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai

# Cargar configuración desde config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Configurar la clave API de Google Gemini desde el archivo config.json
os.environ["GOOGLE_API_KEY"] = config["GOOGLE_API_KEY"]

# Crear cliente persistente de ChromaDB desde la ruta persistente proporcionada
chroma_client = chromadb.PersistentClient(path=config["persist_directory"])

# Función para verificar si la colección existe
def check_collection_exists(collection_name):
    """Verifica si una colección existe en ChromaDB"""
    collections = chroma_client.list_collections()
    print("Colecciones existentes:", collections)  # Mostrar todas las colecciones
    return collection_name.strip() in [col.name.strip() for col in collections]

# Nombre de la colección que estamos buscando
collection_name = "dungeon_master_collection"

# Comprobar si la colección existe, si no, crearla
if check_collection_exists(collection_name):
    print(f"La colección '{collection_name}' ya existe.")
    collection = chroma_client.get_collection(name=collection_name)
else:
    print(f"La colección '{collection_name}' no existe. Creando colección...")
    collection = chroma_client.create_collection(name=collection_name)

# Configurar el modelo de embeddings de Google (mismo modelo que en setup.py)
embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# Crear el vectorstore utilizando el modelo de embeddings
vectorstore = Chroma(
    client=chroma_client,
    collection_name=collection_name,
    embedding_function=embeddings_model  # Pasamos el modelo como el embedding_function
)

# Estado inicial del jugador y del mundo
player_state = {
    'health': 100,
    'inventory': ['espada', 'pociones'],
    'quests': ['explorar la cueva']
}

world_state = {
    'current_area': 'bosque oscuro',
    'events': ['el jugador ha derrotado a un lobo feroz']
}

# Función para recuperar los pasajes relevantes
def get_relevant_passage(query: str, db, n_results: int):
    """Recupera los pasajes más relevantes de la base de datos según la consulta"""
    results = db.similarity_search(query, k=n_results)
    context = ""
    for result in results:
        context += " " + result.page_content  # Obtener el contenido de la página
    return context

# Función para construir un prompt con la personalidad del Dungeon Master
def make_rag_prompt(query: str, relevant_info: str, player_state: dict, world_state: dict):
    """Construye un prompt con personalidad para el Dungeon Master"""
    escaped_info = relevant_info.replace("'", "").replace('"', "").replace("\n", " ")
    prompt = f"""
    Eres un Dungeon Master sabio y misterioso, pero también un poco travieso. El jugador tiene {player_state['health']} de salud y lleva {player_state['inventory']}.
    Actualmente está en el {world_state['current_area']} y tiene las siguientes misiones activas: {', '.join(player_state['quests'])}.
    El jugador ya ha tenido estos eventos: {', '.join(world_state['events'])}.
    
    El jugador pregunta: {query}
    
    Responde de manera épica, desafiando al jugador y adaptándote a sus decisiones. Pero también recuerda mantener un tono amigable y lleno de misterio.
    """
    return prompt

# Función para generar la respuesta del Dungeon Master
def query_dm_system_with_personality(query, player_state, world_state):
    """Consulta el sistema de Dungeon Master y obtiene una respuesta personalizada con contexto"""
    try:
        # Recuperar los pasajes relevantes
        relevant_info = get_relevant_passage(query, vectorstore, n_results=3)

        if not relevant_info:
            return "No se encontraron respuestas relevantes. El destino del jugador es incierto..."

        # Construir el prompt para el modelo con personalidad
        prompt = make_rag_prompt(query, relevant_info, player_state, world_state)

        # Generar la respuesta del modelo
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model1 = genai.GenerativeModel("gemini-pro")
        answer = model1.generate_content(prompt)

        # Actualizar el estado del jugador y el mundo basándote en la respuesta
        player_state['health'] -= 10  # Ejemplo de cómo disminuir la salud por una decisión
        world_state['events'].append("El jugador avanza hacia una cueva oscura.")  # Agregar eventos según la respuesta

        return f"{answer.text}"

    except Exception as e:
        return f"Ocurrió un error al realizar la consulta: {e}"

# Ejemplo de uso
query = "¿Qué sucede si decido explorar la cueva?"
print(query_dm_system_with_personality(query, player_state, world_state))

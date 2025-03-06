import os
import chromadb
from langchain_chroma import Chroma
import json
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configurar la clave API de Google Gemini desde el archivo .env
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("Google API key not found. Please set it in the .env file.")

# Cargar configuración desde config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)


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
embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001", temperature=0.4)

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
    """Construye un prompt para el Dungeon Master que genere una respuesta en JSON estructurado."""
    escaped_info = relevant_info.replace("'", "").replace('"', "").replace("\n", " ")

    prompt = f"""
    Eres un Dungeon Master sabio y misterioso. Responde al jugador basándote en el siguiente contexto:
    
    Información relevante del mundo: {escaped_info}
    
    Estado del jugador:
    - Salud: {player_state["health"]}
    - Inventario: {player_state["inventory"]}
    - Misiones activas: {player_state["quests"]}
    
    Estado del mundo:
    - Área actual: {world_state["current_area"]}
    - Eventos pasados: {world_state["events"]}
    
    El jugador pregunta: "{query}"
    
    Use this JSON schema:
    
    Response = {{
        "narrative": str,
        "player_updates": {{
            "health": int,
            "inventory": list[str]
        }},
        "world_updates": {{
            "current_area": str,
            "events": list[str]
        }},
        "options": list[str]  # Esta lista NO PUEDE estar vacía, debe haber al menos una opción.
    }}
    
    Return: Response
    """
    return prompt


# Función para generar la respuesta del Dungeon Master
import json

def query_dm_system_with_personality(query, player_state, world_state):
    """Consulta el sistema de Dungeon Master y actualiza estados según la respuesta en JSON"""
    try:
        # Recuperar los pasajes relevantes
        relevant_info = get_relevant_passage(query, vectorstore, n_results=3)

        if not relevant_info:
            return {
                "message": "No se encontraron respuestas relevantes. El destino del jugador es incierto...",
                "player_updates": {},
                "world_updates": {}
            }

        # Construir el prompt para el modelo
        prompt = make_rag_prompt(query, relevant_info, player_state, world_state)

        # Generar la respuesta del modelo
        genai.configure(api_key=google_api_key)
        # for m in genai.list_models():
        #     if 'generateContent' in m.supported_generation_methods:
        #         print(m.name)
        model1 = genai.GenerativeModel("gemini-2.0-flash")
        
        response = model1.generate_content(prompt)
        print(response.text)
        
        


        # Intentar cargar el JSON de la respuesta
        try:
            response_text = response.text.strip("```json").strip("```").strip()

    # Intentar cargar la respuesta como JSON
            response_json = json.loads(response_text)
            #print(response_json)
        except json.JSONDecodeError:
            return {
                "message": f"La respuesta no estaba en el formato JSON esperado: {response.text}",
                "player_updates": {},
                "world_updates": {}
            }

        # Extraer la narración y actualizaciones
        narrative = response_json.get("narrative", "El Dungeon Master guarda silencio...")
        player_updates = response_json.get("player_updates", {})
        world_updates = response_json.get("world_updates", {})
        options = response_json.get("options", [])

        # Formatear opciones para mostrar
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])

        return {
            "message": f"{narrative}\n\n¿Qué deseas hacer ahora?\n{options_text}\n\n---",
            "player_updates": player_updates,
            "world_updates": world_updates
        }

    except Exception as e:
        return {
            "message": f"Ocurrió un error al realizar la consulta: {e}",
            "player_updates": {},
            "world_updates": {}
        }



# # Ejemplo de uso
# query = "¿Qué sucede si decido explorar la cueva?"
# print(query_dm_system_with_personality(query, player_state, world_state))

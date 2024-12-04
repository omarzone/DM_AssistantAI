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
    """Construye un prompt para el Dungeon Master que genere una respuesta en JSON estructurado."""
    escaped_info = relevant_info.replace("'", "").replace('"', "").replace("\n", " ")
    
    prompt = f"""
    Eres un Dungeon Master sabio y misterioso. Responde al jugador basándote en el siguiente contexto:
    Información relevante del mundo: {escaped_info}
    
    Estado del jugador:
    - Salud: {player_state['health']}
    - Inventario: {player_state['inventory']}
    - Misiones activas: {player_state['quests']}
    
    Estado del mundo:
    - Área actual: {world_state['current_area']}
    - Eventos pasados: {world_state['events']}
    
    El jugador pregunta: "{query}"
    
    Responde de manera épica, pero estructurada. Proporciona la respuesta en un formato JSON que incluye:
    1. Un campo "narrative" con la narración épica de lo que sucede.
    2. Un campo "player_updates" con los cambios al estado del jugador, como salud, inventario o misiones.
    3. Un campo "world_updates" con los cambios al estado del mundo, como nueva ubicación o eventos adicionales.
    4. Un campo "options" con las posibles decisiones del jugador, en formato de lista. *ESTA NO SE PUEDE OMITIR NUNCA)
    
    IMPORTANTE SEGUIR LA ESTRUCTURA DEL JSON no LO HAGAS CON FORMATOK MARKDOWN, TIENE QUE SER JSON PURO
    Asegúrate de que el JSON esté bien formado y siempre incluyas opciones posibles al jugador. Aquí tienes un ejemplo del formato esperado:
    TOdos los objetos tienen que crearse con sus respectivos valores, ninguno puede estar vacio. Si no hay inventate unos de acuerdo al contexto
    Tampoco puedes agregar nuevos  objetos, se debe respetar exlusivamente la siguiente estructura del JSON
    Tiene que existir por lo menos una opcion disponible
    String must be wrapped in double cuotes
    {{
        "narrative": "Encuentras una cueva misteriosa y oscura...",
        "player_updates": {{
            "health": -10,
            "inventory": ["antorcha"]
        }},
        "world_updates": {{
            "current_area": "Cueva Oscura",
            "events": ["El jugador encuentra una cueva misteriosa."]
        }},
        "options": [
            "Explorar la cueva más a fondo.",
            "Regresar al pueblo para prepararte mejor.",
            "Buscar alguna pista en el bosque."
        ]
    }}
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
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model1 = genai.GenerativeModel("gemini-pro")
        response = model1.generate_content(prompt)

        # Intentar cargar el JSON de la respuesta
        try:
            response_json = json.loads(response.text.replace("'", '"'))
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



# Ejemplo de uso
##query = "¿Qué sucede si decido explorar la cueva?"
#print(query_dm_system_with_personality(query, player_state, world_state))

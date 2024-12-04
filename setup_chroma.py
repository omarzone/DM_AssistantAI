import os
import chromadb
from langchain.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Configura la clave API de Google Gemini
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = input("Please enter your Google API key: ")

# Cargar el PDF y extraer el texto
loader = PyPDFLoader("data/manual.pdf")
documents = loader.load()
texts = [doc.page_content for doc in documents]

# Configurar el modelo de embeddings de Google
embeddings_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
embedding_dimension = 384  # Dimensión esperada para este modelo

# Función para obtener embeddings del texto
def get_embeddings(texts):
    """Obtiene las embeddings usando Google Generative AI"""
    embeddings = embeddings_model.embed_documents(texts)
    return embeddings

# Crear cliente persistente de ChromaDB y colección
persist_directory = "db"  # Directorio donde se guardarán los datos persistentes
chroma_client = chromadb.PersistentClient(path=persist_directory)  # Asegúrate de usar la ruta correcta

# Crear colección o acceder a una existente
collection = chroma_client.create_collection(name="dungeon_master_collection")

# Guardar los embeddings en ChromaDB
def store_embeddings_in_chroma(texts, embeddings):
    """Guarda los documentos y embeddings en ChromaDB"""
    for idx, doc in enumerate(documents):
        collection.add(
            ids=[str(idx)],  # Usamos el índice como ID único
            documents=[doc.page_content],
            metadatas=[{"page": idx}],
            embeddings=[embeddings[idx]]
        )


# Obtener embeddings y guardarlos en ChromaDB
embeddings = get_embeddings(texts)
store_embeddings_in_chroma(texts, embeddings)

print("Embeddings guardados en ChromaDB con éxito.")

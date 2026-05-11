# RAG Pokemon - Practica

## Que es esto?

Un sistema de Preguntas y Respuestas (RAG) sobre datos de Pokemon. Combina:

- **Agente**: Procesa preguntas e intenciones del usuario
- **RAG (Retrieval-Augmented Generation)**: Busca informacion relevante en una base de datos vectorizada
- **Flask API**: Expone todo como endpoints HTTP

## Estructura

```
agente/
  ├── agente_pokemon.py          # Agente que procesa preguntas
  ├── rag_pokemon/
  │   ├── rag_pokemon.py         # Sistema RAG core
  │   ├── crear_vectorstore.py   # Script para generar embeddings
  │   ├── vectorstore/           # Base de datos FAISS (1025 Pokemon)
  │   └── data/
  │       └── dataSetFinal.xlsx  # Datos originales

app/
  └── routes/
      └── pokemon_routes.py      # Endpoints HTTP para RAG
```

## Como funciona

### 1. Creacion del Vectorstore

El Excel con datos Pokemon se convierte en embeddings y se guarda en FAISS:

```bash
python agente/rag_pokemon/crear_vectorstore.py
```

Esto:
- Carga 1025 Pokemon del Excel
- Crea embeddings semanticos con `sentence-transformers`
- Guarda vectorstore comprimido

### 2. Consultas

El agente puede procesar tres tipos de preguntas:

**A) Busqueda por nombre**
```
"quien es pikachu"
"dime sobre charizard"
```

**B) Busqueda por tipo**
```
"pokemon de tipo fuego"
"cuales son los acuaticos"
```

**C) Consulta general/semantica**
```
"que pokemon tiene mejor defensa"
"cuales son legendarios"
"pokemon con mas HP"
```

### 3. API REST

**Iniciar servidor:**
```bash
python run.py
# Abierto en http://127.0.0.1:5000
```

**Endpoints:**

```
POST /pokemon/consultar
Content-Type: application/json

{
  "pregunta": "quien es pikachu"
}

Response:
{
  "ok": true,
  "pregunta": "quien es pikachu",
  "respuesta": "Encontre a Pikachu",
  "tipo": "busqueda_nombre",
  "documentos": [...]
}
```

```
GET /pokemon/tipo/<tipo>

/pokemon/tipo/fuego
/pokemon/tipo/agua
/pokemon/tipo/psiquico

Response:
{
  "ok": true,
  "tipo": "fuego",
  "respuesta": "Encontre 5 Pokemon de tipo 'fuego'",
  "documentos": [...]
}
```

```
GET /pokemon/buscar/<nombre>

/pokemon/buscar/Pikachu
/pokemon/buscar/Dragonite

Response:
{
  "ok": true,
  "nombre": "Pikachu",
  "respuesta": "Encontre a Pikachu",
  "documento": {...}
}
```

## Archivo de Test

Hay un `test_api.py` que prueba todos los endpoints:

```bash
python test_api.py
```

## Dependencias Principales

- `langchain` + `langchain-community` - Framework RAG
- `sentence-transformers` - Embeddings semanticos
- `faiss-cpu` - Base de datos vectorial
- `pandas` + `openpyxl` - Lectura de Excel
- `flask` - API web

## Datos del Excel

26 columnas:
- Basicos: id, Name, Generation
- Fisicos: Height, Weight
- Stats: HP, Attack, Defense, Sp.Atk, Sp.Def, Speed
- Tipos: Type_1, Type_2
- Clasificaciones: Is_Legendary, Is_Mythical, Is_Pseudo_Legendary
- Otros: Capture_Rate, Base_Happiness, Abilities, Egg_Groups, etc.

## Como extender

1. **Añadir mas datos** - Modifica Excel y regenera vectorstore
2. **Cambiar modelo embeddings** - En `HuggingFaceEmbeddings(model_name="...")`
3. **Integrar con LLM** - Añade OpenAI/LLaMA para generar respuestas mejores
4. **Frontend** - Crea HTML/JS que llame a los endpoints

## Errores Comunes

**"Vectorstore no encontrado"**
→ Ejecuta primero `python agente/rag_pokemon/crear_vectorstore.py`

**"No encontre informacion"**
→ La pregunta es muy especifica. Intenta buscar por tipo o nombre

**LangChainDeprecationWarning**
→ Aviso normal, no afecta funcionamiento

# Chatbot Pokémon con IA + RAG + Escalado a Humano

## ¿Qué es este proyecto?

Este proyecto es una práctica de **chatbot con IA y RAG** usando un dataset de Pokémon en formato Excel.

El sistema permite hacer preguntas sobre Pokémon y responde usando los datos del dataset. Además, incluye una lógica de decisión para saber cuándo puede responder automáticamente y cuándo debe escalar la consulta a un agente humano.

El proyecto combina:

- **Agente conversacional**: analiza la intención del usuario.
- **Preprocesado**: limpia y normaliza la pregunta.
- **RAG semántico**: recupera información relevante usando embeddings y FAISS.
- **Dataset Pokémon**: fuente principal de conocimiento.
- **Pipeline de respuesta**: decide cómo responder según la pregunta.
- **Escalado a humano**: si no hay información suficiente, registra la consulta y avisa al usuario.

---

## Objetivo de la práctica

El objetivo es construir un sistema que pueda:

- Responder preguntas generales sobre Pokémon.
- Consultar información específica desde un dataset.
- Usar embeddings y FAISS para recuperación semántica.
- Aplicar reglas de validación.
- Escalar preguntas que no pueda resolver con seguridad.
- Registrar los casos escalados.

---

## Estructura del proyecto

```text
rag_pokemon/
│
├── data/
│   └── dataSetFinal.xlsx
│
├── vectorstore/
│   ├── pokemon.index
│   └── chunks.txt
│
├── agente_pokemon.py
├── crear_faiss.py
├── rag_faiss_pokemon.py
├── pipeline_pokemon.py
└── logs_escalado.txt

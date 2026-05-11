import requests
import json

print("=" * 60)
print("TEST 1: Consulta General")
print("=" * 60)
resp = requests.post('http://127.0.0.1:5000/pokemon/consultar', json={'pregunta': 'quien es pikachu'})
data = resp.json()
print(f"Pregunta: {data['pregunta']}")
print(f"Respuesta: {data['respuesta']}")
print(f"Tipo: {data['tipo']}\n")

print("=" * 60)
print("TEST 2: Busqueda por Tipo")
print("=" * 60)
resp = requests.get('http://127.0.0.1:5000/pokemon/tipo/fuego')
data = resp.json()
print(f"Tipo: {data['tipo']}")
print(f"Encontrados: {len(data['documentos'])} Pokemon")
if data['documentos']:
    for i, doc in enumerate(data['documentos'], 1):
        print(f"  {i}. {doc['nombre']} (Tipo: {doc['tipo']})")
print()

print("=" * 60)
print("TEST 3: Buscar por Nombre")
print("=" * 60)
resp = requests.get('http://127.0.0.1:5000/pokemon/buscar/Charizard')
data = resp.json()
print(f"Nombre: {data['nombre']}")
print(f"Respuesta: {data['respuesta']}")
if data['documento']:
    doc = data['documento']
    print(f"ID: {doc['id']}, Tipo: {doc['tipo']}")
print()

print("=" * 60)
print("TEST 4: Consulta Semantica Compleja")
print("=" * 60)
resp = requests.post('http://127.0.0.1:5000/pokemon/consultar', 
                     json={'pregunta': 'que pokemon tiene mejor defensa'})
data = resp.json()
print(f"Pregunta: {data['pregunta']}")
print(f"Tipo: {data['tipo']}")
print(f"Respuesta: {data['respuesta'][:500]}")

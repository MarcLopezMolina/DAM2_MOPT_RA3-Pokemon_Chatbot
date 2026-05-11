# Agente basico demo

Ejemplo minimo para entender las piezas principales de un agente:

- `estado`: memoria que se conserva entre mensajes.
- `analisis de intencion`: clasificacion simple del mensaje del usuario.
- `artefacto`: resultado estructurado que el agente genera.

Ejecutar:

```powershell
python agente_basico.py
```

Version Flask:

```powershell
cd agente_basico_demo
..\venv\Scripts\python.exe agente_flask.py
..\venv\Scripts\python.exe cliente_flask.py
```

- Agente API: `http://127.0.0.1:5100`
- Cliente demo: `http://127.0.0.1:5101`

Importante: el cliente llama al agente por HTTP. Si solo arrancas `cliente_flask.py`
sin arrancar `agente_flask.py`, el cliente abrira, pero al enviar un mensaje mostrara
un error de conexion.

Flujo esperado:

1. El usuario pega una funcion Python.
2. El agente detecta intencion `python_function`.
3. Guarda la funcion en estado.
4. Devuelve un artefacto de tipo `analysis`.
5. El usuario escribe `siguiente`.
6. El agente usa el estado y genera un artefacto de tipo `service`.

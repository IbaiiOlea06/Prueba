import os
import uuid
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import json
from typing import Annotated
from fastapi import Body, Cookie,Response,Depends,FastAPI
import pathlib
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


cliente=None
gemma=None
modelo=None
dict_funciones=None
system_instruction=None

class Peticion(BaseModel):
    text:str

class Respuesta(BaseModel):
    text:str

##Variables Globales
API_KEY=None
MODEL_ID=None

##Inicializacion
@asynccontextmanager
async def inicializacion(app:FastAPI):
    ##Objetos necesarios para conectar a mongo db
    global cliente ##Cliente
    global gemma ##Objeto que representa al modelo
    global modelo ##nombre del modelo
    global dict_funciones ##un diccionario donde: key;nombre de funcion,                        
    global system_instruction 
    
    #Carga el fichero .env
    load_dotenv()

    #cargamos la version del modelo y la clave de la API de Google
    api_key=os.getenv('GEMINI_API_KEY')
    gemma=genai.Client(api_key=api_key)

    app.state.contents=dict()

    modelo=os.getenv('GEMINI_MODEL_ID')
    system_instruction="""
    Eres el asitente de la guia sobre Beasain.
    

Utiliza la funcion, no pidas mas informacion ni otras explicaciones. 
Para invocar a una funcion DEBERAS usar el siguiente formato:
{"name":nombre_funcion,"args":{diccionario con nombres y valores de los argumentos de la funcion}}}

NO DEBERAS incluir ningun otro texto adicional, ni marcas de formato.

[
    {"name": "consultar_manual",
     "descripcion": "Utilizar esta funcion acerca de informacion sobre Beasain",
     "args":{
     "pregunta":str/*Texto de la consulta a realizar*/
     }
     }
]
"""
    
    #Configurar clave
    #genai.configure(api_key=API_KEY)
    yield
    cliente=None
    
    

def compactar_prompt(sesion,top):
   
    app.state.contents[sesion]=app.state.contents[sesion][top:len(app.state.contents[sesion])]

def resumir(session_id):
    texto_resumen="Resume la interaccion hasta el momento, de forma esquematica en menos de 500 tokens"
   
    app.state.contents[session_id].append(types.Content(role="user",parts=[types.Part(text=texto_resumen)]))
    resumen=gemma.models.generate_content(model=modelo,parts=[app.state.contents[session_id]])
   
    app.state.contents[session_id].clear()
    app.state.contents[session_id].appends(types.Content(role="model",parts=[types.Part(text=resumen)]))

##Iniciarlo
app=FastAPI(lifespan=inicializacion)

@app.post('/asistente/')
def post_peticion(response:Response,p:Annotated[Peticion|None,Body()]=None,session_id:Annotated[str|None, Cookie()]=None):   ##Validacion para las entradas:Annotated
    
    if session_id is None or not session_id in app.state.contents.keys():
        session_id=str(uuid.uuid4())
        response.set_cookie(key="session_id",value=session_id,secure=False)
        app.state.contents.update({session_id:[]})
        
    prompt=f"[SYSTEM:{system_instruction}]\n\n"
    prompt+=p.text
   
    parts=[types.Part(text=prompt)]
    app.state.contents[session_id].append(types.Content(
            role="user",parts=parts
        )
    )
    resp=gemma.models.generate_content(model=modelo, contents=app.state.contents[session_id])
   
    try:##si tratar el json no da error.
        limpia=resp.text.strip("`").replace("json","").replace("'","\"")##limpiar la respuesta
       
        function_call=json.loads(limpia)##cargar el json en diccionario
        funcion=function_call["name"]
        args=function_call["args"]
       
        if(funcion=="consultar_manual"):
            fichero=pathlib.Path("informacion.pdf")
            datos=fichero.read_bytes()
            # Attach PDF and ask for a direct answer
            pdf_parts=[types.Part().from_bytes(data=datos,mime_type='application/pdf'),
                       types.Part(text=p.text+"\nResponde a la pregunta anterior usando solo el documento adjunto. Da una respuesta clara y natural, no en formato de función ni JSON.")]
            app.state.contents[session_id].append(types.Content(role='user',parts=pdf_parts))
            resp=gemma.models.generate_content(model=modelo, contents=app.state.contents[session_id])
           
            # Post-process as with other functions
            respuesta = resp.text
           
            app.state.contents[session_id].append(types.Content(role="model",parts=[types.Part(text=respuesta)]))
            mensaje_usuario = f"[RESULTADO]:{respuesta}. Explica estos resultados al cliente de forma informativa. Utiliza la informacion que encuentres en el documento."
            app.state.contents[session_id].append(types.Content(role="user",parts=[types.Part(text=mensaje_usuario)]))
            respuesta_definitiva = gemma.models.generate_content(model=modelo, contents=app.state.contents[session_id])
            
            if(respuesta_definitiva.usage_metadata.total_token_count>12000):
                resumir(session_id)
            return {"text": respuesta_definitiva.text}
        respuesta=dict_funciones[funcion](**args)##llamar a funcion para recuperar los resultados
       
        app.state.contents[session_id].append(types.Content(role="model",parts=[types.Part(text=limpia)]))##concatenar el filtro generado al historias (contents)
        str_repuesta=json.dumps(respuesta,ensure_ascii=False)##convertir respuesta en diccionario (json -> diccionario)
        mensaje_usuario=f"[RESULTADO]:{str_repuesta}.Explica estos resultados al cliente de forma informativa. Utiliza la informacion que encuentres en el documento."
        app.state.contents[session_id].append(types.Content(role="user",parts=[types.Part(text=mensaje_usuario)]))##concatenar resultado a promp definitivo
        respuesta_definitiva=gemma.models.generate_content(model=modelo,contents=app.state.contents[session_id])##generar respuesta definitiva a partir de promp definitivo
       
        if(respuesta_definitiva.usage_metadata.total_token_count>12000):
            resumir(session_id)
        return{"text":respuesta_definitiva.text}
    except json.JSONDecodeError as exccon: ##si la respuesta no se puede tratar como json
      
        if(resp.usage_metadata.total_token_count>12000):
            resumir(session_id)
        return{"text":resp.text}


##@app.post("/chat/")
##def post_peticion(peticion:Peticion):
##    resp=app.state.model.models.generate_content(model=MODEL_ID,contents=peticion.text)
##    return {"text":resp.text}
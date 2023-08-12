from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Request,Form
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict,List

import json
app = FastAPI()


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now() 
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(JSON.stringify(input.value))
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # add dictionaries for private( 1 on 1 chat) and group chat
        # eg. 
        # self.private_rooms: Dict[str,List[WebSocket]] = {}   limit this to 2 websockets in the list
        # self.private_rooms:Dict[str,List[str],List[WebSocket]] = {}  add the second [] for db storing ids
        self.private_rooms:Dict[str,List[WebSocket]] = {}
        self.group_rooms:Dict[str,List[str],List[WebSocket]] = {}
  

    async def connect(self,websocket: WebSocket,room_type:str,room_id:str): # receive the room id and the client id and add them to their specified room
        await websocket.accept()
        # try:
        #     self.private_rooms[room_id]
            
        # except KeyError:
        #     print("Room does not exist")
        
        if room_type == 'private':
            if  room_id in self.private_rooms:
                self.private_rooms[room_id].append(websocket)
            else:
                self.private_rooms[room_id] = [websocket]
                
        else:
            self.group_rooms['room_id'] = [websocket]
        # self.active_connections.append(websocket)
        
    # Do the new room thing for persintence storage with database
    async def new_room(self,client_id:str,room_type:str,room_id:str,websocket:WebSocket):
        # use client ids with persitence(db) coz here they'll be refreshed so test by limiting adding in private to 2 users
        if room_type == 'PRIVATE':
             self.private_rooms[room_id] = [[client_id],[websocket]]
        else:
            self.group_rooms[room_id] = [[client_id],[websocket]]
            
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    # test function
    async def send_group_message(self,websocket: WebSocket,room_id:str, message: str):
        room = self.private_rooms[room_id]
        for connection in room:
            await connection.send_text(message)

    async def broadcast(self, message: str,websocket:WebSocket):
        for connection in self.active_connections:
            if connection != websocket:
                await connection.send_text(message)
                 

manager = ConnectionManager()

templates = Jinja2Templates(directory='templates')

# @app.get("/")
# async def index(request:Request):
#     # print("PARAMS:",request.path_params)
#     return templates.TemplateResponse('index.html',{'request':request})
 
@app.get("/")
async def room(request:Request):
    return templates.TemplateResponse("room.html",{"request": request})

@app.post("/messages")
async def messages(request:Request):
    form_data = await request.form()
    # print("FORM DATA:",form_data)
    return templates.TemplateResponse("test.html",{"request": request,"room_id":form_data.get('room_id')})

@app.websocket("/ws/{room_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket,room_id:str, client_id: int):
    await manager.connect(websocket,'private',room_id) # here get the room id and the client id
    try: 
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
            await manager.send_group_message(websocket,room_id,data['message'])
            # await manager.send_personal_message(f"You wrote: {json.dumps(data)}", websocket)
            # await manager.broadcast(f"Client #{client_id} says: {json.dumps(data)}",websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat",websocket)

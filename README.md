# How does the Streamlit backend work (WIP)

## This codebase has modificiations in it to experiment with Streamlit - please be aware of that.

- Install instructions:
  https://github.com/streamlit/streamlit/wiki/Contributing

This repo is a modified version that allows to enter the application through cli.py and attach a debugger in VS Code. It also whitelists all domains for debugging purposes to make it easier to just connect a websocket client from a different port/domain:

server_util.py

```
def is_url_from_allowed_origins(url):
```

server.py

```
def check_origin(self, origin):
        """Set up CORS."""
        #return super().check_origin(origin) or is_url_from_allowed_origins(origin)
        return True
```

## To get started VS Code just add your virtualenviornment and run from cli.py

```
{
    "python.pythonPath": "yourvirtualenv"
}

```

There has to be a seperate Nodejs server on 3000 running to render the content on the frontend

## Alterations and Flow

- At the fundamental level, the streamlit server is a tornado backend that spawns one main thread which runs an event loop. It consumes a python script including all its modules and propagates this information into the higher level react components which consume it and render it into the browser. The interesting thing is that internally Streamlit diffs the data it sends, so it can understand what has changed or not internally (it runs a script from top to bottom with every run, yet through the diffing / delta generation it becomes efficent doing this)

Important building blocks (for my usecase):

- A server object (server.py)
- A session per user (report_session.py)
- Thread(s) within the event loop per user?
- A Queue
- Scripts that process the queue
- Filewatcher (Local_sources_watcher.py / event_based_file watcher.py)

### Main Entry

bootstrap.py

```
def run(script_path, command_line, args):
 ....

server = Server(ioloop, script_path, command_line)
    server.start(_on_server_start)

    # (Must come after start(), because this starts a new thread and start()
    # may call sys.exit() which doesn't kill other threads.
    server.add_preheated_report_session()

    # Start the ioloop. This function will not return until the
    # server is shut down.
    ioloop.start()
```

A main thread has an event loop that continously runs and checks for pending messages in the message queue.

server.py

```
@tornado.gen.coroutine
    def _loop_coroutine(self, on_started=None):
```

These messages are of protobuf format and get passed along via websocket. Each message is bound to a session. In fact each session runs in its own thread. The following snippet deals with the messages and consumes them within the session object.

server.py

```
 if msg_type == "cloud_upload":
        yield self._session.handle_save_request(self)
    elif msg_type == "rerun_script":
        self._session.handle_rerun_script_request(msg.rerun_script)
    elif msg_type == "clear_cache":
        self._session.handle_clear_cache_request()
    elif msg_type == "set_run_on_save":
        self._session.handle_set_run_on_save_request(msg.set_run_on_save)
    elif msg_type == "stop_report":
        self._session.handle_stop_script_request()
    elif msg_type == "close_connection":
        if config.get_option("global.developmentMode"):
            Server.get_current().stop()
        else:
            LOGGER.warning(
                "Client tried to close connection when "
                "not in development mode"
            )
    else:
        LOGGER.warning('No handler for "%s"', msg_type)
```

server.py

```
 for session_info in session_infos:
    if session_info.ws is None:
        # Preheated.
        continue
    msg_list = session_info.session.flush_browser_queue()
    for msg in msg_list:
        try:
            jsonObj = MessageToJson(msg)
            print("Send: " + session_info.session.id)
            print("Msg: " + jsonObj)
            self._send_message(session_info, msg)
        except tornado.websocket.WebSocketClosedError:
            self._close_report_session(session_info.session.id)
        yield
    yield
```

The aformentioned event loop runs a continous loop that checks on all connected sessions and checks if any messages are pending. If there are messages, they get processed.

The message processing happens in report_session.py

### Reruns

There are 2 scenarios in which Streamlit triggers a rerun:

- A widget in the application updates (e.g. a slider or button gets pressed)
- The observed file or one of its associated files / packages changes

If multiple user observe the same source file, changes get pushed to all clients subscribed to that source file.

If a user updates his individual widget state, this only updates his session and not anyones elses.

This generates an interesting behavior that can be applicable for a few uses cases, however there are a few caveats.

### Periodic reruns or event driven reruns

https://discuss.streamlit.io/t/live-plot-from-a-thread/247/2
https://gist.github.com/Ghasel/41d4854722f49ad0fc9a6ad8a49af3da

An ideal implementation however would be to have a pure event driven trigger as an endpoint that can trigger a rerun for a specific or for all existing session_ids to make this efficent.

### Caveats

- Streamlit by default doesnt have state. Everytime we rerun the application the state is reset (due to the Top to bottom script evaluation).

- If a user refreshes a session, this essentially creates a new session (session_id) within Streamlit

In order to be able to use this in more complex scenarios it makes sense to gain more control

- over details about how reruns happen (pass them on the server level based on ID / widgets)
- if states can get updated programmatically by fetching a session through a 3rd party and establishing a communication channel
- implementing proper session / cookie based auth and binding this to an internal session id

### Getting the session object inside a streamlit app
Currently, we use custom code to get the streamlit session object. It is defined in the sessionx.py file in the /hello folder. 
Example:

```
sid = sessionx.get_session_id()
```

### Reading the sessionid cookie delivered by the learning_azure backend
In the streamlit REST request handler, all we need to do is read the sessionid cookie
Example
```
session_cookie = self.get_cookie("sessionid")
```
If the cookie doesn't exist, session_cookie will have the value `None`

### Custom endpoints
We have added a /gremloon request handler, defined in the /server/gremloon.py file.
It is using the tornado API and we are adding that handler in the server.py file.

When you send a GET request to /gremloon, that's when the `get` method gets called.

import sys
import inspect
from google.adk.agents.callback_context import CallbackContext

with open('callback_context_src.txt', 'w') as f:
    f.write(inspect.getsource(CallbackContext))

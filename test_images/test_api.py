import numpy as np
import json
from PIL import Image
import requests
import base64
from time import time

# Read Image
with open('car.jpg', 'rb') as img_file:
    img_str = base64.b64encode(img_file.read()).decode('utf-8')

# Call the API
API_URL = "PUT YOUR API URL HERE"

t1 = time()
response = requests.post(API_URL, json=img_str)

print('Status Code:', response.status_code)
print('Time Taken:', time() - t1)
print('Response:\n', response.json())

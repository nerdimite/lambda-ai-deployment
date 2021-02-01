import numpy as np
import json
import os
from PIL import Image
import base64
import io
import torch
from torchvision import models, transforms
import torch.nn.functional as F

def read_image(img_string: str) -> Image.Image:
    """Returns the PIL Image object from base64 string.

    Args:
        img_string (str): base64 string of the input image.

    Returns:
        Image.Image: PIL Image object.

    """
    # If base64 meta data is present in the string, remove it
    if len(img_string.split(',')) > 1:
        img_string = img_string.split(',', 1)[1]

    # Decode the string and read the image
    img_string = base64.b64decode(img_string)
    buffer = io.BytesIO(img_string)
    img = Image.open(buffer).convert('RGB')

    return img

# MODEL_DIR in EFS
MODEL_DIR = os.getenv("MODEL_DIR")

# Loading the Model
model = models.resnet34(pretrained=False)
model.load_state_dict(torch.load(os.path.join(MODEL_DIR, "resnet34-333f7ec4.pth")))
model.eval()

# Creating the transformations
normalize = transforms.Normalize(
    mean=[0.485, 0.456, 0.406],
    std=[0.229, 0.224, 0.225]
)
transformations = transforms.Compose([transforms.Resize(224),
                                      transforms.CenterCrop(224),
                                      transforms.ToTensor(),
                                      normalize])

# Loading the ImageNet class index map
with open("imagenet_class_index.json", 'r') as f:
    label_map = json.loads(f.read())

def predict(img: Image.Image) -> dict:
    """Makes prediction on an input image returns a results dictionary

    Args:
        img (Image.Image): Input image

    Returns:
        dict: Top 3 predictions

    """
    # Preproces the image
    img_tensor = transformations(img).unsqueeze(0)
    pred = F.softmax(model(img_tensor), dim=1).squeeze(0)

    # Get top 3 predictions
    topk_vals, topk_idxs = torch.topk(pred, 3)

    output = {
        'prediction': label_map[str(topk_idxs[0].item())][1]
    }

    for i in range(3):
        label = label_map[str(topk_idxs[i].item())][1]
        prob = round(topk_vals[i].item(), 4)
        output[label] = prob

    return output


def lambda_handler(event, context):
    """Lambda Handler Function"""
    print(event)
    try:
        body = json.loads(event['body'])
    except:
        body = event['body']

    image = read_image(body)
    result = predict(image)

    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }

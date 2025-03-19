import boto3
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware  # Keep CORS for frontend

app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dev.d3czb7uix4xpb0.amplifyapp.com/"],  # Replace with your Amplify URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('Workouts')

class Workout(BaseModel):
    type: str
    duration: int
    calories: int

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.post("/workouts", response_model=Workout)
def log_workout(workout: Workout):
    table.put_item(Item=workout.dict())
    return workout

@app.get("/workouts", response_model=List[Workout])
def get_workouts():
    response = table.scan()
    return response.get('Items', [])

@app.get("/insights")
def get_insights():
    response = table.scan()
    items = response.get('Items', [])
    total_calories = sum(item['calories'] for item in items)
    return {"total_calories": total_calories, "message": f"You've burned {total_calories} calories!"}
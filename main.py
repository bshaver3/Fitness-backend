import boto3
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from datetime import datetime, timezone
from auth import get_current_user_id

app = FastAPI()

# Add CORS - Restrict to authorized origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://main.d20be68lg9xm5h.amplifyapp.com"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('Workouts')
profile_table = dynamodb.Table('UserProfiles')
planned_workouts_table = dynamodb.Table('PlannedWorkouts')

class Workout(BaseModel):
    id: str | None = None
    user_id: str | None = None
    type: str
    duration: int
    calories: int
    timestamp: str | None = None

class Profile(BaseModel):
    user_id: str = "default"  # Default user ID for now
    height_feet: int | None = None
    height_inches: int | None = None
    current_weight: int | None = None
    age: int | None = None
    sex: str | None = None
    goals: str | None = None
    target_weight: int | None = None
    weekly_target_type: str | None = None
    weekly_target_value: int | None = None
    goal_deadline: str | None = None
    workout_frequency: int | None = None  # Times per week currently working out
    activity_level: str | None = None  # Daily activity level
    gym_experience: str | None = None  # Experience level in gym

class PlannedWorkout(BaseModel):
    id: str | None = None
    user_id: str = "default"
    workout_type: str
    planned_date: str  # YYYY-MM-DD format
    planned_time: str | None = None  # HH:MM format (24-hour)
    planned_duration: int
    notes: str | None = None
    created_at: str | None = None
    completed: bool = False
    completed_workout_id: str | None = None

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.post("/workouts", response_model=Workout)
def log_workout(workout: Workout, user_id: str = Depends(get_current_user_id)):
    if not workout.id:
        workout.id = str(uuid4())
    if not workout.timestamp:
        workout.timestamp = datetime.now(timezone.utc).isoformat()
    workout.user_id = user_id
    table.put_item(Item=workout.dict())
    return workout

@app.get("/workouts", response_model=List[Workout])
def get_workouts(user_id: str = Depends(get_current_user_id)):
    response = table.scan(
        FilterExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    return response.get('Items', [])

@app.get("/insights")
def get_insights(user_id: str = Depends(get_current_user_id)):
    response = table.scan(
        FilterExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    items = response.get('Items', [])
    total_calories = sum(item['calories'] for item in items)
    return {"total_calories": total_calories, "message": f"You've burned {total_calories} calories!"}

@app.post("/profile", response_model=Profile)
def save_profile(profile: Profile, user_id: str = Depends(get_current_user_id)):
    profile.user_id = user_id
    profile_table.put_item(Item=profile.dict())
    return profile

@app.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    response = profile_table.get_item(Key={'user_id': user_id})
    return response.get('Item', {})

@app.get("/health")
def health():
    return {"ok": True}

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: str, user_id: str = Depends(get_current_user_id)):
    # Verify ownership before deleting
    response = table.get_item(Key={'id': workout_id})
    item = response.get('Item')
    if not item or item.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Workout not found")
    table.delete_item(Key={'id': workout_id})
    return {"message": f"Workout {workout_id} deleted."}

@app.post("/planned-workouts", response_model=PlannedWorkout)
def create_planned_workout(workout: PlannedWorkout, user_id: str = Depends(get_current_user_id)):
    if not workout.id:
        workout.id = str(uuid4())
    if not workout.created_at:
        workout.created_at = datetime.now(timezone.utc).isoformat()
    workout.user_id = user_id
    planned_workouts_table.put_item(Item=workout.dict())
    return workout

@app.get("/planned-workouts", response_model=List[PlannedWorkout])
def get_planned_workouts(user_id: str = Depends(get_current_user_id)):
    response = planned_workouts_table.scan(
        FilterExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    items = response.get('Items', [])
    # Sort by planned_date
    items.sort(key=lambda x: x.get('planned_date', ''))
    return items

@app.get("/planned-workouts/{workout_id}")
def get_planned_workout(workout_id: str, user_id: str = Depends(get_current_user_id)):
    response = planned_workouts_table.get_item(Key={'id': workout_id})
    item = response.get('Item')
    if not item or item.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    return item

@app.put("/planned-workouts/{workout_id}", response_model=PlannedWorkout)
def update_planned_workout(workout_id: str, workout: PlannedWorkout, user_id: str = Depends(get_current_user_id)):
    # Verify ownership
    response = planned_workouts_table.get_item(Key={'id': workout_id})
    existing = response.get('Item')
    if not existing or existing.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    workout.id = workout_id
    workout.user_id = user_id
    planned_workouts_table.put_item(Item=workout.dict())
    return workout

@app.delete("/planned-workouts/{workout_id}")
def delete_planned_workout(workout_id: str, user_id: str = Depends(get_current_user_id)):
    # Verify ownership before deleting
    response = planned_workouts_table.get_item(Key={'id': workout_id})
    item = response.get('Item')
    if not item or item.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    planned_workouts_table.delete_item(Key={'id': workout_id})
    return {"message": f"Planned workout {workout_id} deleted."}
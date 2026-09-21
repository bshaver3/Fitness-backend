import json
import os
import re
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from auth import get_current_user_id

app = FastAPI()

TRUE_VALUES = {"1", "true", "yes", "on"}
LOCAL_MOCK = os.environ.get("LOCAL_MOCK", "").strip().lower() in TRUE_VALUES
MOCK_DATA_FILE = Path(os.environ.get("MOCK_DATA_FILE", "mock-data.json"))


# In-memory rate limiter: 100 requests per minute per IP
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else (request.client.host if request.client else "unknown")
        )

        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > 1_048_576:  # 1 MB limit
            return JSONResponse(
                status_code=413, content={"detail": "Request body too large"}
            )

        now = time.time()
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < self.window_seconds
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        self.requests[client_ip].append(now)
        return await call_next(request)


app.add_middleware(RateLimitMiddleware)

# Add CORS - Restrict to authorized origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://main.d20be68lg9xm5h.amplifyapp.com",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


class JsonTable:
    def __init__(self, file_path: Path, collection: str, key_name: str):
        self.file_path = file_path
        self.collection = collection
        self.key_name = key_name

    def _default_data(self):
        return {
            "workouts": [],
            "profiles": [],
            "planned_workouts": [],
        }

    def _load(self):
        if not self.file_path.exists():
            return self._default_data()

        with self.file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        defaults = self._default_data()
        defaults.update(data)
        return defaults

    def _save(self, data):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, sort_keys=True)

    def _matches_key(self, item, key):
        return all(item.get(field) == value for field, value in key.items())

    def put_item(self, Item):
        data = self._load()
        items = data[self.collection]
        key = {self.key_name: Item[self.key_name]}
        existing_index = next(
            (index for index, item in enumerate(items) if self._matches_key(item, key)),
            None,
        )

        if existing_index is None:
            items.append(Item)
        else:
            items[existing_index] = Item

        self._save(data)
        return {}

    def get_item(self, Key):
        data = self._load()
        item = next(
            (item for item in data[self.collection] if self._matches_key(item, Key)),
            None,
        )
        return {"Item": item} if item else {}

    def scan(self, FilterExpression=None, ExpressionAttributeValues=None):
        data = self._load()
        items = list(data[self.collection])

        if ExpressionAttributeValues and ":uid" in ExpressionAttributeValues:
            user_id = ExpressionAttributeValues[":uid"]
            items = [item for item in items if item.get("user_id") == user_id]

        return {"Items": items}

    def delete_item(self, Key):
        data = self._load()
        data[self.collection] = [
            item for item in data[self.collection] if not self._matches_key(item, Key)
        ]
        self._save(data)
        return {}


if LOCAL_MOCK:
    table = JsonTable(MOCK_DATA_FILE, "workouts", "id")
    profile_table = JsonTable(MOCK_DATA_FILE, "profiles", "user_id")
    planned_workouts_table = JsonTable(MOCK_DATA_FILE, "planned_workouts", "id")
else:
    import boto3

    # DynamoDB setup
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table("Workouts")
    profile_table = dynamodb.Table("UserProfiles")
    planned_workouts_table = dynamodb.Table("PlannedWorkouts")

ALLOWED_WORKOUT_TYPES = {
    "running",
    "cycling",
    "swimming",
    "strength",
    "yoga",
    "hiit",
    "cardio",
    "walking",
    "basketball",
    "soccer",
    "tennis",
    "volleyball",
    "dancing",
    "rowing",
    "climbing",
    "boxing",
    "pilates",
    "other",
}

ALLOWED_SEX_VALUES = {"male", "female", "other", "prefer_not_to_say"}
ALLOWED_WEEKLY_TARGET_TYPES = {"workouts", "duration"}
ALLOWED_ACTIVITY_LEVELS = {
    "sedentary",
    "lightly_active",
    "moderately_active",
    "very_active",
    "extra_active",
}
ALLOWED_GYM_EXPERIENCE = {"beginner", "intermediate", "advanced"}


class Workout(BaseModel):
    id: str | None = None
    user_id: str | None = None
    type: str = Field(min_length=1, max_length=50)
    duration: int = Field(ge=1, le=600)
    calories: int = Field(ge=0, le=5000)
    timestamp: str | None = None

    @field_validator("type")
    @classmethod
    def validate_workout_type(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ALLOWED_WORKOUT_TYPES:
            raise ValueError("Invalid workout type")
        return cleaned


class Profile(BaseModel):
    user_id: str = "default"
    height_feet: int | None = Field(default=None, ge=1, le=8)
    height_inches: int | None = Field(default=None, ge=0, le=11)
    current_weight: int | None = Field(default=None, ge=50, le=1000)
    age: int | None = Field(default=None, ge=13, le=120)
    sex: str | None = None
    goals: str | None = Field(default=None, max_length=500)
    target_weight: int | None = Field(default=None, ge=50, le=1000)
    weekly_target_type: str | None = None
    weekly_target_value: int | None = Field(default=None, ge=1, le=100)
    goal_deadline: str | None = None
    workout_frequency: int | None = Field(default=None, ge=0, le=7)
    activity_level: str | None = None
    gym_experience: str | None = None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_SEX_VALUES:
            raise ValueError("Invalid sex value")
        return v

    @field_validator("weekly_target_type")
    @classmethod
    def validate_weekly_target_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_WEEKLY_TARGET_TYPES:
            raise ValueError("Invalid weekly target type")
        return v

    @field_validator("activity_level")
    @classmethod
    def validate_activity_level(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_ACTIVITY_LEVELS:
            raise ValueError("Invalid activity level")
        return v

    @field_validator("gym_experience")
    @classmethod
    def validate_gym_experience(cls, v: str | None) -> str | None:
        if v is not None and v not in ALLOWED_GYM_EXPERIENCE:
            raise ValueError("Invalid gym experience level")
        return v

    @field_validator("goal_deadline")
    @classmethod
    def validate_goal_deadline(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("goal_deadline must be in YYYY-MM-DD format")
        return v


class PlannedWorkout(BaseModel):
    id: str | None = None
    user_id: str = "default"
    workout_type: str = Field(min_length=1, max_length=50)
    planned_date: str  # YYYY-MM-DD format
    planned_time: str | None = None  # HH:MM format (24-hour)
    planned_duration: int = Field(ge=1, le=600)
    notes: str | None = Field(default=None, max_length=1000)
    created_at: str | None = None
    completed: bool = False
    completed_workout_id: str | None = None

    @field_validator("workout_type")
    @classmethod
    def validate_planned_workout_type(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ALLOWED_WORKOUT_TYPES:
            raise ValueError("Invalid workout type")
        return cleaned

    @field_validator("planned_date")
    @classmethod
    def validate_planned_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("planned_date must be in YYYY-MM-DD format")
        return v

    @field_validator("planned_time")
    @classmethod
    def validate_planned_time(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("planned_time must be in HH:MM format")
        return v


# Insights response models
class WeeklyProgress(BaseModel):
    current: int
    target: int
    unit: str
    percentage: float


class WeekComparison(BaseModel):
    this_week_workouts: int
    last_week_workouts: int
    this_week_duration: int
    last_week_duration: int
    this_week_calories: int
    last_week_calories: int
    workout_change_percent: float
    duration_change_percent: float
    calories_change_percent: float


class StreakInfo(BaseModel):
    current_streak: int
    longest_streak: int
    last_workout_date: str | None


class WorkoutFrequencyPoint(BaseModel):
    date: str
    count: int


class CaloriesOverTimePoint(BaseModel):
    date: str
    calories: int


class WorkoutTypeBreakdown(BaseModel):
    type: str
    count: int
    total_duration: int
    total_calories: int
    percentage: float


class ConsistencyStats(BaseModel):
    total_workouts: int
    total_duration: int
    total_calories: int
    avg_workouts_per_week: float
    avg_duration_per_workout: float
    most_active_day: str
    favorite_workout_type: str


class ComprehensiveInsights(BaseModel):
    weekly_progress: WeeklyProgress | None
    week_comparison: WeekComparison
    streak: StreakInfo
    workout_frequency: list[WorkoutFrequencyPoint]
    calories_over_time: list[CaloriesOverTimePoint]
    workout_type_breakdown: list[WorkoutTypeBreakdown]
    consistency_stats: ConsistencyStats


# Helper functions for insights calculations
def get_week_bounds(reference_date: datetime, weeks_ago: int = 0):
    """Get start (Sunday) and end (Saturday) of a week"""
    days_since_sunday = (reference_date.weekday() + 1) % 7
    week_start = reference_date - timedelta(days=days_since_sunday + (7 * weeks_ago))
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start, week_end


def convert_decimal(value):
    """Convert Decimal to int for JSON serialization"""
    if isinstance(value, Decimal):
        return int(value)
    return value


def calculate_weekly_progress(workouts: list, profile: dict) -> WeeklyProgress | None:
    """Calculate progress toward weekly goal"""
    target_type = profile.get("weekly_target_type")
    target_value = profile.get("weekly_target_value")

    if not target_type or not target_value:
        return None

    now = datetime.now(UTC)
    week_start, week_end = get_week_bounds(now)

    this_week = [w for w in workouts if week_start <= w["parsed_date"] <= week_end]

    if target_type == "workouts":
        current = len(this_week)
        unit = "workouts"
    else:
        current = sum(convert_decimal(w.get("duration", 0)) for w in this_week)
        unit = "minutes"

    target_value = convert_decimal(target_value)
    percentage = (current / target_value * 100) if target_value > 0 else 0

    return WeeklyProgress(
        current=current, target=target_value, unit=unit, percentage=min(percentage, 100)
    )


def calculate_week_comparison(workouts: list) -> WeekComparison:
    """Compare this week vs last week"""
    now = datetime.now(UTC)
    this_week_start, this_week_end = get_week_bounds(now, 0)
    last_week_start, last_week_end = get_week_bounds(now, 1)

    this_week = [
        w for w in workouts if this_week_start <= w["parsed_date"] <= this_week_end
    ]
    last_week = [
        w for w in workouts if last_week_start <= w["parsed_date"] <= last_week_end
    ]

    this_week_workouts = len(this_week)
    last_week_workouts = len(last_week)
    this_week_duration = sum(convert_decimal(w.get("duration", 0)) for w in this_week)
    last_week_duration = sum(convert_decimal(w.get("duration", 0)) for w in last_week)
    this_week_calories = sum(convert_decimal(w.get("calories", 0)) for w in this_week)
    last_week_calories = sum(convert_decimal(w.get("calories", 0)) for w in last_week)

    def calc_change(current, previous):
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100

    return WeekComparison(
        this_week_workouts=this_week_workouts,
        last_week_workouts=last_week_workouts,
        this_week_duration=this_week_duration,
        last_week_duration=last_week_duration,
        this_week_calories=this_week_calories,
        last_week_calories=last_week_calories,
        workout_change_percent=calc_change(this_week_workouts, last_week_workouts),
        duration_change_percent=calc_change(this_week_duration, last_week_duration),
        calories_change_percent=calc_change(this_week_calories, last_week_calories),
    )


def calculate_streak(workouts: list) -> StreakInfo:
    """Calculate current and longest workout streak"""
    if not workouts:
        return StreakInfo(current_streak=0, longest_streak=0, last_workout_date=None)

    workout_dates = set()
    for w in workouts:
        date_only = w["parsed_date"].date()
        workout_dates.add(date_only)

    sorted_dates = sorted(workout_dates, reverse=True)

    if not sorted_dates:
        return StreakInfo(current_streak=0, longest_streak=0, last_workout_date=None)

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    current_streak = 0
    if sorted_dates[0] >= yesterday:
        current_streak = 1
        check_date = sorted_dates[0] - timedelta(days=1)
        for date in sorted_dates[1:]:
            if date == check_date:
                current_streak += 1
                check_date = date - timedelta(days=1)
            elif date < check_date:
                break

    longest_streak = 1 if sorted_dates else 0
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] == sorted_dates[i - 1] - timedelta(days=1):
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 1

    return StreakInfo(
        current_streak=current_streak,
        longest_streak=longest_streak,
        last_workout_date=sorted_dates[0].isoformat() if sorted_dates else None,
    )


def calculate_workout_frequency(workouts: list) -> list[WorkoutFrequencyPoint]:
    """Get workout count per week for last 8 weeks"""
    now = datetime.now(UTC)
    result = []

    for weeks_ago in range(7, -1, -1):
        week_start, week_end = get_week_bounds(now, weeks_ago)
        week_workouts = [
            w for w in workouts if week_start <= w["parsed_date"] <= week_end
        ]
        label = week_start.strftime("%b %d")
        result.append(WorkoutFrequencyPoint(date=label, count=len(week_workouts)))

    return result


def calculate_calories_over_time(workouts: list) -> list[CaloriesOverTimePoint]:
    """Get calories burned per week for last 8 weeks"""
    now = datetime.now(UTC)
    result = []

    for weeks_ago in range(7, -1, -1):
        week_start, week_end = get_week_bounds(now, weeks_ago)
        week_workouts = [
            w for w in workouts if week_start <= w["parsed_date"] <= week_end
        ]
        total_calories = sum(
            convert_decimal(w.get("calories", 0)) for w in week_workouts
        )
        label = week_start.strftime("%b %d")
        result.append(CaloriesOverTimePoint(date=label, calories=total_calories))

    return result


def calculate_type_breakdown(workouts: list) -> list[WorkoutTypeBreakdown]:
    """Get breakdown by workout type"""
    type_stats = {}
    total_workouts = len(workouts)

    for w in workouts:
        workout_type = w.get("type", "Unknown")
        if workout_type not in type_stats:
            type_stats[workout_type] = {"count": 0, "duration": 0, "calories": 0}
        type_stats[workout_type]["count"] += 1
        type_stats[workout_type]["duration"] += convert_decimal(w.get("duration", 0))
        type_stats[workout_type]["calories"] += convert_decimal(w.get("calories", 0))

    result = []
    for workout_type, stats in type_stats.items():
        percentage = (
            (stats["count"] / total_workouts * 100) if total_workouts > 0 else 0
        )
        result.append(
            WorkoutTypeBreakdown(
                type=workout_type,
                count=stats["count"],
                total_duration=stats["duration"],
                total_calories=stats["calories"],
                percentage=round(percentage, 1),
            )
        )

    result.sort(key=lambda x: x.count, reverse=True)
    return result


def calculate_consistency_stats(workouts: list) -> ConsistencyStats:
    """Calculate overall consistency statistics"""
    if not workouts:
        return ConsistencyStats(
            total_workouts=0,
            total_duration=0,
            total_calories=0,
            avg_workouts_per_week=0,
            avg_duration_per_workout=0,
            most_active_day="N/A",
            favorite_workout_type="N/A",
        )

    total_workouts = len(workouts)
    total_duration = sum(convert_decimal(w.get("duration", 0)) for w in workouts)
    total_calories = sum(convert_decimal(w.get("calories", 0)) for w in workouts)

    dates = [w["parsed_date"].date() for w in workouts]
    if dates:
        date_range = (max(dates) - min(dates)).days + 1
        weeks = max(date_range / 7, 1)
        avg_workouts_per_week = round(total_workouts / weeks, 1)
    else:
        avg_workouts_per_week = 0

    avg_duration = (
        round(total_duration / total_workouts, 1) if total_workouts > 0 else 0
    )

    day_counts = {}
    for w in workouts:
        day_name = w["parsed_date"].strftime("%A")
        day_counts[day_name] = day_counts.get(day_name, 0) + 1
    most_active_day = max(day_counts, key=day_counts.get) if day_counts else "N/A"

    type_counts = {}
    for w in workouts:
        workout_type = w.get("type", "Unknown")
        type_counts[workout_type] = type_counts.get(workout_type, 0) + 1
    favorite_type = max(type_counts, key=type_counts.get) if type_counts else "N/A"

    return ConsistencyStats(
        total_workouts=total_workouts,
        total_duration=total_duration,
        total_calories=total_calories,
        avg_workouts_per_week=avg_workouts_per_week,
        avg_duration_per_workout=avg_duration,
        most_active_day=most_active_day,
        favorite_workout_type=favorite_type.capitalize()
        if favorite_type != "N/A"
        else "N/A",
    )


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}


@app.post("/workouts", response_model=Workout)
def log_workout(workout: Workout, user_id: str = Depends(get_current_user_id)):
    if not workout.id:
        workout.id = str(uuid4())
    if not workout.timestamp:
        workout.timestamp = datetime.now(UTC).isoformat()
    workout.user_id = user_id
    table.put_item(Item=workout.dict())
    return workout


@app.get("/workouts", response_model=list[Workout])
def get_workouts(user_id: str = Depends(get_current_user_id)):
    response = table.scan(
        FilterExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id}
    )
    return response.get("Items", [])


@app.get("/insights")
def get_insights(user_id: str = Depends(get_current_user_id)):
    response = table.scan(
        FilterExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id}
    )
    items = response.get("Items", [])
    total_calories = sum(item["calories"] for item in items)
    return {
        "total_calories": total_calories,
        "message": f"You've burned {total_calories} calories!",
    }


@app.get("/insights/comprehensive", response_model=ComprehensiveInsights)
def get_comprehensive_insights(user_id: str = Depends(get_current_user_id)):
    # Fetch all workouts for user
    response = table.scan(
        FilterExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id}
    )
    workouts = response.get("Items", [])

    # Fetch user profile for weekly targets
    profile_response = profile_table.get_item(Key={"user_id": user_id})
    profile = profile_response.get("Item", {})

    # Parse timestamps and sort
    for w in workouts:
        try:
            ts = w.get("timestamp", "")
            if ts:
                w["parsed_date"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                w["parsed_date"] = datetime.now(UTC)
        except:
            w["parsed_date"] = datetime.now(UTC)
    workouts.sort(key=lambda x: x["parsed_date"], reverse=True)

    # Calculate all insights
    weekly_progress = calculate_weekly_progress(workouts, profile)
    week_comparison = calculate_week_comparison(workouts)
    streak = calculate_streak(workouts)
    workout_frequency = calculate_workout_frequency(workouts)
    calories_over_time = calculate_calories_over_time(workouts)
    workout_type_breakdown = calculate_type_breakdown(workouts)
    consistency_stats = calculate_consistency_stats(workouts)

    return ComprehensiveInsights(
        weekly_progress=weekly_progress,
        week_comparison=week_comparison,
        streak=streak,
        workout_frequency=workout_frequency,
        calories_over_time=calories_over_time,
        workout_type_breakdown=workout_type_breakdown,
        consistency_stats=consistency_stats,
    )


@app.post("/profile", response_model=Profile)
def save_profile(profile: Profile, user_id: str = Depends(get_current_user_id)):
    profile.user_id = user_id
    profile_table.put_item(Item=profile.dict())
    return profile


@app.get("/profile")
def get_profile(user_id: str = Depends(get_current_user_id)):
    response = profile_table.get_item(Key={"user_id": user_id})
    return response.get("Item", {})


@app.get("/health")
def health():
    return {"ok": True}


@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: str, user_id: str = Depends(get_current_user_id)):
    # Verify ownership before deleting
    response = table.get_item(Key={"id": workout_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Workout not found")
    table.delete_item(Key={"id": workout_id})
    return {"message": f"Workout {workout_id} deleted."}


@app.post("/planned-workouts", response_model=PlannedWorkout)
def create_planned_workout(
    workout: PlannedWorkout, user_id: str = Depends(get_current_user_id)
):
    if not workout.id:
        workout.id = str(uuid4())
    if not workout.created_at:
        workout.created_at = datetime.now(UTC).isoformat()
    workout.user_id = user_id
    planned_workouts_table.put_item(Item=workout.dict())
    return workout


@app.get("/planned-workouts", response_model=list[PlannedWorkout])
def get_planned_workouts(user_id: str = Depends(get_current_user_id)):
    response = planned_workouts_table.scan(
        FilterExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id}
    )
    items = response.get("Items", [])
    # Sort by planned_date
    items.sort(key=lambda x: x.get("planned_date", ""))
    return items


@app.get("/planned-workouts/{workout_id}")
def get_planned_workout(workout_id: str, user_id: str = Depends(get_current_user_id)):
    response = planned_workouts_table.get_item(Key={"id": workout_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    return item


@app.put("/planned-workouts/{workout_id}", response_model=PlannedWorkout)
def update_planned_workout(
    workout_id: str,
    workout: PlannedWorkout,
    user_id: str = Depends(get_current_user_id),
):
    # Verify ownership
    response = planned_workouts_table.get_item(Key={"id": workout_id})
    existing = response.get("Item")
    if not existing or existing.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    workout.id = workout_id
    workout.user_id = user_id
    planned_workouts_table.put_item(Item=workout.dict())
    return workout


@app.delete("/planned-workouts/{workout_id}")
def delete_planned_workout(
    workout_id: str, user_id: str = Depends(get_current_user_id)
):
    # Verify ownership before deleting
    response = planned_workouts_table.get_item(Key={"id": workout_id})
    item = response.get("Item")
    if not item or item.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Planned workout not found")
    planned_workouts_table.delete_item(Key={"id": workout_id})
    return {"message": f"Planned workout {workout_id} deleted."}

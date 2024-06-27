from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import engine, get_db, Base
from models import User
from schemas import UserCreate, User as UserSchema
import aioredis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")

app = FastAPI()

# Initialize Redis
redis = aioredis.from_url(REDIS_URL)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # Create database tables
        await conn.run_sync(Base.metadata.create_all)

@app.post("/users/", response_model=UserSchema)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = User(name=user.name, email=user.email)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    await redis.set(f"user:{db_user.id}", db_user.json())
    return db_user

@app.get("/users/{user_id}", response_model=UserSchema)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    # Try to get the user from Redis cache
    user = await redis.get(f"user:{user_id}")
    if user:
        return UserSchema.parse_raw(user)

    # If not found in Redis, get from database
    result = await db.execute(select(User).filter(User.id == user_id))
    db_user = result.scalars().first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Cache the user in Redis
    await redis.set(f"user:{db_user.id}", db_user.json())
    return db_user

@app.put("/users/{user_id}", response_model=UserSchema)
async def update_user(user_id: int, user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    db_user = result.scalars().first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.name = user.name
    db_user.email = user.email
    await db.commit()
    await db.refresh(db_user)
    
    # Update Redis cache
    await redis.set(f"user:{db_user.id}", db_user.json())
    return db_user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    db_user = result.scalars().first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(db_user)
    await db.commit()

    # Remove from Redis cache
    await redis.delete(f"user:{user_id}")
    return {"ok": True}

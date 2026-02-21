PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "daily_limit": 3,  # free users total quota (will never reset)
        "is_free": True    # flag to identify free users
    },
    "starter": {
        "name": "Starter",
        "price": 20000,
        "daily_limit": 5
    },
    "pro": {
        "name": "Pro",
        "price": 70000,
        "daily_limit": 10
    },
    "max": {
        "name": "Max",
        "price": 150000,
        "daily_limit": 20  # top plan with 20 videos/day
    }
}
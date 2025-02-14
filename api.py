from fastapi import FastAPI, HTTPException
import requests
import stripe
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Configuration API TikTok (RapidAPI)
RAPIDAPI_KEY = "f1e0f97d90msh8ea49080d6b8b56p1b1f8cjsndd8c890d9017"
RAPIDAPI_HOST = "tiktok-api23.p.rapidapi.com"
MIN_VIEWS = 2000000  # 2M de vues minimum
DAYS_THRESHOLD = 15  # Vidéos récentes (moins de 15 jours)

# ✅ Configuration Stripe (Remplace par ta clé)
stripe.api_key = "TA_CLE_STRIPE_ICI"  # Remplace avec TA clé Stripe

def get_secuid(username: str):
    url = f"https://{RAPIDAPI_HOST}/api/user/info"
    headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}
    querystring = {"uniqueId": username}

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        data = response.json()
        return data["userInfo"]["user"]["secUid"]
    except Exception:
        return None

@app.get("/get_tiktok_videos")
def get_tiktok_videos(username: str):
    secUid = get_secuid(username)
    if not secUid:
        return {"error": "Impossible de récupérer le secUid"}

    url = f"https://{RAPIDAPI_HOST}/api/user/posts"
    headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}
    querystring = {"secUid": secUid, "count": "20"}

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        data = response.json()
        videos = data.get("data", {}).get("itemList", [])

        results = []
        for video in videos:
            views = int(video.get("stats", {}).get("playCount", 0))
            publish_time = datetime.utcfromtimestamp(int(video.get("createTime")))
            if views >= MIN_VIEWS and publish_time >= datetime.utcnow() - timedelta(days=DAYS_THRESHOLD):
                results.append({
                    "title": video.get("desc", "Vidéo TikTok"),
                    "video_url": f"https://www.tiktok.com/@{username}/video/{video['id']}",
                    "views": views,
                    "publish_time": publish_time.isoformat()
                })

        return {"videos": results}

    except Exception as e:
        return {"error": str(e)}

@app.post("/create-checkout-session")
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'TikTok Pro Access'},
                    'unit_amount': 1000,  # 10€
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url="https://tiktok-saas.vercel.app/success",
            cancel_url="https://tiktok-saas.vercel.app/cancel",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

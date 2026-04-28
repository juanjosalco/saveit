from sqlalchemy.orm import Session
from .models import Category, Rule

DEFAULT_CATEGORIES = [
    ("Restaurants", "#ef4444"),
    ("Groceries", "#22c55e"),
    ("Food Delivery", "#f97316"),
    ("Rideshare", "#eab308"),
    ("Travel", "#06b6d4"),
    ("Shopping", "#a855f7"),
    ("Subscriptions", "#3b82f6"),
    ("Utilities", "#0ea5e9"),
    ("Gas", "#84cc16"),
    ("Rent", "#dc2626"),
    ("Entertainment", "#ec4899"),
    ("Health", "#10b981"),
    ("Fees", "#71717a"),
    ("Payment", "#6366f1"),
    ("Refund", "#14b8a6"),
    ("Other", "#9ca3af"),
]

# (pattern, category_name, priority) — lower priority wins ties; first match in priority order is used
DEFAULT_RULES = [
    # Payments / refunds first
    ("PAYMENT THANK YOU", "Payment", 10),
    ("AUTOPAY", "Payment", 10),
    ("AMEX DINING CREDIT", "Refund", 10),
    ("CREDIT", "Refund", 90),

    # Rent
    ("BROADSTONE", "Rent", 20),
    ("YSI*", "Rent", 20),

    # Travel
    ("AMEXTRAVEL", "Travel", 30),
    ("DELTA", "Travel", 30), ("UNITED", "Travel", 30), ("ALASKA AIR", "Travel", 30),
    ("AMERICAN AIR", "Travel", 30), ("SOUTHWEST", "Travel", 30),
    ("MARRIOTT", "Travel", 30), ("HILTON", "Travel", 30),
    ("AIRBNB", "Travel", 30), ("EXPEDIA", "Travel", 30), ("BOOKING", "Travel", 30),
    ("VOLARIS", "Travel", 30), ("AEROMEXICO", "Travel", 30),

    # Food delivery
    ("UBER EATS", "Food Delivery", 40), ("DOORDASH", "Food Delivery", 40),
    ("RAPPI", "Food Delivery", 40), ("GRUBHUB", "Food Delivery", 40),

    # Rideshare
    ("UBER", "Rideshare", 50), ("LYFT", "Rideshare", 50), ("DIDI", "Rideshare", 50),

    # Subscriptions
    ("NETFLIX", "Subscriptions", 30), ("SPOTIFY", "Subscriptions", 30),
    ("HULU", "Subscriptions", 30), ("DISNEY", "Subscriptions", 30),
    ("APPLE.COM/BILL", "Subscriptions", 30), ("ICLOUD", "Subscriptions", 30),
    ("OPENAI", "Subscriptions", 30), ("CHATGPT", "Subscriptions", 30),
    ("GITHUB", "Subscriptions", 30), ("ANTHROPIC", "Subscriptions", 30),
    ("YOUTUBE", "Subscriptions", 30),

    # Utilities / phone
    ("T-MOBILE", "Utilities", 30), ("VERIZON", "Utilities", 30),
    ("AT&T", "Utilities", 30), ("COMCAST", "Utilities", 30),
    ("XFINITY", "Utilities", 30), ("PUGET SOUND ENERGY", "Utilities", 30),

    # Gas
    ("SHELL", "Gas", 40), ("CHEVRON", "Gas", 40), ("EXXON", "Gas", 40),
    ("ARCO", "Gas", 40),

    # Groceries
    ("QFC", "Groceries", 40), ("SAFEWAY", "Groceries", 40),
    ("TRADER", "Groceries", 40), ("WHOLEFDS", "Groceries", 40),
    ("WHOLE FOODS", "Groceries", 40), ("COSTCO", "Groceries", 40),
    ("WALMART", "Groceries", 40), ("TARGET", "Groceries", 40),
    ("H-MART", "Groceries", 40), ("HMART", "Groceries", 40),
    ("7-ELEVEN", "Groceries", 40),

    # Shopping
    ("AMAZON", "Shopping", 50), ("AMZN", "Shopping", 50),
    ("BEST BUY", "Shopping", 50), ("APPLE STORE", "Shopping", 50),
    ("CROCS", "Shopping", 50), ("NIKE", "Shopping", 50),
    ("SEPHORA", "Shopping", 50), ("DSW", "Shopping", 50),
    ("VICTORIAS SECRET", "Shopping", 50),

    # Entertainment
    ("CINEMARK", "Entertainment", 50), ("AMC THEATRES", "Entertainment", 50),
    ("STEAM", "Entertainment", 50), ("LUCKY STRIKE", "Entertainment", 50),
    ("FLATSTICK", "Entertainment", 50),

    # Health
    ("GYM", "Health", 50), ("FITNESS", "Health", 50),
    ("LIVING WELL HEALTH", "Health", 50), ("PHARMACY", "Health", 50),
    ("CVS", "Health", 50), ("WALGREENS", "Health", 50),

    # Fees
    ("ANNUAL MEMBERSHIP FEE", "Fees", 20), ("MEMBERSHIP FEE", "Fees", 30),
    ("FOREIGN TRANSACTION FEE", "Fees", 30),

    # Restaurants — broad catch-all (high number = lower priority, runs last)
    ("RESTAURANT", "Restaurants", 80), ("RAMEN", "Restaurants", 80),
    ("STARBUCKS", "Restaurants", 80), ("CHIPOTLE", "Restaurants", 80),
    ("MCDONALD", "Restaurants", 80), ("SUSHI", "Restaurants", 80),
    ("TST*", "Restaurants", 80), ("PIZZA", "Restaurants", 80),
    ("TACO", "Restaurants", 80), ("SUBWAY", "Restaurants", 80),
    ("PANDA", "Restaurants", 80), ("THAI", "Restaurants", 80),
    ("BURGER", "Restaurants", 80), ("GRILL", "Restaurants", 80),
    ("KITCHEN", "Restaurants", 80), ("COFFEE", "Restaurants", 80),
    ("CAFE", "Restaurants", 80), ("DUNKIN", "Restaurants", 80),
    ("POPEYE", "Restaurants", 80), ("WENDY", "Restaurants", 80),
    ("CHICKEN", "Restaurants", 80), ("BBQ", "Restaurants", 80),
    ("DINER", "Restaurants", 80), ("FIVE GUYS", "Restaurants", 80),
    ("CHICK-FIL-A", "Restaurants", 80), ("SHAKE SHACK", "Restaurants", 80),
    ("RAISING CANES", "Restaurants", 80), ("DICK'S DRIVE", "Restaurants", 80),
    ("JUST POKE", "Restaurants", 80), ("HELLO POKE", "Restaurants", 80),
    ("PARIS BAGUETTE", "Restaurants", 80), ("BAKERY", "Restaurants", 80),
    ("KIZUKI", "Restaurants", 80), ("WISEGUY", "Restaurants", 80),
    ("BOBA", "Restaurants", 80), ("GYRO", "Restaurants", 80),
    ("CHOP SUEY", "Restaurants", 80), ("FOODHALL", "Restaurants", 80),
    ("MERCADOPAGO", "Restaurants", 85),

    # Mexican / Spanish-language merchants (Santander statements)
    ("OXXO", "Groceries", 40), ("SORIANA", "Groceries", 40),
    ("CHEDRAUI", "Groceries", 40), ("SUPERAMA", "Groceries", 40),
    ("LA COMER", "Groceries", 40), ("CITY MARKET", "Groceries", 40),
    ("PEMEX", "Gas", 40), ("MOBIL", "Gas", 45),
    ("CFE", "Utilities", 30), ("TELMEX", "Utilities", 30),
    ("TELCEL", "Utilities", 30), ("IZZI", "Utilities", 30),
    ("TOTALPLAY", "Utilities", 30), ("MEGACABLE", "Utilities", 30),
    ("CINEPOLIS", "Entertainment", 50), ("CINEMEX", "Entertainment", 50),
    ("FARMACIA", "Health", 50), ("FARMACIAS DEL AHORRO", "Health", 50),
    ("FARMACIAS GUADALAJARA", "Health", 50), ("SIMILARES", "Health", 50),
    ("LIVERPOOL", "Shopping", 50), ("PALACIO DE HIERRO", "Shopping", 50),
    ("SANBORNS", "Shopping", 60),
    ("PAGO RECIBIDO", "Payment", 10), ("PAGO TARJETA", "Payment", 10),
    ("BONIFICACION", "Refund", 20), ("BONIFICACIÓN", "Refund", 20),
    ("COMISION", "Fees", 30), ("COMISIÓN", "Fees", 30),
    ("ANUALIDAD", "Fees", 20),
]


def seed_defaults(db: Session) -> None:
    if db.query(Category).count() == 0:
        for name, color in DEFAULT_CATEGORIES:
            db.add(Category(name=name, color=color))
        db.commit()
    cats = {c.name: c.id for c in db.query(Category).all()}
    # Additive: only insert rules whose (pattern, category_id) isn't already present.
    existing = {
        (r.pattern, r.category_id) for r in db.query(Rule).all()
    }
    added = False
    for pattern, cat_name, priority in DEFAULT_RULES:
        cid = cats.get(cat_name)
        if cid and (pattern, cid) not in existing:
            db.add(Rule(pattern=pattern, match_type="contains",
                        category_id=cid, priority=priority))
            added = True
    if added:
        db.commit()

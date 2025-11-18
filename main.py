import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order

app = FastAPI(title="Ecommerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductResponse(Product):
    id: str

class OrderRequest(Order):
    pass


@app.get("/")
def read_root():
    return {"message": "Ecommerce API running"}


@app.get("/schema")
def get_schema():
    """Expose schemas to admin tools/viewer"""
    return {
        "collections": [
            "user",
            "product",
            "order",
        ]
    }


@app.get("/api/products", response_model=List[ProductResponse])
def list_products():
    try:
        docs = get_documents("product")
        products = []
        for d in docs:
            d["id"] = str(d.get("_id"))
            d.pop("_id", None)
            products.append(d)
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orders")
def create_order(order: OrderRequest):
    try:
        # basic validation that product_ids exist
        for item in order.items:
            if not ObjectId.is_valid(item.product_id):
                raise HTTPException(status_code=400, detail=f"Invalid product id: {item.product_id}")
            prod = db["product"].find_one({"_id": ObjectId(item.product_id)})
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product not found: {item.product_id}")
        inserted_id = create_document("order", order)
        return {"id": inserted_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
def seed_products():
    """Seed some demo products if the collection is empty."""
    try:
        count = db["product"].count_documents({})
        if count > 0:
            return {"message": "Products already seeded", "count": count}
        demo = [
            {
                "title": "Classic Tee",
                "description": "Soft cotton tee in multiple colors.",
                "price": 24.99,
                "category": "Apparel",
                "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?q=80&w=1200&auto=format&fit=crop",
                "in_stock": True,
            },
            {
                "title": "Minimal Backpack",
                "description": "Durable everyday backpack with laptop sleeve.",
                "price": 79.0,
                "category": "Accessories",
                "image": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=1200&auto=format&fit=crop",
                "in_stock": True,
            },
            {
                "title": "Ceramic Mug",
                "description": "12oz matte-finish mug. Dishwasher safe.",
                "price": 14.5,
                "category": "Home",
                "image": "https://images.unsplash.com/photo-1517686469429-8bdb88b9f907?q=80&w=1200&auto=format&fit=crop",
                "in_stock": True,
            },
        ]
        for d in demo:
            create_document("product", d)
        return {"message": "Seeded", "count": len(demo)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db as _db

        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

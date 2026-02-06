from fastapi import FastAPI, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.price_service import price_service
from app.api.schemas import PriceResponse, PriceCreate

app = FastAPI(title="FBR Invoice Uploader API", version="1.0.0")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/prices/active", response_model=List[PriceResponse])
def get_active_prices(db: Session = Depends(get_db)):
    """
    Get all currently active prices.
    """
    return price_service.get_all_active_prices(db)

@app.get("/prices/{model}/active", response_model=PriceResponse)
def get_active_price_for_model(model: str, db: Session = Depends(get_db)):
    """
    Get active price for a specific model.
    """
    price = price_service.get_active_price(model, db)
    if not price:
        raise HTTPException(status_code=404, detail=f"No active price found for model {model}")
    return price

@app.get("/prices/{model}/history", response_model=List[PriceResponse])
def get_price_history(
    model: str, 
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get price history for a specific model (including expired ones).
    """
    # This requires a new method in PriceService or direct DB query
    # Implementing direct query here for now as Service didn't have history method explicitly
    from app.db.models import Price, ProductModel
    prices = db.query(Price).join(ProductModel).filter(ProductModel.model_name == model).order_by(Price.effective_date.desc()).limit(limit).all()
    if not prices:
         raise HTTPException(status_code=404, detail=f"No price history found for model {model}")
    return prices

@app.post("/prices", response_model=PriceResponse)
def create_price(price: PriceCreate, db: Session = Depends(get_db)):
    """
    Create a new price version for a model. Expires the previous active price.
    """
    try:
        new_price = price_service.add_price(
            model=price.model,
            base_price=price.base_price,
            tax=price.tax_amount,
            levy=price.levy_amount,
            total=price.total_price,
            optional_features=price.optional_features,
            db=db
        )
        return new_price
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/invoices/check-chassis/{chassis_number}")
def check_chassis_duplication(chassis_number: str, db: Session = Depends(get_db)):
    """
    Check if a chassis number has already been used in a posted invoice.
    """
    from app.services.invoice_service import InvoiceService
    service = InvoiceService()
    is_duplicate = service.is_chassis_used_in_posted_invoice(db, chassis_number)
    
    if is_duplicate:
        return {
            "exists": True, 
            "message": f"Invoice with chassis number {chassis_number} has already been posted"
        }
    return {"exists": False, "message": "Chassis number is available"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

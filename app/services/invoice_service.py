from sqlalchemy.orm import Session
from app.db.models import Invoice, InvoiceItem, Motorcycle, Customer, CustomerType, ProductModel
from app.api.schemas import InvoiceCreate
from app.api.fbr_client import fbr_client
from app.core.logger import logger
from datetime import datetime
from typing import Optional
import json

class InvoiceService:
    def create_invoice(self, db: Session, invoice_in: InvoiceCreate):
        # 1. Calculate totals
        total_sale_value = 0.0
        total_tax_charged = 0.0
        total_further_tax = 0.0
        total_quantity = 0.0
        total_amount = 0.0

        db_items = []
        for item in invoice_in.items:
            # Check for Chassis Uniqueness across all fiscalized invoices
            if item.chassis_number:
                # Check if this chassis has already been fiscalized (successfully uploaded)
                # Note: InvoiceItem no longer has chassis_number directly, it links to Motorcycle
                # But we can check via Motorcycle link or logic.
                # Since we are creating new items, we check DB.
                # Wait, InvoiceItem lost chassis_number column in my new model.
                # So I must find the motorcycle first.
                pass

            # Trust input values from price table as per user request
            sale_value = item.sale_value
            tax_charged = item.tax_charged
            further_tax = item.further_tax if hasattr(item, 'further_tax') else 0.0
            
            # Calculate line total
            line_total = sale_value + tax_charged + further_tax

            # Update totals
            total_sale_value += sale_value
            total_tax_charged += tax_charged
            total_further_tax += further_tax
            total_quantity += item.quantity
            total_amount += line_total

            # Inventory Logic: Check and Update Status
            motorcycle_id = None
            if item.chassis_number:
                # Find bike by chassis
                lookup_chassis = item.chassis_number.upper()
                bike = db.query(Motorcycle).filter(Motorcycle.chassis_number == lookup_chassis).first()
                if bike:
                    if bike.status != "IN_STOCK":
                        # Check if it was sold in a fiscalized invoice?
                        # Simplified: If status is not IN_STOCK, error.
                        raise ValueError(f"Motorcycle Chassis {lookup_chassis} is already {bike.status}")
                    
                    # Mark as SOLD
                    bike.status = "SOLD"
                    motorcycle_id = bike.id
                    db.add(bike) # Ensure update is tracked
                else:
                    # Create new motorcycle if details are provided (User Request: Add to inventory as SOLD)
                    if getattr(item, 'model_name', None) and getattr(item, 'color', None):
                        product_model = db.query(ProductModel).filter(ProductModel.model_name == item.model_name).first()
                        if product_model:
                            # Use 0.0 for prices as per user request (Do not save price in inventory for auto-created bikes)
                            new_bike = Motorcycle(
                                chassis_number=lookup_chassis,
                                engine_number=(item.engine_number or "UNKNOWN").upper(),
                                product_model_id=product_model.id,
                                year=datetime.now().year,
                                color=item.color.upper(),
                                cost_price=0.0, 
                                sale_price=0.0,
                                status="SOLD",
                                purchase_date=datetime.now()
                            )
                            db.add(new_bike)
                            db.flush() # To get ID
                            motorcycle_id = new_bike.id
                            logger.info(f"Created new SOLD motorcycle for chassis {item.chassis_number}")
                        else:
                             logger.warning(f"Model {item.model_name} not found. Cannot create motorcycle for chassis {item.chassis_number}.")
                    else:
                        logger.warning(f"Chassis {item.chassis_number} not found in Inventory. Missing model/color to create.")

            db_item = InvoiceItem(
                item_code=item.item_code,
                item_name=item.item_name,
                pct_code=item.pct_code,
                quantity=item.quantity,
                tax_rate=item.tax_rate,
                sale_value=sale_value,
                further_tax=further_tax,
                tax_charged=tax_charged,
                total_amount=line_total,
                motorcycle_id=motorcycle_id
                # Removed chassis_number, engine_number from InvoiceItem
            )
            db_items.append(db_item)

        # Customer Logic: Find or Create
        customer = None
        if invoice_in.buyer_cnic:
            customer = db.query(Customer).filter(Customer.cnic == invoice_in.buyer_cnic).first()
        
        if customer:
            # Update info
            if invoice_in.buyer_name: customer.name = invoice_in.buyer_name.upper()
            if invoice_in.buyer_father_name: customer.father_name = invoice_in.buyer_father_name.upper()
            if invoice_in.buyer_ntn: customer.ntn = (invoice_in.buyer_ntn or "").upper()
            if invoice_in.buyer_phone: customer.phone = invoice_in.buyer_phone
            if invoice_in.buyer_address: customer.address = invoice_in.buyer_address.upper()
        else:
            # Create new
            customer = Customer(
                cnic=invoice_in.buyer_cnic,
                name=(invoice_in.buyer_name or "").upper(),
                father_name=(invoice_in.buyer_father_name or "").upper(),
                ntn=(invoice_in.buyer_ntn or "").upper(),
                phone=invoice_in.buyer_phone,
                address=(invoice_in.buyer_address or "").upper(),
                type=CustomerType.INDIVIDUAL
            )
            db.add(customer)
        
        db.flush() # Get customer.id

        # 2. Attempt to Fiscalize (Upload to FBR) BEFORE saving to DB
        
        # Prepare data for client
        fbr_invoice_data = {
            "invoice_number": invoice_in.invoice_number,
            "datetime": invoice_in.datetime,
            "buyer_name": invoice_in.buyer_name,
            "buyer_ntn": invoice_in.buyer_ntn,
            "buyer_cnic": invoice_in.buyer_cnic,
            "buyer_phone": invoice_in.buyer_phone,
            "total_sale_value": total_sale_value,
            "total_tax_charged": total_tax_charged,
            "total_further_tax": total_further_tax,
            "total_quantity": total_quantity,
            "total_amount": total_amount,
            "payment_mode": invoice_in.payment_mode,
            "items": [
                {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "tax_rate": item.tax_rate,
                    "sale_value": item.sale_value,
                    "further_tax": item.further_tax if hasattr(item, 'further_tax') else 0.0,
                    "tax_charged": item.tax_charged,
                    "total_amount": item.sale_value + item.tax_charged + (item.further_tax if hasattr(item, 'further_tax') else 0.0),
                    "pct_code": item.pct_code,
                    "discount": item.discount
                } for item in invoice_in.items
            ]
        }

        try:
            # Get latest settings dynamically from DB
            from app.services.settings_service import settings_service
            settings = settings_service.get_active_settings()
            
            logger.info(f"AUDIT: Starting FBR Upload for Invoice {invoice_in.invoice_number}. Environment: {settings.get('env', 'UNKNOWN')}")
            response = fbr_client.post_invoice(fbr_invoice_data)
            
            # Check response success - Strict Validation
            if not response:
                raise ValueError("Received empty response from FBR.")

            # Validate key success indicators
            fbr_inv_num = response.get("InvoiceNumber")
            fbr_response_msg = response.get("Response")
            fbr_code = response.get("Code")
            
            # 0. Strict Rule: Code MUST be 100
            if str(fbr_code) != "100":
                 error_msg = f"FBR Error (Code {fbr_code}): {fbr_response_msg}"
                 logger.error(f"AUDIT: FBR Upload Rejected. {error_msg}")
                 raise Exception(error_msg)

            # 1. Check if InvoiceNumber exists
            if not fbr_inv_num or str(fbr_inv_num).strip().lower() == "not available":
                 error_msg = f"FBR did not return a valid Invoice Number. Response: {fbr_response_msg}"
                 logger.error(f"AUDIT: FBR Upload Failed for {invoice_in.invoice_number}. Reason: {error_msg}")
                 raise Exception(f"FBR Upload Failed: {error_msg}")

            # 2. Check for Echoed Invoice Number (Bug Fix)
            if str(fbr_inv_num) == str(invoice_in.invoice_number):
                error_msg = f"FBR returned echoed Invoice Number '{fbr_inv_num}' instead of Fiscal ID. Response: {fbr_response_msg}"
                logger.error(f"AUDIT: FBR Upload Rejected (Echo detected) for {invoice_in.invoice_number}.")
                raise Exception(f"FBR Validation Failed: {error_msg}")

            # 3. Check format
            if not fbr_inv_num or not isinstance(fbr_inv_num, (str, int)):
                 error_msg = f"Invalid FBR Invoice Number format: '{fbr_inv_num}'. Expected string or number."
                 logger.error(f"AUDIT: FBR Upload Rejected (Invalid Format) for {invoice_in.invoice_number}.")
                 raise Exception(f"FBR Validation Failed: {error_msg}")
                 
            logger.info(f"AUDIT: FBR Upload Success for {invoice_in.invoice_number}. FBR ID: {fbr_inv_num}")
            
            # 3. Create Invoice Record ONLY if FBR success
            db_invoice = Invoice(
                invoice_number=invoice_in.invoice_number,
                pos_id=settings.get("pos_id", ""),
                usin=invoice_in.invoice_number, 
                datetime=invoice_in.datetime,
                
                customer_id=customer.id,
                
                total_sale_value=total_sale_value,
                total_tax_charged=total_tax_charged,
                total_further_tax=total_further_tax,
                total_quantity=total_quantity,
                total_amount=total_amount,
                payment_mode=invoice_in.payment_mode,
                items=db_items,
                
                # FBR Fields
                fbr_invoice_number=response.get("InvoiceNumber"),
                is_fiscalized=True,
                sync_status="SYNCED",
                fbr_response_code=str(response.get("Code")) if response.get("Code") else None,
                fbr_response_message="Success",
                fbr_full_response=response
            )
    
            db.add(db_invoice)
            db.commit()
            db.refresh(db_invoice)
            
            return db_invoice

        except Exception as e:
            logger.error(f"Invoice creation failed: {e}")
            db.rollback() # Ensure nothing is saved
            raise e # Propagate error to UI
            
    def sync_invoice(self, db: Session, invoice: Invoice):
        """
        Tries to upload a single invoice to FBR.
        Updates status based on response.
        """
        try:
            # Prepare data for client
            # Retrieve customer details
            customer = invoice.customer
            
            invoice_data = {
                "invoice_number": invoice.invoice_number,
                "datetime": invoice.datetime,
                "buyer_name": customer.name if customer else "",
                "buyer_ntn": customer.ntn if customer else "",
                "buyer_cnic": customer.cnic if customer else "",
                "buyer_phone": customer.phone if customer else "",
                "total_sale_value": invoice.total_sale_value,
                "total_tax_charged": invoice.total_tax_charged,
                "total_quantity": invoice.total_quantity,
                "total_amount": invoice.total_amount,
                "payment_mode": invoice.payment_mode,
                "items": [
                    {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "quantity": item.quantity,
                        "tax_rate": item.tax_rate,
                        "sale_value": item.sale_value,
                        "tax_charged": item.tax_charged,
                        "further_tax": item.further_tax,
                        "total_amount": item.total_amount,
                        "pct_code": item.pct_code,
                        "discount": item.discount
                    } for item in invoice.items
                ]
            }

            logger.info(f"Syncing invoice {invoice.invoice_number} to FBR...")
            response = fbr_client.post_invoice(invoice_data)
            
            if response and "InvoiceNumber" in response:
                invoice.fbr_invoice_number = response.get("InvoiceNumber")
                invoice.is_fiscalized = True
                invoice.sync_status = "SYNCED"
                invoice.fbr_response_code = str(response.get("Code")) if response.get("Code") else None
                invoice.fbr_response_message = "Success"
                invoice.fbr_full_response = response
            else:
                invoice.sync_status = "FAILED"
                invoice.fbr_response_message = response.get("Response", "Unknown Error") if response else "No response"
                
            db.commit()
            
        except Exception as e:
            logger.error(f"Invoice sync failed: {e}")
            invoice.sync_status = "FAILED"
            invoice.fbr_response_message = str(e)
            db.commit()

    def get_last_invoice_by_cnic(self, db: Session, cnic: str) -> Optional[Invoice]:
        """
        Finds the most recent invoice for a given CNIC to auto-populate customer details.
        """
        # Join Customer to filter by CNIC
        return db.query(Invoice).join(Customer).filter(Customer.cnic == cnic).order_by(Invoice.id.desc()).first()

    def generate_next_invoice_number(self, db: Session) -> str:
        """
        Generates the next invoice number based on FBR USIN setting.
        Format: {USIN}-{0001}
        """
        from app.services.settings_service import settings_service
        settings = settings_service.get_active_settings()
        
        usin = settings.get("usin", "")
        if usin:
            usin = usin.strip()
            
        if not usin:
            # Fallback if USIN is missing
            logger.warning("FBR_USIN not set in configuration. Using 'UNKNOWN'.")
            usin = "UNKNOWN"
            
        # Find the last invoice number that starts with this USIN
        last_invoice = db.query(Invoice).filter(
            Invoice.invoice_number.like(f"{usin}-%")
        ).order_by(Invoice.id.desc()).first()
        
        if last_invoice:
            try:
                # Extract the numeric part (last 4 digits)
                parts = last_invoice.invoice_number.split("-")
                last_seq_str = parts[-1]
                last_seq = int(last_seq_str)
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                # If parsing fails, start from 1
                logger.warning(f"Failed to parse sequence from last invoice number: {last_invoice.invoice_number}. Resetting to 1.")
                next_seq = 1
        else:
            next_seq = 1
            
        return f"{usin}-{next_seq:04d}"

invoice_service = InvoiceService()

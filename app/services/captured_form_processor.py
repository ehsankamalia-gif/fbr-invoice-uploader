import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import CapturedData
from app.core.logger import logger

class CapturedFormProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mapping = config.get("field_mapping", {})

    def process_submission(self, session_data: Dict[str, Any]) -> bool:
        """
        Processes the captured session data, maps it to CapturedData model, 
        and saves it to the database.
        """
        try:
            # 1. Flatten data from all pages
            flat_data = {}
            pages = session_data.get("pages", {})
            for url, page_data in pages.items():
                fields = page_data.get("fields", {})
                for selector, field_info in fields.items():
                    val = field_info.get("value", "")
                    flat_data[selector] = val

            logger.info(f"Processing submission with data: {flat_data}")

            # DEBUG: Dump flat data
            try:
                with open("save_debug.txt", "a") as f:
                    f.write(f"\n--- SUBMISSION START {datetime.now()} ---\n")
                    f.write(f"Flat Data Keys: {list(flat_data.keys())}\n")
                    f.write(f"Flat Data Content: {flat_data}\n")
            except:
                pass

            # 2. Map data to schema fields
            mapped_data = self._map_data(flat_data)
            logger.info(f"Mapped data: {mapped_data}")

            # DEBUG: Dump mapped data
            try:
                with open("save_debug.txt", "a") as f:
                    f.write(f"Mapped Data: {mapped_data}\n")
            except:
                pass

            # 3. Validate required fields
            if not self._validate(mapped_data):
                logger.error("Validation failed for captured form.")
                return False

            # 4. Save to CapturedData Table
            with SessionLocal() as db:
                # Check uniqueness of chassis
                chassis = mapped_data.get("chassis_number")
                existing = db.query(CapturedData).filter(CapturedData.chassis_number == chassis).first()
                
                if existing:
                    # Update existing record
                    logger.info(f"Updating existing record for chassis {chassis}")
                    existing.name = (mapped_data.get("buyer_name") or "").upper()
                    existing.father = (mapped_data.get("buyer_father_name") or "").upper()
                    existing.cnic = mapped_data.get("buyer_cnic")
                    existing.cell = mapped_data.get("buyer_phone")
                    existing.address = (mapped_data.get("buyer_address") or "").upper()
                    existing.engine_number = (mapped_data.get("engine_number") or "").upper()
                    existing.color = (mapped_data.get("color") or "").upper()
                    existing.model = (mapped_data.get("model_name") or "").upper()
                    existing.created_at = datetime.utcnow() # Update timestamp?
                else:
                    # Create new record
                    logger.info(f"Creating new record for chassis {chassis}")
                    new_record = CapturedData(
                        name=(mapped_data.get("buyer_name") or "").upper(),
                        father=(mapped_data.get("buyer_father_name") or "").upper(),
                        cnic=mapped_data.get("buyer_cnic"),
                        cell=mapped_data.get("buyer_phone"),
                        address=(mapped_data.get("buyer_address") or "").upper(),
                        chassis_number=(chassis or "").upper(),
                        engine_number=(mapped_data.get("engine_number") or "").upper(),
                        color=(mapped_data.get("color") or "").upper(),
                        model=(mapped_data.get("model_name") or "").upper()
                    )
                    db.add(new_record)
                
                db.commit()
                return True

        except Exception as e:
            logger.error(f"Error processing captured form submission: {e}")
            return False

    def _map_data(self, flat_data: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        
        # specific handling for CNIC parts if they exist in mapping
        cnic_parts = []
        
        # Merge diagnostic inputs if available as fallback
        diagnostic_inputs = flat_data.get("_debug_all_inputs", {})
        if isinstance(diagnostic_inputs, dict):
            # Normalize diagnostic keys to lowercase for fuzzy matching
            diagnostic_map = {k.lower(): v for k, v in diagnostic_inputs.items() if k}
        else:
            diagnostic_map = {}
        
        for selector, value in flat_data.items():
            if selector == "_debug_all_inputs": continue

            # Check if this selector is mapped
            target_field = self.mapping.get(selector)
            
            # If not found, try to match by ID only (e.g. input#txt_id -> #txt_id)
            if not target_field and '#' in selector:
                # Extract ID part
                id_part = '#' + selector.split('#')[-1]
                target_field = self.mapping.get(id_part)
            
            if target_field:
                result[target_field] = value
                
                # Special CNIC handling
                if target_field.startswith("buyer_cnic_part"):
                    cnic_parts.append((target_field, value))

        # FALLBACK: Check for missing fields using diagnostic map
        for selector, target_field in self.mapping.items():
            if target_field not in result:
                # Try to find it in diagnostic_map
                # Selector is like "#txt_full_name" -> look for "txt_full_name"
                clean_key = selector.replace('#', '').replace('.', '').lower()
                
                if clean_key in diagnostic_map:
                    val = diagnostic_map[clean_key]
                    if val:
                        logger.info(f"Fallback: Found {target_field} via diagnostic map key {clean_key}")
                        result[target_field] = val
                        
                        if target_field.startswith("buyer_cnic_part"):
                            cnic_parts.append((target_field, val))

        # Reconstruct CNIC if parts are found
        if cnic_parts:
            # Sort by part number (part1, part2, part3)
            cnic_parts.sort(key=lambda x: x[0])
            
            # Explicitly look for parts
            p1 = result.get("buyer_cnic_part1", "")
            p2 = result.get("buyer_cnic_part2", "")
            p3 = result.get("buyer_cnic_part3", "")
            
            if p1 and p2 and p3:
                 result["buyer_cnic"] = f"{p1}-{p2}-{p3}"
            elif cnic_parts:
                 # Fallback if keys don't match exactly but we have parts
                 # Assuming sorted order is correct
                 result["buyer_cnic"] = "-".join([p[1] for p in cnic_parts if p[1]])

        # Append City to Address
        if "city" in result and "buyer_address" in result:
            city = result["city"].strip()
            address = result["buyer_address"].strip()
            if city and address:
                # Check if city is already in address to avoid duplication
                if city.lower() not in address.lower():
                    result["buyer_address"] = f"{address}, {city}"
                    logger.info(f"Appended city '{city}' to address: {result['buyer_address']}")

        return result

    def _validate(self, data: Dict[str, Any]) -> bool:
        # Minimal validation
        # Only require chassis number now as that's the primary key/unique identifier
        if not data.get("chassis_number"):
            logger.warning("Missing chassis_number in captured data")
            return False
            
        return True

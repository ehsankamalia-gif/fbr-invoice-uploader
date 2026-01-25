import os
import tempfile
import webbrowser
import base64
from io import BytesIO
import html
import qrcode
from datetime import datetime
from app.db.models import Invoice

class PrintService:
    def generate_qr_base64(self, data):
        if not data:
            return None
        try:
            qr = qrcode.QRCode(box_size=10, border=4)
            qr.add_data(str(data))
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"Error generating QR for print: {e}")
            return None

    def print_honda_invoice(self, invoice: Invoice, chassis_filter=None, explicit_item=None):
        """
        Generates a Honda-specific HTML invoice layout matching the provided image.
        """
        try:
            # Prepare Data
            inv_num = invoice.invoice_number
            date_str = invoice.datetime.strftime("%d-%m-%y")
            
            customer_name = invoice.customer.name if invoice.customer else "N/A"
            customer_father = invoice.customer.father_name if invoice.customer else ""
            customer_cnic = invoice.customer.cnic if invoice.customer else ""
            customer_address = invoice.customer.address if invoice.customer else ""
            customer_phone = invoice.customer.phone if invoice.customer else ""
            
            # Filter for the specific chassis item if provided, otherwise take the first vehicle item
            target_item = explicit_item
            if not target_item:
                for item in invoice.items:
                    if chassis_filter:
                        if (item.motorcycle and item.motorcycle.chassis_number == chassis_filter):
                            target_item = item
                            break
                    else:
                        # Heuristic: find first item with chassis
                        if item.motorcycle_id:
                            target_item = item
                            break
            
            if not target_item:
                return False, "No vehicle item found in invoice."

            # Item Details
            model_name = getattr(target_item, 'model_name', None) or "Honda Motorcycle"
            if not model_name or model_name == "None":
                 # Try to fetch from relationship if available
                 if target_item.motorcycle and target_item.motorcycle.product_model:
                     model_name = target_item.motorcycle.product_model.model_name
                 else:
                     model_name = target_item.item_name

            engine_no = target_item.motorcycle.engine_number if target_item.motorcycle else "N/A"
            chassis_no = target_item.motorcycle.chassis_number if target_item.motorcycle else "N/A"
            color = getattr(target_item, 'color', None) or (target_item.motorcycle.color if target_item.motorcycle else "N/A")
            model_year = getattr(target_item, 'year', None) or (target_item.motorcycle.year if target_item.motorcycle else datetime.now().year)

            # Financials
            val_excl = target_item.sale_value
            tax_rate = int(target_item.tax_rate)
            sales_tax = target_item.tax_charged
            val_incl = val_excl + sales_tax
            
            # Levy handling (Assuming further_tax is the levy or explicitly calculated)
            # The image shows "N.E.V. Levy (@ 1%)".
            # If further_tax is > 0, we use that.
            levy_amount = target_item.further_tax
            
            grand_total = val_incl + levy_amount
            
            # QR Code Logic for Honda Invoice
            fbr_inv_num = invoice.fbr_invoice_number
            qr_html = ""
            if fbr_inv_num:
                qr_base64 = self.generate_qr_base64(fbr_inv_num)
                if qr_base64:
                    qr_html = f"""
                    <div style="margin-top: 40px; text-align: center;">
                        <img src="data:image/png;base64,{qr_base64}" alt="FBR QR" style="width: 100px; height: 100px;"/>
                        <div style="font-size: 10px; font-weight: bold; margin-top: 5px;">FBR Invoice #: {fbr_inv_num}</div>
                    </div>
                    """

            # CNIC Formatting (Boxed)
            cnic_digits = [c for c in customer_cnic if c.isdigit()]
            # Pad or truncate to 13 digits for the standard 5-7-1 format
            # Display format in image: 5 boxes - 7 boxes - 1 box
            cnic_html = ""
            
            # Helper for boxes
            def make_boxes(digits, count):
                html = ""
                for i in range(count):
                    d = digits[i] if i < len(digits) else "&nbsp;"
                    html += f'<div class="box">{d}</div>'
                return html, digits[count:]

            rem_digits = cnic_digits
            part1, rem_digits = make_boxes(rem_digits, 5)
            part2, rem_digits = make_boxes(rem_digits, 7)
            part3, rem_digits = make_boxes(rem_digits, 1)
            
            cnic_display = f"""
            <div class="cnic-wrapper">
                {part1}
                <div class="dash">-</div>
                {part2}
                <div class="dash">-</div>
                {part3}
            </div>
            """

            # HTML Content
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Invoice {inv_num}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #000; }}
                    .container {{ width: 100%; max-width: 900px; margin: auto; }}
                    
                    /* Header */
                    .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }}
                    .logo-left {{ width: 200px; }} /* Placeholder for Honda Logo */
                    .logo-left h1 {{ color: #CC0000; font-style: italic; font-weight: 900; margin: 0; font-size: 32px; }}
                    
                    .dealer-info {{ text-align: right; font-size: 12px; }}
                    .dealer-info .logo-3s {{ font-weight: bold; border: 2px solid #CC0000; border-radius: 50%; width: 40px; height: 40px; line-height: 40px; text-align: center; display: inline-block; color: #CC0000; margin-bottom: 5px; }}
                    .dealer-name {{ font-weight: bold; font-size: 16px; color: #CC0000; }}
                    
                    /* Title */
                    .invoice-title {{ text-align: center; color: #CC0000; font-size: 24px; font-weight: bold; margin: 10px 0; text-transform: uppercase; letter-spacing: 2px; }}
                    
                    /* Meta */
                    .meta-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
                    .meta-field {{ display: flex; align-items: baseline; }}
                    .meta-field label {{ font-weight: bold; margin-right: 5px; font-style: italic; }}
                    .meta-field span {{ border-bottom: 1px solid #000; min-width: 150px; display: inline-block; text-align: center; }}
                    
                    /* Customer Info */
                    .customer-row {{ margin-bottom: 8px; display: flex; align-items: baseline; }}
                    .customer-row label {{ font-weight: bold; width: 80px; }}
                    .customer-input {{ flex: 1; border-bottom: 1px solid #000; padding-left: 10px; }}
                    
                    .cnic-row {{ display: flex; align-items: center; margin-top: 10px; margin-bottom: 20px; }}
                    .cnic-label {{ font-weight: bold; margin-right: 10px; }}
                    .cnic-wrapper {{ display: flex; align-items: center; }}
                    .box {{ width: 20px; height: 25px; border: 1px solid #000; text-align: center; line-height: 25px; margin-right: 2px; font-weight: bold; }}
                    .dash {{ margin: 0 5px; font-weight: bold; }}
                    
                    .mob-label {{ font-weight: bold; margin-left: 20px; margin-right: 10px; }}
                    .mob-input {{ border-bottom: 1px solid #000; min-width: 150px; display: inline-block; }}

                    /* Table */
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; border: 2px solid #000; }}
                    th, td {{ border: 1px solid #000; padding: 8px; vertical-align: top; }}
                    th {{ text-align: center; font-weight: bold; font-size: 12px; }}
                    
                    .col-qty {{ width: 40px; text-align: center; }}
                    .col-desc {{ width: 40%; }}
                    .col-val {{ text-align: center; width: 15%; }}
                    .col-rate {{ text-align: center; width: 10%; }}
                    .col-tax {{ text-align: center; width: 15%; }}
                    .col-total {{ text-align: center; width: 15%; }}
                    
                    .desc-line {{ margin-bottom: 15px; display: block; }}
                    .desc-label {{ display: inline-block; width: 120px; }}
                    .desc-val {{ font-weight: bold; }}
                    
                    .levy-line {{ margin-top: 10px; font-weight: bold; text-align: right; display: block; }}
                    
                    /* Footer */
                    .footer-total {{ font-weight: bold; text-align: right; font-size: 14px; padding: 10px; }}
                    
                    .signatures {{ display: flex; justify-content: space-between; margin-top: 60px; }}
                    .sig-box {{ text-align: center; width: 200px; border-top: 1px solid #000; padding-top: 5px; }}
                    .dealer-stamp {{ text-align: center; }}
                    .dealer-stamp h3 {{ margin: 0; color: #000080; }}
                    .dealer-stamp p {{ margin: 0; font-size: 10px; }}
                    
                    @media print {{
                        body {{ -webkit-print-color-adjust: exact; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <!-- Header -->
                    <div class="header">
                        <div class="logo-left">
                            <h1>HONDA</h1>
                        </div>
                        <div class="dealer-info">
                            <div class="logo-3s">3S</div>
                            <div class="dealer-name">Data Motors</div>
                            <div>Chichawatni Road, Kamalia</div>
                            <div>Ph: 0300-6564768, 0333-7264768</div>
                            <div>Sales Tax Registration No: 2400416228112</div>
                            <div>NTN: 4162281-2</div>
                        </div>
                    </div>
                    
                    <div class="meta-row">
                        <div class="meta-field">
                            <label>Date:</label>
                            <span>{date_str}</span>
                        </div>
                        <div class="invoice-title">INVOICE</div>
                        <div class="meta-field">
                            <label>No.</label>
                            <span>{inv_num}</span>
                        </div>
                    </div>
                    
                    <!-- Customer Info -->
                    <div class="customer-row">
                        <label>Name</label>
                        <div class="customer-input">{customer_name} &nbsp;&nbsp;&nbsp; S/O &nbsp;&nbsp;&nbsp; {customer_father}</div>
                    </div>
                    <div class="customer-row">
                        <label>Address</label>
                        <div class="customer-input">{customer_address}</div>
                    </div>
                    
                    <div class="cnic-row">
                        <div class="cnic-label">CNIC #</div>
                        {cnic_display}
                        <div class="mob-label">Mob #</div>
                        <div class="mob-input">{customer_phone}</div>
                    </div>
                    
                    <!-- Table -->
                    <table>
                        <thead>
                            <tr>
                                <th>QTY<br>No</th>
                                <th>Description of Goods</th>
                                <th>Value<br>Excluding<br>Sales Tax</th>
                                <th>Rate<br>of Sales Tax</th>
                                <th>Sales Tax<br>Payable</th>
                                <th>Value<br>Including<br>Sales Tax</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr style="height: 400px;">
                                <td class="col-qty">1</td>
                                <td class="col-desc">
                                    <span class="desc-line">Honda Motorcycle : <span class="desc-val">{model_name}</span></span>
                                    <span class="desc-line">Engine No : <span class="desc-val">{engine_no}</span></span>
                                    <span class="desc-line">Chasis No : <span class="desc-val">{chassis_no}</span></span>
                                    <span class="desc-line">Model : <span class="desc-val">{model_year}</span></span>
                                    <span class="desc-line">Colour : <span class="desc-val">{color}</span></span>
                                    <span class="desc-line">Registration Letter No : ........................</span>
                                    {qr_html}
                                </td>
                                <td class="col-val">{val_excl:,.0f}</td>
                                <td class="col-rate">{tax_rate}%</td>
                                <td class="col-tax">
                                    {sales_tax:,.0f}<br>
                                    {f'<br><span class="levy-line">N.E.V. Levy (@ 1%) Rs.{levy_amount:,.0f}/-</span>' if levy_amount > 0 else ''}
                                </td>
                                <td class="col-total">Rs.{val_incl:,.0f}/-</td>
                            </tr>
                            <tr>
                                <td colspan="5" class="footer-total">TOTAL</td>
                                <td class="footer-total">Rs.{grand_total:,.0f}/-</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <!-- Signatures -->
                    <div class="signatures">
                        <div class="sig-box">
                            Customer Signature
                        </div>
                        <div class="dealer-stamp">
                            <h3>DATA MOTORS</h3>
                            <p>Chichawatni Road Kamalia</p>
                            <p>0300-6564768</p>
                            <p>0333-7264768</p>
                        </div>
                        <div class="sig-box">
                            For Data Motors<br><br>
                            Signature
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Save and Open
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                url = 'file://' + f.name
                webbrowser.open(url)
                
            return True, "Invoice opened in browser"
            
        except Exception as e:
            return False, str(e)

    def print_honda_live_preview(
        self,
        invoice: Invoice,
        layout_config: dict,
        chassis_filter=None,
        explicit_item=None,
        overrides: dict = None,
        paper_width_mm: float = 210,
        paper_height_mm: float = 297,
        preview_width_px: float = 600,
        preview_height_px: float = 850,
    ):
        try:
            target_item = explicit_item
            if not target_item:
                for item in invoice.items:
                    if chassis_filter:
                        if item.motorcycle and item.motorcycle.chassis_number == chassis_filter:
                            target_item = item
                            break
                    else:
                        if item.motorcycle_id:
                            target_item = item
                            break

            if not target_item:
                return False, "No vehicle item found in invoice."
            
            overrides = overrides or {}

            date_str = invoice.datetime.strftime('%d-%m-%Y')
            inv_no = str(invoice.invoice_number)

            customer_name = overrides.get("name") or (invoice.customer.name if invoice.customer else "")
            
            # Father Name Logic
            # If overrides has 'father_name', use it. Else DB.
            customer_father = overrides.get("father_name") 
            if customer_father is None:
                 customer_father = invoice.customer.father_name if invoice.customer else ""
            
            # Relation Type Logic
            rel_type = overrides.get("rel_type", "S/O")

            if customer_father:
                if rel_type == "Org":
                    name_text = f"{customer_name} (Attn: {customer_father})".strip()
                else:
                    name_text = f"{customer_name} {rel_type} {customer_father}".strip()
            else:
                name_text = customer_name

            address_text = overrides.get("address") or (invoice.customer.address if (invoice.customer and invoice.customer.address) else "")

            # Model Logic
            model_text = overrides.get("model") or ""
            if not model_text and target_item.motorcycle and target_item.motorcycle.product_model:
                model_text = target_item.motorcycle.product_model.model_name or ""
            if not model_text:
                model_text = getattr(target_item, "model_name", "") or ""
            if not model_text:
                model_text = getattr(target_item, "item_name", "") or ""

            desc_text = "Honda Motorcycle"
            if model_text:
                desc_text += f" {model_text}"

            engine_text = overrides.get("engine") or (target_item.motorcycle.engine_number if target_item.motorcycle else "")
            chassis_text = target_item.motorcycle.chassis_number if target_item.motorcycle else ""
            
            color_text = overrides.get("color") or (target_item.motorcycle.color if target_item.motorcycle else "")

            item_total = target_item.total_amount
            
            # Check for financial overrides
            # Helper to parse float from string
            def parse_float_val(val):
                try:
                    return float(str(val).replace(",", "").strip())
                except:
                    return 0.0

            val_excl_override = parse_float_val(overrides.get("amount")) if overrides.get("amount") else None
            tax_charged_override = parse_float_val(overrides.get("sale_tax")) if overrides.get("sale_tax") else None
            further_tax_override = parse_float_val(overrides.get("other_tax")) if overrides.get("other_tax") else None

            if val_excl_override is not None:
                sale_value = val_excl_override
                tax_charged = tax_charged_override if tax_charged_override is not None else target_item.tax_charged
                further_tax = further_tax_override if further_tax_override is not None else target_item.further_tax
                
                # Recalculate Totals based on overrides
                horizontal_total = sale_value + tax_charged
                final_grand_total = horizontal_total + further_tax + 1.0
                
                amount_text = f"{sale_value:,.2f}"
                sale_tax_text = f"{tax_charged:,.2f}"
                other_tax_text = f"{further_tax:,.2f}"
                item_total_text = f"{horizontal_total:,.0f}"
                grand_total_text = f"{final_grand_total:,.0f}"
            else:
                item_total_text = f"{item_total:,.0f}"
                grand_total_text = f"{item_total:,.0f}"

                amount_text = f"{target_item.sale_value:,.2f}"
                sale_tax_text = f"{target_item.tax_charged:,.2f}"
                other_tax_text = f"{target_item.further_tax:,.2f}"
            
            defaults = {
                "date": {"x": 90, "y": 135},
                "inv_no": {"x": 90, "y": 165},
                "name": {"x": 90, "y": 215},
                "address": {"x": 90, "y": 255},
                "desc": {"x": 280, "y": 400},
                "engine": {"x": 280, "y": 440},
                "chassis": {"x": 280, "y": 480},
                "model": {"x": 280, "y": 520},
                "color": {"x": 280, "y": 560},
                "reg_letter": {"x": 280, "y": 600},
                "item_total": {"x": 460, "y": 400},
                "amount": {"x": 460, "y": 450},
                "sale_tax": {"x": 460, "y": 480},
                "other_tax": {"x": 460, "y": 510},
                "grand_total": {"x": 460, "y": 710},
                "qr": {"x": 340, "y": 620},
            }

            paper_width_mm = float(paper_width_mm)
            paper_height_mm = float(paper_height_mm)
            preview_width_px = float(preview_width_px)
            preview_height_px = float(preview_height_px)

            def pos_mm(key: str):
                cfg = (layout_config or {}).get(key) or defaults.get(key) or {"x": 0, "y": 0}
                x_px = float(cfg.get("x", 0))
                y_px = float(cfg.get("y", 0))
                return x_px * (paper_width_mm / preview_width_px), y_px * (paper_height_mm / preview_height_px)

            fields = [
                ("date", date_str, {"size": 10, "weight": 700}),
                ("inv_no", inv_no, {"size": 10, "weight": 700}),
                ("name", name_text, {"size": 10, "weight": 400}),
                ("address", address_text, {"size": 10, "weight": 400}),
                ("desc", desc_text, {"size": 10, "weight": 400}),
                ("engine", engine_text, {"size": 10, "weight": 400}),
                ("chassis", chassis_text, {"size": 10, "weight": 400}),
                ("model", model_text, {"size": 10, "weight": 400}),
                ("color", color_text, {"size": 10, "weight": 400}),
                ("reg_letter", "", {"size": 10, "weight": 400}),
                ("item_total", item_total_text, {"size": 10, "weight": 700}),
                ("amount", amount_text, {"size": 10, "weight": 400}),
                ("sale_tax", sale_tax_text, {"size": 10, "weight": 400}),
                ("other_tax", other_tax_text, {"size": 10, "weight": 400}),
                ("grand_total", grand_total_text, {"size": 12, "weight": 700}),
            ]

            elements_html = ""
            for key, value, style in fields:
                x_mm, y_mm = pos_mm(key)
                safe_value = html.escape(str(value))
                size = style.get("size", 10)
                weight = style.get("weight", 400)
                elements_html += (
                    f'<div class="field" style="left:{x_mm:.2f}mm; top:{y_mm:.2f}mm; '
                    f'font-size:{size}pt; font-weight:{weight};">{safe_value}</div>'
                )

            qr_html = ""
            fbr_inv_num = getattr(invoice, "fbr_invoice_number", None)
            if fbr_inv_num:
                qr_base64 = self.generate_qr_base64(fbr_inv_num)
                if qr_base64:
                    qr_x_mm, qr_y_mm = pos_mm("qr")
                    qr_html = (
                        f'<img class="qr" src="data:image/png;base64,{qr_base64}" '
                        f'style="left:{qr_x_mm:.2f}mm; top:{qr_y_mm:.2f}mm;" alt="FBR QR" />'
                        f'<div class="qr_text" style="left:{qr_x_mm:.2f}mm; top:{(qr_y_mm + 26):.2f}mm;">FBR Invoice #: {html.escape(str(fbr_inv_num))}</div>'
                    )

            html_content = f"""
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
                <meta charset=\"UTF-8\">
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                <title>Invoice {html.escape(inv_no)}</title>
                <style>
                    @page {{ size: {paper_width_mm:.2f}mm {paper_height_mm:.2f}mm; margin: 0; }}
                    html, body {{ margin: 0; padding: 0; }}
                    body {{ background: #fff; font-family: Arial, sans-serif; }}
                    .sheet {{ width: {paper_width_mm:.2f}mm; height: {paper_height_mm:.2f}mm; position: relative; }}
                    .field {{ position: absolute; white-space: pre; color: #000; }}
                    .qr {{ position: absolute; width: 25mm; height: 25mm; }}
                    .qr_text {{ position: absolute; font-size: 9pt; font-weight: 700; color: #000; }}
                    .screen_badge {{ display: none; }}
                    @media screen {{
                        body {{ display: flex; justify-content: center; padding: 16px; background: #f4f4f4; }}
                        .sheet {{ background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.15); }}
                        .screen_badge {{
                            display: block;
                            position: fixed;
                            left: 16px;
                            bottom: 16px;
                            background: rgba(0,0,0,0.72);
                            color: #fff;
                            padding: 8px 10px;
                            border-radius: 8px;
                            font-size: 12px;
                            z-index: 9999;
                        }}
                    }}
                    @media print {{
                        .screen_badge {{ display: none; }}
                    }}
                </style>
            </head>
            <body>
                <div class=\"sheet\">{elements_html}{qr_html}</div>
                <div class=\"screen_badge\">Paper: {paper_width_mm:.2f}×{paper_height_mm:.2f} mm</div>
                <script>
                    window.focus();
                </script>
            </body>
            </html>
            """

            fd, path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)

            webbrowser.open(f"file://{path}")
            return True, "Opened live preview print page"

        except Exception as e:
            return False, str(e)

    def print_invoice(self, invoice: Invoice):
        """
        Generates an HTML file for the invoice and opens it in the default browser.
        """
        try:
            # Prepare Data
            inv_num = invoice.invoice_number
            fbr_inv_num = invoice.fbr_invoice_number or "N/A"
            date_str = invoice.datetime.strftime("%d-%b-%Y %H:%M")
            
            customer_name = invoice.customer.name if invoice.customer else "N/A"
            customer_father = invoice.customer.father_name if invoice.customer else ""
            customer_business = invoice.customer.business_name if invoice.customer else ""
            
            # Construct Name with S/O, D/O, W/O logic
            # Since we don't have rel_type in DB, we'll infer or default to S/O unless it's a business
            full_customer_name = customer_name
            if customer_business:
                full_customer_name = f"{customer_business}<br>(Attn: {customer_name})"
            elif customer_father:
                 full_customer_name = f"{customer_name} S/O {customer_father}"
            
            customer_cnic = invoice.customer.cnic if invoice.customer else "N/A"
            customer_address = invoice.customer.address if invoice.customer else "N/A"
            customer_ntn = invoice.customer.ntn if invoice.customer else "N/A"
            
            # QR Code
            qr_code_img = ""
            if invoice.fbr_invoice_number:
                qr_base64 = self.generate_qr_base64(invoice.fbr_invoice_number)
                if qr_base64:
                    qr_code_img = f'<img src="data:image/png;base64,{qr_base64}" alt="FBR QR Code" class="qr-code"/>'
            
            # FBR Logo
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
            logo_path = os.path.join(project_root, "assets", "fbr_logo.png")
            logo_img_tag = ""
            if os.path.exists(logo_path):
                try:
                    with open(logo_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        logo_img_tag = f'<img src="data:image/png;base64,{encoded_string}" alt="FBR Logo" style="max-height: 80px; margin-bottom: 10px;">'
                except Exception:
                    pass
            
            if not logo_img_tag:
                 # Fallback text logo
                 logo_img_tag = '<div style="font-size: 24px; font-weight: bold; color: #006400; border: 2px solid #006400; padding: 5px 10px; display: inline-block; margin-bottom: 10px;">FBR</div>'

            # Items Rows
            items_html = ""
            
            # Column Totals
            sum_qty = 0
            sum_val = 0.0
            sum_tax = 0.0
            sum_nev = 0.0
            sum_total = 0.0

            for item in invoice.items:
                # Extract details
                model_name = ""
                engine_no = ""
                chassis_no = ""
                if item.motorcycle:
                    if item.motorcycle.product_model:
                        model_name = item.motorcycle.product_model.model_name
                    engine_no = item.motorcycle.engine_number
                    chassis_no = item.motorcycle.chassis_number
                
                # Fallbacks
                if not model_name:
                    model_name = getattr(item, "model_name", "") or ""
                
                details = []
                if model_name: details.append(f"Model: {model_name}")
                if engine_no: details.append(f"Eng: {engine_no}")
                if chassis_no: details.append(f"Chassis: {chassis_no}")
                
                details_html = "<br>".join(details)
                if details_html:
                    details_html = f"<br><span style='font-size: 0.9em; color: #555;'>{details_html}</span>"

                # Calculate specific values for display
                # Note: item.total_amount usually includes further tax
                # We want to display Further Tax explicitly if it exists
                further_tax = item.further_tax if hasattr(item, 'further_tax') else 0.0
                
                # Horizontal Total (Price + Sales Tax)
                # User requested Horizontal Total to be 209909 (Price + Tax), excluding N.E.V Levy
                row_total_display = item.sale_value + item.tax_charged
                
                # Accumulate Totals
                sum_qty += item.quantity
                sum_val += item.sale_value
                sum_tax += item.tax_charged
                sum_nev += further_tax
                sum_total += row_total_display # Sum of row totals
                
                items_html += f"""
                <tr>
                    <td>
                        <strong>{item.item_name}</strong>
                        {details_html}
                        <br><small>{item.item_code}</small>
                    </td>
                    <td class="text-right">{item.quantity}</td>
                    <td class="text-right">{item.sale_value:,.2f}</td>
                    <td class="text-right">{item.tax_rate}%</td>
                    <td class="text-right">{item.tax_charged:,.2f}</td>
                    <td class="text-right">{further_tax:,.2f}</td>
                    <td class="text-right">{row_total_display:,.2f}</td>
                </tr>
                """
            
            # Calculate Grand Total (Sum of Horizontal Totals + NEV + POS Fee)
            # Or use invoice.total_amount if it aligns, but let's be precise based on components
            # grand_total_val = sum_total + sum_nev + 1.0
            # User specified Vertical Grand Total should be 211901 (which is 211900 + 1)
            # Assuming invoice.total_amount is 211900
            
            final_grand_total = sum_total + sum_nev + 1.0

            
            # HTML Template
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Invoice {inv_num}</title>
                <style>
                    body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 20px; }}
                    .invoice-box {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #eee; box-shadow: 0 0 10px rgba(0, 0, 0, 0.15); }}
                    .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }}
                    .company-info {{ display: flex; flex-direction: column; align-items: flex-start; }}
                    .company-info h1 {{ margin: 0; font-size: 24px; color: #444; }}
                    .invoice-details {{ text-align: right; }}
                    .invoice-details h2 {{ margin: 0; color: #666; }}
                    .customer-info {{ margin-bottom: 30px; border-bottom: 1px solid #eee; padding-bottom: 20px; }}
                    .customer-info h3 {{ margin-top: 0; margin-bottom: 10px; }}
                    table {{ width: 100%; line-height: inherit; text-align: left; border-collapse: collapse; }}
                    table th {{ background: #f9f9f9; padding: 10px; font-weight: bold; border-bottom: 2px solid #ddd; }}
                    table td {{ padding: 10px; border-bottom: 1px solid #eee; vertical-align: top; }}
                    .text-right {{ text-align: right; }}
                    .totals {{ margin-top: 20px; text-align: right; }}
                    .totals-row {{ display: flex; justify-content: flex-end; padding: 5px 0; }}
                    .totals-row label {{ font-weight: bold; width: 150px; }}
                    .totals-row span {{ width: 120px; }}
                    .grand-total {{ font-size: 1.2em; font-weight: bold; border-top: 2px solid #333; padding-top: 10px; margin-top: 10px; }}
                    .footer {{ margin-top: 40px; text-align: center; font-size: 0.8em; color: #777; border-top: 1px solid #eee; padding-top: 20px; }}
                    .qr-code {{ width: 120px; height: 120px; margin-top: 10px; }}
                    .fbr-status {{ font-weight: bold; color: green; border: 1px solid green; padding: 5px 10px; display: inline-block; margin-top: 10px; }}
                    .watermark {{ position: absolute; top: 40%; left: 30%; font-size: 100px; color: rgba(0,0,0,0.05); transform: rotate(-45deg); z-index: -1; }}
                    
                    @media print {{
                        .invoice-box {{ border: none; box-shadow: none; padding: 0; }}
                        body {{ padding: 0; }}
                    }}
                </style>
            </head>
            <body>
                <div class="invoice-box">
                    <div class="header">
                        <div class="company-info">
                            {logo_img_tag}
                            <h1>INVOICE</h1>
                            <p><strong>FBR POS ID:</strong> {invoice.pos_id or 'N/A'}</p>
                        </div>
                        <div class="invoice-details">
                            <h2>#{inv_num}</h2>
                            <p>Date: {date_str}</p>
                            {f'<div class="fbr-status">FBR ID: {fbr_inv_num}</div>' if invoice.fbr_invoice_number else ''}
                            <br>
                            {qr_code_img}
                        </div>
                    </div>

                    <div class="customer-info">
                        <h3>Bill To:</h3>
                        <p>
                            <strong>{full_customer_name}</strong><br>
                            CNIC: {customer_cnic}<br>
                            NTN: {customer_ntn}<br>
                            {customer_address}
                        </p>
                    </div>

                    <table>
                        <thead>
                            <tr>
                                <th>Item</th>
                                <th class="text-right">Qty</th>
                                <th class="text-right">Price</th>
                                <th class="text-right">Tax %</th>
                                <th class="text-right">Tax</th>
                                <th class="text-right">N.E.V Levy</th>
                                <th class="text-right">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                        <tfoot>
                            <tr style="background: #e9e9e9; font-weight: bold;">
                                <td class="text-right">TOTALS:</td>
                                <td class="text-right">{sum_qty}</td>
                                <td class="text-right">{sum_val:,.2f}</td>
                                <td></td>
                                <td class="text-right">{sum_tax:,.2f}</td>
                                <td class="text-right">{sum_nev:,.2f}</td>
                                <td class="text-right">{sum_total:,.2f}</td>
                            </tr>
                        </tfoot>
                    </table>

                    <div class="totals">
                        <div class="totals-row">
                            <label>Subtotal:</label>
                            <span>{invoice.total_sale_value:,.2f}</span>
                        </div>
                        <div class="totals-row">
                            <label>Sales Tax ({invoice.items[0].tax_rate if invoice.items else 18}%):</label>
                            <span>{invoice.total_tax_charged:,.2f}</span>
                        </div>
                        <div class="totals-row">
                            <label>N.E.V Levy:</label>
                            <span>{invoice.total_further_tax:,.2f}</span>
                        </div>
                        <div class="totals-row">
                            <label>POS Fee:</label>
                            <span>1.00</span>
                        </div>
                        <div class="totals-row grand-total">
                            <label>Grand Total:</label>
                            <span>{final_grand_total:,.2f}</span>
                        </div>
                    </div>

                    <div class="footer">
                        <p>Thank you for your business!</p>
                        <p>This is a computer-generated invoice and may be verified via FBR Tax Asaan App.</p>
                    </div>
                </div>
            </body>
            </html>

            """
            
            # Write to Temp File
            fd, path = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Open in Browser
            webbrowser.open(f"file://{path}")
            
            return True, "Invoice opened for printing"
            
        except Exception as e:
            return False, str(e)

print_service = PrintService()

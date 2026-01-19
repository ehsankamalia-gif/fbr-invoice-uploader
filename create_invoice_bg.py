from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_invoice():
    # A4 size at roughly 72 DPI is 595x842. Let's use 600x850 for simplicity.
    width, height = 600, 850
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Draw simple lines to mimic the invoice structure
    
    # Honda Logo (Top Left)
    draw.text((30, 30), "HONDA", fill="red", font_size=40)
    
    # Dealer Info (Top Right)
    draw.text((400, 30), "Ehsan Traders", fill="red")
    draw.text((400, 50), "Kamalia", fill="black")
    
    # Invoice Title
    draw.text((250, 100), "INVOICE", fill="red", font_size=30)
    
    # Date and No
    draw.line((80, 150, 200, 150), fill="black", width=1)
    draw.text((30, 135), "Date:", fill="black")
    
    draw.line((80, 180, 200, 180), fill="black", width=1)
    draw.text((30, 165), "No.", fill="black")
    
    # Name and Address
    draw.line((80, 230, 550, 230), fill="black", width=1)
    draw.text((30, 215), "Name", fill="black")
    
    draw.line((80, 270, 550, 270), fill="black", width=1)
    draw.text((30, 255), "Address", fill="black")
    
    # Table Header
    y_start = 320
    draw.rectangle((30, y_start, 570, y_start+40), outline="black")
    draw.text((40, y_start+10), "QTY", fill="black")
    draw.text((150, y_start+10), "Description", fill="black")
    draw.text((450, y_start+10), "Total", fill="black")
    
    # Table Rows
    draw.rectangle((30, y_start+40, 570, 700), outline="black")
    draw.line((130, y_start+40, 130, 700), fill="black") # Vertical line after Qty
    draw.line((440, y_start+40, 440, 700), fill="black") # Vertical line before Total
    
    # Row Lines
    y = y_start + 40
    lines = ["Honda Motorcycle:", "Engine No:", "Chassis No:", "Model:", "Color:", "Reg Letter No:"]
    for i, line in enumerate(lines):
        draw.text((140, y + 40 + (i*40)), line, fill="gray")
        draw.line((260, y + 55 + (i*40), 430, y + 55 + (i*40)), fill="gray", width=1)

    # Footer
    draw.text((30, 750), "Customer Signature", fill="black")
    draw.line((30, 745, 200, 745), fill="black")
    
    draw.text((450, 750), "Signature", fill="black")
    draw.line((450, 745, 570, 745), fill="black")
    
    if not os.path.exists("assets"):
        os.makedirs("assets")
        
    image.save("assets/invoice_bg.png")
    print("Created assets/invoice_bg.png")

if __name__ == "__main__":
    create_placeholder_invoice()

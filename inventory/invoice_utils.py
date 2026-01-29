from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import io

@login_required(login_url='user')
def download_invoice(request, order_id):
    """Generate and download PDF invoice for an order"""
    from .models import Order
    
    try:
        order = Order.objects.get(id=order_id, customer=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order not found or you don't have permission to access it.")
        return redirect('order_history')
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4b2e1e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4b2e1e'),
        spaceAfter=12
    )
    
    # Title
    elements.append(Paragraph("FURNIQ", title_style))
    elements.append(Paragraph("INVOICE / RECEIPT", styles['Heading2']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Order Info
    order_data = [
        ['Order ID:', order.tracking_number or f"#{order.id}"],
        ['Order Date:', order.order_date.strftime('%B %d, %Y')],
        ['Payment Method:', order.payment_method],
        ['Payment Status:', order.payment_status],
        ['Order Status:', order.status],
    ]
    
    order_table = Table(order_data, colWidths=[2*inch, 3*inch])
    order_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4b2e1e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(order_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Customer Info
    elements.append(Paragraph("Customer Information", heading_style))
    customer_data = [
        ['Name:', order.customer.get_full_name() or order.customer.username],
        ['Email:', order.customer.email or 'N/A'],
    ]
    if order.delivery_phone:
        customer_data.append(['Phone:', order.delivery_phone])
    if order.delivery_address:
        customer_data.append(['Address:', order.delivery_address])
    
    customer_table = Table(customer_data, colWidths=[2*inch, 4*inch])
    customer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4b2e1e')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(customer_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Items Table
    elements.append(Paragraph("Order Items", heading_style))
    
    # Header for Items Table
    item_header = [['Product Description', 'Quantity', 'Unit Price', 'Total']]
    item_data = []
    
    # Robust Parsing of items_summary
    # Expected format: "Item1 (x2) - Rs 500, Item2 (x1) - Rs 200"
    raw_summary = order.items_summary or ""
    parts = raw_summary.split(',')
    
    for p in parts:
        p = p.strip()
        if not p: continue
        
        try:
            # 1. Primary approach: "Item (x2) - Rs 500"
            if ' - ' in p:
                name_part = p.split(' - ')[0]
                price_part = p.split(' - ')[1].replace('Rs', '').strip()
                
                name = name_part.split(' (x')[0]
                qty = name_part.split(' (x')[1].replace(')', '') if ' (x' in name_part else "1"
                
                total_p = float(price_part)
                unit_p = total_p / int(qty)
                item_data.append([name, qty, f"Rs {unit_p:.2f}", f"Rs {total_p:.2f}"])
            
            # 2. Fallback for old orders: "Item (x2)"
            else:
                from .models import Product
                name = p.split(' (x')[0]
                qty = p.split(' (x')[1].replace(')', '') if ' (x' in p else "1"
                
                # Try to fetch unit price from DB fallback
                prod = Product.objects.filter(name__icontains=name).first()
                if prod:
                    unit_p = float(prod.price)
                    total_p = unit_p * int(qty)
                    item_data.append([name, qty, f"Rs {unit_p:.2f}", f"Rs {total_p:.2f}"])
                else:
                    item_data.append([name, qty, "N/A", "N/A"])
        except:
            item_data.append([p, "1", "N/A", "N/A"])
            
    if not item_data:
        item_data = [["No items detail available", "-", "-", "-"]]

    # Combine Header + Data
    full_table_data = item_header + item_data
    
    items_table = Table(full_table_data, colWidths=[3*inch, 0.8*inch, 1.2*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fdfaf8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4b2e1e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Grand Total Block
    total_data = [
        ['', 'Grand Total:', f'Rs {order.total_price}'],
    ]
    total_table = Table(total_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
    total_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (-1, -1), 12),
        ('TEXTCOLOR', (1, 0), (-1, -1), colors.HexColor('#4b2e1e')),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(total_table)
    
    # Professional Footer
    elements.append(Spacer(1, 0.8*inch))
    elements.append(Paragraph("This is a computer-generated receipt and does not require a physical signature.", ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)))
    elements.append(Spacer(1, 0.1*inch))
    elements.append(Paragraph("Thank you for choosing FurniQ Luxury Interiors!", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)))
    
    # Build PDF
    try:
        doc.build(elements)
        buffer.seek(0)
        
        # Return PDF
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="FurniQ_Invoice_{order.tracking_number or order.id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f"Error generating invoice: {str(e)}")
        return redirect('order_history')

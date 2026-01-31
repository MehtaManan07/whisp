from typing import Optional
from pydantic import BaseModel, Field


class OrderItemData(BaseModel):
    """DTO for a single order item."""
    
    product_name: Optional[str] = Field(default=None, description="Product name")
    sku: Optional[str] = Field(default=None, description="Product SKU")
    price: Optional[str] = Field(default=None, description="Product price")
    quantity: Optional[str] = Field(default=None, description="Order quantity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_name": "T-Shirt",
                "sku": "TSH-001",
                "price": "₹500",
                "quantity": "2",
            }
        }


class ProcessEmailsRequest(BaseModel):
    """Request DTO for processing kraftculture emails."""
    
    from_email: Optional[str] = Field(
        default=None, 
        description="Override sender email to filter (uses config default if not provided)"
    )
    max_results: int = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="Maximum number of emails to fetch"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "max_results": 10,
            }
        }


class ProcessEmailsResponse(BaseModel):
    """Response DTO for email processing results."""
    
    processed_count: int = Field(..., description="Number of emails processed")
    sent_count: int = Field(..., description="Number of WhatsApp messages sent")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    
    class Config:
        json_schema_extra = {
            "example": {
                "processed_count": 3,
                "sent_count": 3,
                "errors": [],
            }
        }


class ParsedEmailData(BaseModel):
    """DTO for parsed Webkul order email data."""
    
    order_id: Optional[str] = Field(default=None, description="Order ID")
    order_name: Optional[str] = Field(default=None, description="Order name")
    items: list[OrderItemData] = Field(default_factory=list, description="List of order items")
    # Keep legacy single-item fields for backward compatibility
    product_name: Optional[str] = Field(default=None, description="Product name (deprecated, use items)")
    sku: Optional[str] = Field(default=None, description="Product SKU (deprecated, use items)")
    price: Optional[str] = Field(default=None, description="Product price (deprecated, use items)")
    quantity: Optional[str] = Field(default=None, description="Order quantity (deprecated, use items)")
    payment_status: Optional[str] = Field(default=None, description="Payment status")
    customer_name: Optional[str] = Field(default=None, description="Customer name")
    address_line: Optional[str] = Field(default=None, description="Address line")
    city_state_pincode: Optional[str] = Field(default=None, description="City, state, pincode")
    country: Optional[str] = Field(default=None, description="Country")
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "12345",
                "order_name": "ORD-001",
                "items": [
                    {"product_name": "T-Shirt", "sku": "TSH-001", "price": "₹500", "quantity": "2"},
                    {"product_name": "Jeans", "sku": "JNS-002", "price": "₹1200", "quantity": "1"},
                ],
                "product_name": "T-Shirt",
                "sku": "TSH-001",
                "price": "₹500",
                "quantity": "2",
                "payment_status": "Paid",
                "customer_name": "John Doe",
                "address_line": "123 Main St",
                "city_state_pincode": "Mumbai, MH 400001",
                "country": "India",
            }
        }

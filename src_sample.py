def calculate_discount(price: float, discount_rate: float) -> float:
    if discount_rate < 0 or discount_rate > 100:
        raise ValueError("La tasa de descuento debe estar entre 0 y 100")
    
    discount_amount = price * (discount_rate / 100)
    return price - discount_amount
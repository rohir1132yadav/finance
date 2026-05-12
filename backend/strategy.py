def calculate_price_change(current, previous):
    return ((current - previous) / previous) * 100

def calculate_spread(bid, ask, spot):
    return ((ask - bid) / spot) * 100

def calculate_liquidity(bid, ask, spot):
    return ((ask - bid) / spot) * 100

def calculate_atm(price):
    return round(price / 50) * 50
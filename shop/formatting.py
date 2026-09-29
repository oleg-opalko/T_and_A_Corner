def format_uah(value):
    try:
        amount = f'{value:,.2f}'.replace(',', ' ').replace('.', ',')
    except (TypeError, ValueError):
        return value
    return f'{amount} грн'

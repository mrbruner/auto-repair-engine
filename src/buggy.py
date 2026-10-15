def calculate_total(price, tax):
    # Intentional bug: 'tax_rate' is undefined (should be 'tax')
    total = price + (price * tax_rate)
    return total

if __name__ == "__main__":
    print(calculate_total(100, 0.05))

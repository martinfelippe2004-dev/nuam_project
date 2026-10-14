from decimal import Decimal, ROUND_HALF_UP

def calcular_factores_desde_montos(montos_dict):
    """
    Recibe un diccionario con montos {'monto_08': Decimal, ..., 'monto_19': Decimal, ...}
    Calcula los factores dividiendo cada monto por la base total.
    Aplica redondeo exacto al 8vo decimal.
    """
    
    base_afecta = Decimal('0')
    for i in range(8, 20):
        clave = f'monto_{i:02d}'
        base_afecta += Decimal(str(montos_dict.get(clave, 0) or 0))

    factores_calculados = {}

    if base_afecta > Decimal('0'):
        for i in range(8, 20):
            clave_monto = f'monto_{i:02d}'
            monto = Decimal(str(montos_dict.get(clave_monto, 0) or 0))
            factor = (monto / base_afecta).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
            factores_calculados[f'factor_{i:02d}'] = factor
    else:
        for i in range(8, 20):
            factores_calculados[f'factor_{i:02d}'] = Decimal('0.00000000')

    for i in range(20, 38):
        clave_f = f'factor_{i:02d}'
        clave_m = f'monto_{i:02d}'
        valor = montos_dict.get(clave_f) or montos_dict.get(clave_m) or 0
        factores_calculados[clave_f] = Decimal(str(valor)).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

    suma_8_a_19 = sum(factores_calculados[f'factor_{i:02d}'] for i in range(8, 20))
    if suma_8_a_19 > Decimal('1.00000000'):
        raise ValueError(f"Inconsistencia normativa: La suma de los factores 8 al 19 da {suma_8_a_19}, superando el límite de 1.00000000.")

    return factores_calculados
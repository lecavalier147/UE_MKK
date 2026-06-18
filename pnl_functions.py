import math

# ------------------------------------------------------------------
# 1. ФИКСИРОВАННАЯ МАТРИЦА РЕТЕНШН (не выносим в интерфейс)
# ------------------------------------------------------------------
RETENTION_DISTRIBUTION = [
    0.193035236, 0.134961924, 0.094249796, 0.074784504, 0.062350676,
    0.055178598, 0.043844575, 0.037204127, 0.031744049, 0.030081385,
    0.027366096, 0.024009771, 0.021567695, 0.019596441, 0.019395174,
    0.018052836, 0.016968566, 0.015839143, 0.015158945, 0.016692521,
    0.015500169, 0.016876157, 0.01443332, 0.012452476
]
# Сумма ~ 1.0

# ------------------------------------------------------------------
# 2. ТАБЛИЦА КОЭФФИЦИЕНТОВ АННУИТЕТА (доля процентов по месяцам)
#    Ключ: срок в месяцах, значение: список долей (сумма = 1)
# ------------------------------------------------------------------
ANNUITY_COEFFS = {
    1: [1.0],
    2: [0.6667, 0.3333],
    3: [0.50, 0.3333, 0.1667],
    4: [0.40, 0.30, 0.20, 0.10],
    5: [0.3333, 0.2667, 0.20, 0.1333, 0.0667],
    6: [0.2857, 0.2381, 0.1905, 0.1429, 0.0952, 0.0476],
    7: [0.25, 0.2143, 0.1786, 0.1429, 0.1071, 0.0714, 0.0357],
    8: [0.2222, 0.1944, 0.1667, 0.1389, 0.1111, 0.0833, 0.0556, 0.0278],
    9: [0.20, 0.1778, 0.1556, 0.1333, 0.1111, 0.0889, 0.0667, 0.0444, 0.0222],
    10: [0.1818, 0.1636, 0.1455, 0.1273, 0.1091, 0.0909, 0.0727, 0.0545, 0.0364, 0.0182],
    11: [0.1667, 0.1515, 0.1364, 0.1212, 0.1061, 0.0909, 0.0758, 0.0606, 0.0455, 0.0303, 0.0152],
    12: [0.1538, 0.1410, 0.1282, 0.1154, 0.1026, 0.0897, 0.0769, 0.0641, 0.0513, 0.0385, 0.0256, 0.0128],
}
# Для сроков > 12 используем равномерное распределение (заглушка)


def generate_loan_cashflows(params, issue_month, total_months):
    """
    params: словарь с параметрами займа
    issue_month: месяц выдачи (0-based)
    total_months: горизонт планирования
    Возвращает breakdown – словарь со статьями (списки длиной total_months)
    """
    # Извлечение параметров
    L = params.get('L', 0.0)
    t = params.get('t', 30)                # срок в днях
    r = params.get('r', 1.0) / 100.0       # ставка (доля)
    fee = params.get('fee', 5.0) / 100.0
    early_rate = params.get('early_rate', 0.0)
    default_rate = params.get('default_rate', 0.12)
    lgd = params.get('lgd', 0.8)
    ins_pen = params.get('ins_pen', 0.25)
    ins_sum = params.get('ins_sum', 800.0)
    cross_pen = params.get('cross_pen', 0.10)
    cross_sum = params.get('cross_sum', 2000.0)
    money_transfer_cost = params.get('money_transfer_cost', 0.5) / 100.0
    collection_rate = params.get('collection_rate', 0.30)
    collection_cost_rate = params.get('collection_cost_rate', 7.0) / 100.0
    funding_rate = params.get('funding_rate', 19.0) / 100.0
    repay_fee_inc = params.get('repay_fee_inc', 3.5) / 100.0
    repay_fee_exp = params.get('repay_fee_exp', 0.3) / 100.0
    portfolio_sale_rate = params.get('portfolio_sale_rate', 0.80)
    portfolio_sale_price = params.get('portfolio_sale_price', 18.0) / 100.0
    tax_rate = params.get('tax_rate', 20.0) / 100.0

    ins_margin = 0.95
    cross_margin = 0.90
    vat_factor = 1.2

    is_new = params.get('is_new', True)
    if is_new:
        cac_direct = params.get('cac_direct', 500.0)
        # СМС и колл-центр обнуляем по требованию
        sms_cost = 0.0
        kc_cost = 0.0
        scoring_cost = params.get('scoring_cost', 49.0)
        ident_cost = params.get('ident_cost', 150.0)
        AR = params.get('AR', 0.62)
        TR = params.get('TR', 0.63)
        lead_price = params.get('lead_price', 108.0)
        scoring_per_loan = scoring_cost / AR / TR if AR and TR else scoring_cost
        ident_per_loan = ident_cost / AR / TR if AR and TR else ident_cost
        rejection_income = lead_price / TR * ((1 - AR) / AR) if AR and TR else 0.0
    else:
        cac_direct = params.get('cac_direct', 0.0)
        sms_cost = 0.0
        kc_cost = 0.0
        scoring_cost = params.get('scoring_cost', 0.0)
        ident_cost = params.get('ident_cost', 0.0)
        scoring_per_loan = scoring_cost
        ident_per_loan = ident_cost
        rejection_income = 0.0
        AR = 1.0
        TR = 1.0

    # Общие суммы (как в UE)
    interest_total = L * r * t
    fee_income = L * fee
    cross_income = (cross_margin * cross_pen * cross_sum) / vat_factor if cross_sum else 0.0
    ins_income = (ins_margin * ins_pen * ins_sum) / vat_factor if ins_sum else 0.0
    early_loss = L * r * t * early_rate * 0.5
    portfolio_sale_income = L * default_rate * (1 + r * t) * portfolio_sale_rate * portfolio_sale_price
    repay_fee_inc_total = L * (1 + r * t) * (1 - default_rate) * repay_fee_inc
    repay_fee_exp_total = L * (1 + r * t) * (1 - default_rate) * repay_fee_exp
    money_transfer = L * money_transfer_cost
    collection = collection_rate * (1 - default_rate) * L * collection_cost_rate
    expected_loss = L * default_rate * lgd
    funding_total = L * (1 + r * t / 2) * (funding_rate / 365) * t

    n_months = max(1, math.ceil(t / 30))  # срок в месяцах

    # Список статей
    revenue_keys = ['процентный_доход', 'комиссия_за_выдачу', 'страховки', 'кросс_продукты',
                    'комиссия_за_погашение_доход', 'продажа_портфеля', 'отказной_трафик']
    expense_keys = ['CAC', 'СМС', 'колл_центр', 'скоринг', 'идентификация', 'перевод_денег',
                    'взыскание', 'фондирование', 'комиссия_за_погашение_расход', 'резервы_ECL',
                    'потери_от_досрочки', 'налог']
    all_keys = revenue_keys + expense_keys
    breakdown = {key: [0.0] * total_months for key in all_keys}

    # ---- РАСПРЕДЕЛЕНИЕ ПРОЦЕНТНОГО ДОХОДА ПО АННУИТЕТУ ----
    # Получаем коэффициенты для данного срока (если есть)
    if n_months in ANNUITY_COEFFS:
        coeffs = ANNUITY_COEFFS[n_months]
        # Если срок меньше n_months? n_months = срок, так что ок.
    else:
        # Если срока нет в таблице, используем равномерное распределение
        coeffs = [1.0 / n_months] * n_months

    for m in range(n_months):
        month_index = issue_month + m
        if month_index >= total_months:
            break
        # Доля процентов в этом месяце
        share = coeffs[m] if m < len(coeffs) else 0.0
        breakdown['процентный_доход'][month_index] += interest_total * share

    # ---- ОСТАЛЬНЫЕ СТАТЬИ ----
    # Фондирование – распределяем равномерно по дням (пока оставим)
    funding_per_day = funding_total / t if t > 0 else 0
    repay_inc_per_day = repay_fee_inc_total / t if t > 0 else 0
    repay_exp_per_day = repay_fee_exp_total / t if t > 0 else 0

    for m in range(n_months):
        month_index = issue_month + m
        if month_index >= total_months:
            break
        days_in_month = min(30, t - m * 30)
        if days_in_month <= 0:
            break
        breakdown['фондирование'][month_index] += funding_per_day * days_in_month
        breakdown['комиссия_за_погашение_доход'][month_index] += repay_inc_per_day * days_in_month
        breakdown['комиссия_за_погашение_расход'][month_index] += repay_exp_per_day * days_in_month

    # Момент выдачи
    if issue_month < total_months:
        breakdown['комиссия_за_выдачу'][issue_month] += fee_income
        breakdown['страховки'][issue_month] += ins_income
        breakdown['кросс_продукты'][issue_month] += cross_income
        breakdown['отказной_трафик'][issue_month] += rejection_income

        sale_month = issue_month + min(12, n_months)
        if sale_month < total_months:
            breakdown['продажа_портфеля'][sale_month] += portfolio_sale_income
        else:
            last_month = min(issue_month + n_months - 1, total_months - 1)
            breakdown['продажа_портфеля'][last_month] += portfolio_sale_income

        # Расходы в момент выдачи (СМС и колл-центр обнулены)
        breakdown['CAC'][issue_month] += cac_direct + sms_cost + kc_cost
        breakdown['скоринг'][issue_month] += scoring_per_loan
        breakdown['идентификация'][issue_month] += ident_per_loan
        breakdown['перевод_денег'][issue_month] += money_transfer
        breakdown['взыскание'][issue_month] += collection
        breakdown['резервы_ECL'][issue_month] += expected_loss
        breakdown['потери_от_досрочки'][issue_month] += early_loss

    # ---- НАЛОГ (помесячно) ----
    for m in range(total_months):
        profit_before_tax = (breakdown['процентный_доход'][m] +
                             breakdown['комиссия_за_выдачу'][m] +
                             breakdown['страховки'][m] +
                             breakdown['кросс_продукты'][m] +
                             breakdown['комиссия_за_погашение_доход'][m] +
                             breakdown['продажа_портфеля'][m] +
                             breakdown['отказной_трафик'][m] -
                             breakdown['CAC'][m] -
                             breakdown['СМС'][m] -
                             breakdown['колл_центр'][m] -
                             breakdown['скоринг'][m] -
                             breakdown['идентификация'][m] -
                             breakdown['перевод_денег'][m] -
                             breakdown['взыскание'][m] -
                             breakdown['фондирование'][m] -
                             breakdown['комиссия_за_погашение_расход'][m] -
                             breakdown['резервы_ECL'][m] -
                             breakdown['потери_от_досрочки'][m])
        if profit_before_tax > 0:
            breakdown['налог'][m] += profit_before_tax * tax_rate

    return breakdown


def calculate_repeat_loans(new_volumes, RR, total_months):
    """Расчёт повторных займов с использованием фиксированной матрицы ретеншн."""
    repeat_loans = [0] * total_months
    max_delay = len(RETENTION_DISTRIBUTION)
    for m in range(total_months):
        total_repeat = 0.0
        for i in range(m):
            delay = m - i
            if 1 <= delay <= max_delay:
                total_repeat += new_volumes[i] * RR * RETENTION_DISTRIBUTION[delay - 1]
        repeat_loans[m] = total_repeat
    return repeat_loans


def aggregate_pnl_detailed(products_data, volumes_dict, RR,
                           total_months, fixed_opex_per_month):
    """
    products_data: список словарей с ключами 'id', 'params_new', 'params_repeat'
    volumes_dict: {product_id: {'new': [list]}}
    total_months: горизонт
    fixed_opex_per_month: постоянные расходы
    Возвращает breakdown_total (словарь со статьями) и также добавляет
    'new_loans_count' и 'repeat_loans_count' для агрегированных объёмов.
    """
    # Список всех статей (такой же, как в generate_loan_cashflows)
    revenue_keys = ['процентный_доход', 'комиссия_за_выдачу', 'страховки', 'кросс_продукты',
                    'комиссия_за_погашение_доход', 'продажа_портфеля', 'отказной_трафик']
    expense_keys = ['CAC', 'СМС', 'колл_центр', 'скоринг', 'идентификация', 'перевод_денег',
                    'взыскание', 'фондирование', 'комиссия_за_погашение_расход', 'резервы_ECL',
                    'потери_от_досрочки', 'налог']
    all_keys = revenue_keys + expense_keys

    breakdown_total = {key: [0.0] * total_months for key in all_keys}
    # Добавляем счётчики займов
    breakdown_total['new_loans_count'] = [0] * total_months
    breakdown_total['repeat_loans_count'] = [0] * total_months

    for prod in products_data:
        prod_id = prod['id']
        params_new = prod['params_new']
        params_repeat = prod['params_repeat']
        new_volumes = volumes_dict.get(prod_id, {}).get('new', [0] * total_months)
        repeat_loans = calculate_repeat_loans(new_volumes, RR, total_months)

        for m in range(total_months):
            cnt_new = new_volumes[m] if m < len(new_volumes) else 0
            if cnt_new > 0:
                breakdown_total['new_loans_count'][m] += cnt_new
                p_new = params_new.copy()
                p_new['is_new'] = True
                br = generate_loan_cashflows(p_new, m, total_months)
                for key in all_keys:
                    for i in range(total_months):
                        breakdown_total[key][i] += br[key][i] * cnt_new

            cnt_repeat = repeat_loans[m] if m < len(repeat_loans) else 0
            if cnt_repeat > 0:
                breakdown_total['repeat_loans_count'][m] += cnt_repeat
                p_repeat = params_repeat.copy()
                p_repeat['is_new'] = False
                br = generate_loan_cashflows(p_repeat, m, total_months)
                for key in all_keys:
                    for i in range(total_months):
                        breakdown_total[key][i] += br[key][i] * cnt_repeat

    # Постоянные расходы
    breakdown_total['постоянные_расходы'] = [fixed_opex_per_month] * total_months

    return breakdown_total
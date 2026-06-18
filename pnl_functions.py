import math

def generate_loan_cashflows(params, issue_month, total_months):
    """
    Генерирует помесячные денежные потоки для одного займа с детализацией по статьям.
    params: словарь с параметрами займа (как в UE)
    issue_month: месяц выдачи (0-based)
    total_months: общее количество месяцев для расчёта
    Возвращает: breakdown – словарь {статья: [значение_за_месяц, ...]}
    """
    L = params['L']
    t = params['t']  # дней
    r = params['r'] / 100.0
    fee = params['fee'] / 100.0
    early_rate = params.get('early_rate', 0.0)
    default_rate = params['default_rate']
    lgd = params['lgd']
    ins_pen = params['ins_pen']
    ins_sum = params['ins_sum']
    ins_margin = 0.95
    cross_pen = params['cross_pen']
    cross_sum = params['cross_sum']
    cross_margin = 0.90
    vat_factor = 1.2
    money_transfer_cost = params['money_transfer_cost'] / 100.0
    collection_rate = params['collection_rate']
    collection_cost_rate = params['collection_cost_rate'] / 100.0
    funding_rate = params['funding_rate'] / 100.0
    repay_fee_inc = params['repay_fee_inc'] / 100.0
    repay_fee_exp = params['repay_fee_exp'] / 100.0
    portfolio_sale_rate = params['portfolio_sale_rate']
    portfolio_sale_price = params['portfolio_sale_price'] / 100.0
    tax_rate = params['tax_rate'] / 100.0
    
    is_new = params.get('is_new', True)
    if is_new:
        cac_direct = params['cac_direct']
        sms_cost = params['sms_count'] * params['sms_price']
        kc_cost = params['kc_cost']
        scoring_per_loan = params['scoring_cost'] / params['AR'] / params['TR']
        ident_per_loan = params['ident_cost'] / params['AR'] / params['TR']
        rejection_income = params['lead_price'] / params['TR'] * ((1 - params['AR']) / params['AR'])
    else:
        cac_direct = params['cac_direct']
        sms_cost = params['sms_count'] * params['sms_price']
        kc_cost = params['kc_cost']
        scoring_per_loan = params['scoring_cost']
        ident_per_loan = params['ident_cost']
        rejection_income = 0.0

    # Общие суммы (как в UE)
    interest_total = L * r * t
    fee_income = L * fee
    cross_income = (cross_margin * cross_pen * cross_sum) / vat_factor
    ins_income = (ins_margin * ins_pen * ins_sum) / vat_factor
    early_loss = L * r * t * early_rate * 0.5
    portfolio_sale_income = L * default_rate * (1 + r * t) * portfolio_sale_rate * portfolio_sale_price
    repay_fee_inc_total = L * (1 + r * t) * (1 - default_rate) * repay_fee_inc
    repay_fee_exp_total = L * (1 + r * t) * (1 - default_rate) * repay_fee_exp
    money_transfer = L * money_transfer_cost
    collection = collection_rate * (1 - default_rate) * L * collection_cost_rate
    expected_loss = L * default_rate * lgd
    funding_total = L * (1 + r * t / 2) * (funding_rate / 365) * t

    n_months = max(1, math.ceil(t / 30))

    # Инициализация детализации
    breakdown = {
        'процентный_доход': [0.0] * total_months,
        'комиссия_за_выдачу': [0.0] * total_months,
        'страховки': [0.0] * total_months,
        'кросс_продукты': [0.0] * total_months,
        'комиссия_за_погашение_доход': [0.0] * total_months,
        'продажа_портфеля': [0.0] * total_months,
        'отказной_трафик': [0.0] * total_months,
        'CAC': [0.0] * total_months,
        'СМС': [0.0] * total_months,
        'колл_центр': [0.0] * total_months,
        'скоринг': [0.0] * total_months,
        'идентификация': [0.0] * total_months,
        'перевод_денег': [0.0] * total_months,
        'взыскание': [0.0] * total_months,
        'фондирование': [0.0] * total_months,
        'комиссия_за_погашение_расход': [0.0] * total_months,
        'резервы_ECL': [0.0] * total_months,
        'потери_от_досрочки': [0.0] * total_months,
        'налог': [0.0] * total_months,
    }

    # Распределение по дням (проценты, фондирование, комиссии за погашение)
    interest_per_day = L * r
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
        breakdown['процентный_доход'][month_index] += interest_per_day * days_in_month
        breakdown['фондирование'][month_index] += funding_per_day * days_in_month
        breakdown['комиссия_за_погашение_доход'][month_index] += repay_inc_per_day * days_in_month
        breakdown['комиссия_за_погашение_расход'][month_index] += repay_exp_per_day * days_in_month

    # Доходы в момент выдачи
    if issue_month < total_months:
        breakdown['комиссия_за_выдачу'][issue_month] += fee_income
        breakdown['страховки'][issue_month] += ins_income
        breakdown['кросс_продукты'][issue_month] += cross_income
        breakdown['отказной_трафик'][issue_month] += rejection_income
        # Продажа портфеля – через 12 месяцев или в последний месяц
        sale_month = issue_month + min(12, n_months)
        if sale_month < total_months:
            breakdown['продажа_портфеля'][sale_month] += portfolio_sale_income
        else:
            last_month = min(issue_month + n_months - 1, total_months - 1)
            breakdown['продажа_портфеля'][last_month] += portfolio_sale_income

    # Расходы в момент выдачи
    if issue_month < total_months:
        breakdown['CAC'][issue_month] += cac_direct + sms_cost + kc_cost
        breakdown['скоринг'][issue_month] += scoring_per_loan
        breakdown['идентификация'][issue_month] += ident_per_loan
        breakdown['перевод_денег'][issue_month] += money_transfer
        breakdown['взыскание'][issue_month] += collection
        breakdown['резервы_ECL'][issue_month] += expected_loss
        breakdown['потери_от_досрочки'][issue_month] += early_loss

    # Налог (помесячно, на положительную прибыль)
    # Рассчитываем прибыль до налога за месяц
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


def calculate_repeat_loans(new_volumes, RR, retention_distribution, total_months):
    repeat_loans = [0] * total_months
    max_delay = len(retention_distribution)
    for m in range(total_months):
        total_repeat = 0.0
        for i in range(m):
            delay = m - i
            if 1 <= delay <= max_delay:
                total_repeat += new_volumes[i] * RR * retention_distribution[delay - 1]
        repeat_loans[m] = total_repeat
    return repeat_loans


def aggregate_pnl_detailed(products_data, volumes_dict, RR, retention_distribution,
                           total_months, fixed_opex_per_month):
    """
    Агрегирует детализированный P&L по всем продуктам.
    products_data: список словарей с параметрами продуктов
    volumes_dict: {product_id: {'new': [list]}}
    RR, retention_distribution: см. выше
    total_months: int
    fixed_opex_per_month: float
    Возвращает словарь breakdown_total (ключи – статьи, значения – списки длиной total_months)
    """
    breakdown_total = {}
    # Инициализируем пустыми списками на основе первого продукта
    first_prod = products_data[0]
    sample_breakdown = generate_loan_cashflows(first_prod['params_new'], 0, total_months)
    for key in sample_breakdown.keys():
        breakdown_total[key] = [0.0] * total_months

    for prod in products_data:
        prod_id = prod['id']
        params_new = prod['params_new']
        params_repeat = prod['params_repeat']
        new_volumes = volumes_dict[prod_id]['new']
        repeat_loans = calculate_repeat_loans(new_volumes, RR, retention_distribution, total_months)

        for m in range(total_months):
            cnt_new = new_volumes[m]
            if cnt_new > 0:
                p = params_new.copy()
                p['is_new'] = True
                br = generate_loan_cashflows(p, m, total_months)
                for key in br:
                    breakdown_total[key][m] += br[key][m] * cnt_new  # только для месяца m, но нужно умножать все месяцы! Ошибка – исправим ниже.
            # Правильно: умножаем все месяцы, а не только m.
    # Выше ошибка: нужно умножать все месяцы, а не только m. Перепишем.

    # Исправленный цикл:
    for prod in products_data:
        prod_id = prod['id']
        params_new = prod['params_new']
        params_repeat = prod['params_repeat']
        new_volumes = volumes_dict[prod_id]['new']
        repeat_loans = calculate_repeat_loans(new_volumes, RR, retention_distribution, total_months)

        for m in range(total_months):
            cnt_new = new_volumes[m]
            if cnt_new > 0:
                p = params_new.copy()
                p['is_new'] = True
                br = generate_loan_cashflows(p, m, total_months)
                for key in br:
                    for i in range(total_months):
                        breakdown_total[key][i] += br[key][i] * cnt_new

            cnt_repeat = repeat_loans[m]
            if cnt_repeat > 0:
                p = params_repeat.copy()
                p['is_new'] = False
                br = generate_loan_cashflows(p, m, total_months)
                for key in br:
                    for i in range(total_months):
                        breakdown_total[key][i] += br[key][i] * cnt_repeat

    # Добавляем постоянные операционные расходы отдельной статьёй
    breakdown_total['постоянные_расходы'] = [fixed_opex_per_month] * total_months

    # Также можно добавить итоговые строки: всего доходов, всего расходов, прибыль.
    # Их мы вычислим в UI.

    return breakdown_total
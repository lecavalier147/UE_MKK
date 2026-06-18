import math

def generate_loan_cashflows(params, issue_month, total_months):
    """
    Генерирует помесячные денежные потоки для одного займа.
    params: словарь с параметрами займа (как в UE)
    issue_month: месяц выдачи (0-based)
    total_months: общее количество месяцев для расчёта
    Возвращает: (revenue, costs, profit) – списки длиной total_months
    """
    L = params['L']
    t = params['t']  # дней
    r = params['r'] / 100.0
    fee = params['fee'] / 100.0
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
        cac_total = (params['cac_direct'] + 
                     params['sms_count'] * params['sms_price'] + 
                     params['kc_cost'])
        scoring_per_loan = params['scoring_cost'] / params['AR'] / params['TR']
        ident_per_loan = params['ident_cost'] / params['AR'] / params['TR']
        rejection_income = params['lead_price'] / params['TR'] * ((1 - params['AR']) / params['AR'])
    else:
        cac_total = params['cac_direct']
        scoring_per_loan = params['scoring_cost']
        ident_per_loan = params['ident_cost']
        rejection_income = 0.0

    # Общие суммы (как в UE)
    interest_total = L * r * t
    fee_income = L * fee
    cross_income = (cross_margin * cross_pen * cross_sum) / vat_factor
    ins_income = (ins_margin * ins_pen * ins_sum) / vat_factor
    portfolio_sale_income = L * default_rate * (1 + r * t) * portfolio_sale_rate * portfolio_sale_price
    repay_fee_inc_total = L * (1 + r * t) * (1 - default_rate) * repay_fee_inc
    repay_fee_exp_total = L * (1 + r * t) * (1 - default_rate) * repay_fee_exp
    money_transfer = L * money_transfer_cost
    collection = collection_rate * (1 - default_rate) * L * collection_cost_rate
    expected_loss = L * default_rate * lgd
    funding_total = L * (1 + r * t / 2) * (funding_rate / 365) * t

    # Длительность в месяцах (округление вверх)
    n_months = max(1, math.ceil(t / 30))

    revenue = [0.0] * total_months
    costs = [0.0] * total_months

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
        revenue[month_index] += interest_per_day * days_in_month
        costs[month_index] += funding_per_day * days_in_month
        revenue[month_index] += repay_inc_per_day * days_in_month
        costs[month_index] += repay_exp_per_day * days_in_month

    # Доходы в момент выдачи
    if issue_month < total_months:
        revenue[issue_month] += fee_income + ins_income + cross_income + rejection_income
        # Продажа портфеля – через 12 месяцев или в последний месяц
        sale_month = issue_month + min(12, n_months)
        if sale_month < total_months:
            revenue[sale_month] += portfolio_sale_income
        else:
            last_month = min(issue_month + n_months - 1, total_months - 1)
            revenue[last_month] += portfolio_sale_income

    # Расходы в момент выдачи
    if issue_month < total_months:
        costs[issue_month] += (cac_total + scoring_per_loan + ident_per_loan +
                               money_transfer + collection + expected_loss)

    # Налог (применяем для каждого месяца, если прибыль > 0)
    for m in range(total_months):
        profit = revenue[m] - costs[m]
        if profit > 0:
            costs[m] += profit * tax_rate

    profit = [revenue[i] - costs[i] for i in range(total_months)]
    return revenue, costs, profit


def calculate_repeat_loans(new_volumes, RR, retention_distribution, total_months):
    """
    Рассчитывает количество повторных займов по месяцам.
    new_volumes: список новых выдач по месяцам (длина total_months)
    RR: общий retention rate
    retention_distribution: список вероятностей повтора через k месяцев (сумма=1)
    total_months: горизонт планирования
    Возвращает список repeat_loans длиной total_months
    """
    repeat_loans = [0] * total_months
    max_delay = len(retention_distribution)
    for m in range(total_months):
        total_repeat = 0.0
        for i in range(m):
            delay = m - i  # количество месяцев между выдачей и повторным займом
            if 1 <= delay <= max_delay:
                total_repeat += new_volumes[i] * RR * retention_distribution[delay - 1]
        repeat_loans[m] = total_repeat
    return repeat_loans


def aggregate_pnl(products_data, volumes_dict, RR, retention_distribution,
                  total_months, fixed_opex_per_month):
    """
    Агрегирует P&L по всем продуктам.
    products_data: список словарей с параметрами продуктов (каждый содержит 'id', 'params_new', 'params_repeat')
    volumes_dict: {product_id: {'new': [list], 'repeat': [list]}} – repeat можно не передавать, он рассчитается
    RR, retention_distribution: см. выше
    total_months: int
    fixed_opex_per_month: float
    Возвращает словарь с массивами revenue, costs, profit, cumulative_profit
    """
    total_revenue = [0.0] * total_months
    total_costs = [0.0] * total_months

    for prod in products_data:
        prod_id = prod['id']
        params_new = prod['params_new']
        params_repeat = prod['params_repeat']
        new_volumes = volumes_dict[prod_id]['new']  # список длиной total_months

        # Рассчитываем repeat_loans
        repeat_loans = calculate_repeat_loans(new_volumes, RR, retention_distribution, total_months)

        # Для каждого месяца генерируем cashflows для всех займов
        for m in range(total_months):
            cnt_new = new_volumes[m]
            if cnt_new > 0:
                p = params_new.copy()
                p['is_new'] = True
                rev, cost, _ = generate_loan_cashflows(p, m, total_months)
                for i in range(total_months):
                    total_revenue[i] += rev[i] * cnt_new
                    total_costs[i] += cost[i] * cnt_new

            cnt_repeat = repeat_loans[m]
            if cnt_repeat > 0:
                p = params_repeat.copy()
                p['is_new'] = False
                rev, cost, _ = generate_loan_cashflows(p, m, total_months)
                for i in range(total_months):
                    total_revenue[i] += rev[i] * cnt_repeat
                    total_costs[i] += cost[i] * cnt_repeat

    # Добавляем постоянные операционные расходы
    for m in range(total_months):
        total_costs[m] += fixed_opex_per_month

    total_profit = [total_revenue[i] - total_costs[i] for i in range(total_months)]
    cum_profit = []
    cum = 0.0
    for p in total_profit:
        cum += p
        cum_profit.append(cum)

    return {
        'revenue': total_revenue,
        'costs': total_costs,
        'profit': total_profit,
        'cumulative_profit': cum_profit
    }
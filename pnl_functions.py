import math

def generate_loan_cashflows(params, issue_month, total_months):
    L = params.get('L', 0.0)
    t = params.get('t', 30)
    r = params.get('r', 1.0) / 100.0
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
        sms_count = params.get('sms_count', 6)
        sms_price = params.get('sms_price', 3.0)
        kc_cost = params.get('kc_cost', 59.0)
        scoring_cost = params.get('scoring_cost', 49.0)
        ident_cost = params.get('ident_cost', 150.0)
        AR = params.get('AR', 0.62)
        TR = params.get('TR', 0.63)
        lead_price = params.get('lead_price', 108.0)
        sms_cost = sms_count * sms_price
        scoring_per_loan = scoring_cost / AR / TR if AR and TR else scoring_cost
        ident_per_loan = ident_cost / AR / TR if AR and TR else ident_cost
        rejection_income = lead_price / TR * ((1 - AR) / AR) if AR and TR else 0.0
    else:
        cac_direct = params.get('cac_direct', 0.0)
        sms_count = params.get('sms_count', 0)
        sms_price = params.get('sms_price', 0.0)
        kc_cost = params.get('kc_cost', 0.0)
        scoring_cost = params.get('scoring_cost', 0.0)
        ident_cost = params.get('ident_cost', 0.0)
        sms_cost = sms_count * sms_price
        scoring_per_loan = scoring_cost
        ident_per_loan = ident_cost
        rejection_income = 0.0
        AR = 1.0
        TR = 1.0

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

    n_months = max(1, math.ceil(t / 30))
    
    # Доходные статьи
    revenue_keys = ['процентный_доход', 'комиссия_за_выдачу', 'страховки', 'кросс_продукты',
                    'комиссия_за_погашение_доход', 'продажа_портфеля', 'отказной_трафик']
    expense_keys = ['CAC', 'СМС', 'колл_центр', 'скоринг', 'идентификация', 'перевод_денег',
                    'взыскание', 'фондирование', 'комиссия_за_погашение_расход', 'резервы_ECL',
                    'потери_от_досрочки', 'налог']
    all_keys = revenue_keys + expense_keys
    breakdown = {key: [0.0] * total_months for key in all_keys}

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

        breakdown['CAC'][issue_month] += cac_direct + sms_cost + kc_cost
        breakdown['скоринг'][issue_month] += scoring_per_loan
        breakdown['идентификация'][issue_month] += ident_per_loan
        breakdown['перевод_денег'][issue_month] += money_transfer
        breakdown['взыскание'][issue_month] += collection
        breakdown['резервы_ECL'][issue_month] += expected_loss
        breakdown['потери_от_досрочки'][issue_month] += early_loss

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
    # Список статей (те же, что в generate_loan_cashflows)
    revenue_keys = ['процентный_доход', 'комиссия_за_выдачу', 'страховки', 'кросс_продукты',
                    'комиссия_за_погашение_доход', 'продажа_портфеля', 'отказной_трафик']
    expense_keys = ['CAC', 'СМС', 'колл_центр', 'скоринг', 'идентификация', 'перевод_денег',
                    'взыскание', 'фондирование', 'комиссия_за_погашение_расход', 'резервы_ECL',
                    'потери_от_досрочки', 'налог']
    all_keys = revenue_keys + expense_keys

    breakdown_total = {key: [0.0] * total_months for key in all_keys}

    for prod in products_data:
        prod_id = prod['id']
        params_new = prod['params_new']
        params_repeat = prod['params_repeat']
        new_volumes = volumes_dict.get(prod_id, {}).get('new', [0] * total_months)
        repeat_loans = calculate_repeat_loans(new_volumes, RR, retention_distribution, total_months)

        for m in range(total_months):
            cnt_new = new_volumes[m] if m < len(new_volumes) else 0
            if cnt_new > 0:
                p_new = params_new.copy()
                p_new['is_new'] = True
                br = generate_loan_cashflows(p_new, m, total_months)
                for key in all_keys:
                    for i in range(total_months):
                        breakdown_total[key][i] += br[key][i] * cnt_new

            cnt_repeat = repeat_loans[m] if m < len(repeat_loans) else 0
            if cnt_repeat > 0:
                p_repeat = params_repeat.copy()
                p_repeat['is_new'] = False
                br = generate_loan_cashflows(p_repeat, m, total_months)
                for key in all_keys:
                    for i in range(total_months):
                        breakdown_total[key][i] += br[key][i] * cnt_repeat

    breakdown_total['постоянные_расходы'] = [fixed_opex_per_month] * total_months
    return breakdown_total